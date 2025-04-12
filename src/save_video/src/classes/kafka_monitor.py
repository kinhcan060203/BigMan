import base64
import cv2
import numpy as np
from confluent_kafka import Consumer, KafkaException, KafkaError
import json
import logging as logger
import uuid

from config import LENGTH_VIDEO
from src.utils.preprocess_video import upload_video
from src.classes.minio_monitor import MinioMonitor


class KafkaMonitor:
    def __init__(self, kafka_hostname, redis_client):
        self.consumer = Consumer(
            {
                "bootstrap.servers": kafka_hostname + ":9092",
                "group.id": str(uuid.uuid1()),
                "auto.offset.reset": "latest",
                "enable.auto.commit": False,
            }
        )
        self.redis_client = redis_client
        minio_monitor = MinioMonitor()
        self.minio_client = minio_monitor.client

    def consumer_message(self, camera_topic):
        kafka_pat = self.consumer.poll(timeout=1.0)
        if kafka_pat is None:
            return
        if kafka_pat.error():
            if kafka_pat.error().code() == KafkaError._PARTITION_EOF:
                logger.info(f"End of partition reached {camera_topic}")
            else:
                return
        else:
            frame = kafka_pat.value()
            return frame

    def produce_message():
        pass

    def process_message(self, message):
        nparr = np.frombuffer(message, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        height, width, _ = frame.shape
        resized_frame_base64 = base64.b64encode(cv2.imencode(".jpg", frame)[1]).decode(
            "utf-8"
        )
        return resized_frame_base64, height, width

    def collect_frames(self, old_frames, camera_topic, list_params, event_message):
        last_frame = json.loads(old_frames[-1])
        list_frame = []

        fps = list_params[0]
        old_json_frames = [json.loads(frame) for frame in old_frames]

        while len(list_frame) < (int(fps) * int(LENGTH_VIDEO)) / 2:
            last_data = json.loads(self.redis_client.lrange(camera_topic, -2, -1)[0])

            if float(last_frame["timestamp"]) < float(last_data["timestamp"]):
                list_frame.append(last_frame)
                last_frame = last_data
        list_frame = old_json_frames + list_frame

        new_list_frame = [frame["frame"] for frame in list_frame]

        # Upload video to Minio
        upload_video(
            self.minio_client,
            new_list_frame,
            camera_topic,
            list_params,
            event_message,
        )
