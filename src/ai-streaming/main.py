import datetime
import numpy as np
import pymongo
import supervision as sv
import torch
from ultralytics import YOLO
import cv2
from rich import print, inspect
from os.path import join
from utils.logger import logger
import json
from config import MONGODB_SERVER, KAFKA_SERVER, REDIS_HOST, REDIS_PORT
import time
from utils.camera import Camera
from confluent_kafka import Producer
from utils.common import encode_image, serialize_data
from utils.kafka import pub_kafka_metadata
from utils.redis import RedisHandler
import queue

import multiprocessing
from concurrent.futures import ThreadPoolExecutor



def preprocessing(camera_streams, start_index):
    global preprocess_outputs, is_ok
    i = 0
    def get_frame(camera):
        ret_, (frame_tensor, key, frame) = camera.get()
        return ret_, key, frame, frame_tensor

    with ThreadPoolExecutor(max_workers=len(camera_streams)) as executor:
        while True:

            futures = [
                executor.submit(get_frame, thread) for thread in camera_streams
            ]
            results = [future.result() for future in futures]
            ret_list, keys, frames_list, frames_tensor_list = zip(*results)

            batch_tensor = torch.stack(frames_tensor_list)
            time.sleep(1/100)
            preprocess_outputs = (
                list(ret_list),
                list(keys),
                list(frames_list),
                batch_tensor,
                f"batch_{i}",
            )
            
            i += 1
            if i == 10000:
                i = 0

import uuid
def send_metadata(
    producer,
    result,
    key,
    topic,
    frame,
    tracker,
):
    try:
        result = result.to("cpu")
        detections = sv.Detections.from_ultralytics(result)
        detections = tracker.update_with_detections(detections)
        meta = {
            "timestamp": time.time(),
            "detections": detections.xyxy.tolist(),
            "confidences": detections.confidence.tolist(),
            "class_ids": detections.class_id.tolist(),
            "data": {"class_name": detections.data.get("class_name", np.empty(0)).tolist()},
            "track_ids": detections.tracker_id.tolist(),
        }
        frame_bytes = encode_image(frame)
        data = serialize_data(frame_bytes, meta)

        pub_kafka_metadata(
            producer,
            f"stream.{topic}",
            key,
            data,
        )
    except Exception as e:
        console.print_exception()
        logger.error(f"Error: {e}")


def main(
    net,
    start_index,
    camera_streams,
    topics,

):
    global preprocess_outputs, is_ok
    trackers = [sv.ByteTrack() for _ in range(len(topics))]
    executor = ThreadPoolExecutor(max_workers=8)
    stream = torch.cuda.Stream()
    start = time.time()
    import threading
    preprocess_thread = threading.Thread(
        target=preprocessing, args=(camera_streams, start_index)
    )
    preprocess_thread.start()
    producer = Producer(
        {
            "bootstrap.servers": KAFKA_SERVER,
            "message.max.bytes": 10 * 1024 * 1024,  # 10 MB
            "enable.ssl.certificate.verification": False,
        }
    )
    while True:
        try:
            if preprocess_outputs[0] is None:
                continue
            ret, keys, frames, frames_tensor, batch_id = preprocess_outputs
            time.sleep(1/30)
            with torch.cuda.stream(stream):
                results = net(
                    frames_tensor,
                    stream=False,
                    verbose=False,
                    conf=0.4,
                    iou=0.7,
                    agnostic_nms=True,
                    classes=[1, 2, 3, 4, 5],
                )

            if start_index == 0:
                elapsed_time = time.time() - start
                start = time.time()
                print(f"FPS: {1/elapsed_time}", batch_id, ret)
            for idx, result in enumerate(results):
                if not ret[idx] or len(result.boxes) == 0:
                    continue
                send_metadata(
                    producer,
                    result,
                    keys[idx],
                    topics[idx],
                    frames[idx],
                    trackers[idx],
                )
        except KeyboardInterrupt:
            print("Ctrl C")
            for camera in camera_streams:
                camera.stop()
                camera.join()
                logger.info(f"Camera {camera} stopped.")
            break
        except Exception as e:
            console.print_exception()
            logger.error(f"Error: {e}")
            continue


from rich.console import Console
console = Console()

import argparse

if __name__ == "__main__":
    # add argument parser

    parser = argparse.ArgumentParser(description="Process camera.")
    parser.add_argument("--start_index", type=int, required=False, help="Start index")
    parser.add_argument("--num_cam", type=int, required=False, help="Number of camera")
    parser.add_argument("--meta_file", type=str, required=False, help="Meta file")

    args = parser.parse_args()

    preprocess_outputs = (None, None, None, None)
    is_ok = True
    # Load model
    net = YOLO("src/ai-streaming/models/detect/best.engine")

    mongo_client = pymongo.MongoClient("mongodb://admin:anh123@100.112.243.28:27010/?authSource=admin")
    metadata = mongo_client["nano"]["camera"]
    metadata = list(metadata.find({}))
    logger.info(f"Connected to mongodb: {MONGODB_SERVER}!")


    camera_data = metadata[args.start_index : args.start_index + args.num_cam]

    CLASS_NAMES = net.names
    redis_client = RedisHandler(
        host=REDIS_HOST, port=REDIS_PORT, db=0, timeout=5
    )
    camera_streams = [
        Camera(camera_data[i]["url"], redis_client, cam=0)
        for i in range(len(camera_data))
    ]
    topics = [camera_data[i]["camera_id"] for i in range(len(camera_data))]
    main(
        net,
        args.start_index,
        camera_streams,
        topics,
     
    )
    
    cv2.destroyAllWindows()
