import cv2
import numpy as np
import uuid
import time
from ultralytics import YOLO
import supervision as sv
from supervision import ByteTrack
import argparse
import sys
import torch.nn.functional as F
import cv2
import numpy as np
import tqdm
from torch.backends import cudnn
sys.path.append('./')
from fastreid.config import get_cfg
from fastreid.utils.logger import setup_logger
import logging
from fastreid.utils.file_io import PathManager
from predictor import FeatureExtractionDemo
from config import (
    KAFKA_SERVER,
    POSTGRES_DATABASE,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    REDIS_HOST,
    REDIS_PORT,
)
from modules.redis_handler import RedisHandler
from modules.milvus_handler import MilvusMonitor
import supervision as sv
from confluent_kafka import Consumer, Producer, KafkaError, TopicPartition, Producer, OFFSET_END
import msgpack
from utils.common import deserialize_data, upload_image_to_minio
from collections import Counter
from sklearn.metrics.pairwise import cosine_similarity
import peewee
from modules.models import Camera, Event, WatchListLicensePlate, Vehicle

cudnn.benchmark = True
setup_logger(name="reid")
logger = logging.getLogger("reid")

def setup_cfg(args):
    cfg = get_cfg()
    # add_partialreid_config(cfg)
    cfg.merge_from_file(args.config_file)
    cfg.merge_from_list(args.opts)
    cfg.freeze()
    return cfg


def get_parser():
    parser = argparse.ArgumentParser(description="Feature extraction with reid models")
    parser.add_argument(
        "--config-file",
        metavar="FILE",
        default='src/reid/reid_configs/VehicleID/bagtricks_R50-ibn.yml',
        help="path to config file",
    )
    parser.add_argument(
        "--parallel",
        action='store_true',
        help='If use multiprocess for feature extraction.'
    )
    parser.add_argument(
        "--input",
        nargs="+",
        help="A list of space separated input images; "
             "or a single glob pattern such as 'directory/*.jpg'",
    )
    parser.add_argument(
        "--output",
        default='demo_output',
        help='path to save features'
    )
    parser.add_argument(
        "--opts",
        help="Modify config options using the command-line 'KEY VALUE' pairs",
        default=[],
        nargs=argparse.REMAINDER,
    )
    return parser


def postprocess(features):
    features = F.normalize(features)
    features = features.cpu().data.numpy()
    return features

def get_embedding(reid_model, vehicle_box_img):
    feat = reid_model.run_on_image(vehicle_box_img)
    feat = postprocess(feat)[0]
    return feat
def print_depth(d, start=0):
    for key, value in d.items():
        print(key, start + 1)
        if isinstance(value, dict):
            print_depth(value, start=start+1)
def clear_reid(milvus_cache, redis_cache, tracker_id=None, identity=None):
    if tracker_id is not None:
        search_results = milvus_cache.get_tracker_id("tmp_vehicle", tracker_id)
        if search_results:
            embeddings = np.array([result["embedding"] for result in search_results])
            if embeddings.size:
                similarity_matrix = cosine_similarity(embeddings)
                sum_similarity = np.sum(similarity_matrix, axis=1)
                top_indices = np.argsort(sum_similarity)[-2:]
                best_ids = [search_results[i]["id"] for i in top_indices]

                redis_data = redis_cache.lrange(tracker_id, 0, -1)
                redis_dict = {eval(data)["id"]: eval(data) for data in redis_data}
                for row in search_results:
                    id = row["id"]
                    vehicle_path = ''
                    lpr = 'unknown'
                    if redis_data and id in redis_dict:
                        tmp_file_name = redis_dict[id]["tmp_file_name"]
                        service_name, camera_name = redis_dict[id]["service_name"], redis_dict[id]["camera_name"]  
                        image = cv2.imread(tmp_file_name)
                        import os
                        # os.makedirs("store", exist_ok=True)
                        # index = len(os.listdir("store"))
                        # cv2.imwrite(f"store/{index}-{id}.jpg", image)
                        try:
                            vehicle_path = upload_image_to_minio(
                                image, service_name, camera_name, dir_name="vehicle"
                            )
                        except:
                            print("Upload image to minio failed")
                        lpr = redis_dict[id]["lpr"]
                        try:
                            os.remove(tmp_file_name)
                        except Exception as e:

                            print("Error", e)
                    if id in best_ids:
                        item = milvus_cache.insert("main_vehicle", {
                            "embedding": row["embedding"],
                            "timestamp": row["timestamp"],
                            "camera_name": row["camera_name"],
                            "identity": row["identity"],
                            "vehicle_path": vehicle_path,
                            "lpr": lpr,

                        })
                        import rich
                        import datetime
                        camera = Camera.get(Camera.camera_id == row["camera_name"])
                        timestamp = datetime.datetime.fromtimestamp(float(row["timestamp"]))
                        class_name = redis_dict[id]["class_name"]
                        try:
                            new_event = Vehicle.create(
                                license_plate=lpr,
                                data={"class_name": class_name},
                                thumbnail=vehicle_path,
                                snapshot_at=timestamp,
                                camera_id=camera.id,
                                embedding_id=item["ids"][0]
                            )
                        except Exception as e:
                            rich.console.Console().print_exception()
                            print("Error", e)
                    elif lpr !="unknown":
                        item = milvus_cache.insert("main_vehicle", {
                            "embedding": row["embedding"],
                            "timestamp": row["timestamp"],
                            "camera_name": row["camera_name"],
                            "identity": row["identity"],
                            "vehicle_path": vehicle_path,
                            "lpr": lpr,

                        })
                        import rich
                        import datetime
                        camera = Camera.get(Camera.camera_id == row["camera_name"])
                        timestamp = datetime.datetime.fromtimestamp(float(row["timestamp"]))
                        class_name = redis_dict[id]["class_name"]
                        try:
                            new_event = Vehicle.create(
                                license_plate=lpr,
                                data={"class_name": class_name},
                                thumbnail=vehicle_path,
                                snapshot_at=timestamp,
                                camera_id=camera.id,
                                embedding_id=item["ids"][0]
                            )
                        except Exception as e:
                            rich.console.Console().print_exception()
                            print("Error", e)
                    milvus_cache.delete_by_id('tmp_vehicle',id)

        redis_cache.delete(tracker_id)
        print("clear tracker_id", tracker_id)

    
def update_reid(milvus_cache, redis_cache, reid_model, metadata, vehicle_box_img):
    tracker_id = int(metadata.get("tracker_id", -1))
    camera_name = metadata.get("camera_name", 'unknown')
    service_name = metadata.get("service_name", 'unknown')
    lpr = metadata.get("lpr", 'unknown')
    timestamp = metadata.get("timestamp", 0)
    source_service = metadata.get("source_service", 'unknown')
    class_name = metadata.get("class_name", 'unknown')
    collection_name = "tmp_vehicle"
    embedding = get_embedding(reid_model, vehicle_box_img)
    search_results = milvus_cache.search(collection_name, embedding, camera_name)

    if search_results:
        identities = [result[0]["entity"]["identity"] for result in search_results]
        if identities:
            optim_identity = Counter(identities).most_common(1)[0][0]
            optim_index = identities.index(optim_identity)
        else:
            optim_identity = str(uuid.uuid4())[:10]
    else:
        optim_identity = str(uuid.uuid4())[:10]

    import os
    os.makedirs("tmp", exist_ok=True)
    index = len(os.listdir("tmp"))
    tmp_file_name = f"tmp/{index}-{optim_identity}.jpg"
    cv2.imwrite(f"tmp/{index}-{optim_identity}.jpg", vehicle_box_img)

    if tracker_id is not None:
        item = milvus_cache.insert(collection_name, {
            "embedding": embedding,
            "timestamp": timestamp,
            "event_type": source_service,
            "camera_name": camera_name,
            "tracker_id": tracker_id,
            "identity": optim_identity,
        })
        vehicle_data = {
            "id": item["ids"][0],
            "camera_name": camera_name,
            "service_name": service_name,
            "lpr": lpr,
            "timestamp": timestamp,
            "event_type": source_service,
            "identity": optim_identity,
            "tmp_file_name": tmp_file_name,
            "class_name": class_name,
        }
        vehicle_data = str(vehicle_data)
        redis_cache.rpush(tracker_id, vehicle_data)
        return embedding, optim_identity
    return None, None


def convert_ndarray_to_list(obj):
    if isinstance(obj, dict):
        return {k: convert_ndarray_to_list(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_ndarray_to_list(elem) for elem in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    else:
        return obj


def run(cfg, args, consumer_config, producer_config, stop_event):
    db = peewee.PostgresqlDatabase(
            POSTGRES_DATABASE, host=POSTGRES_HOST, port=POSTGRES_PORT, user=POSTGRES_USER, password=POSTGRES_PASSWORD
        )
    db.bind([Camera, Event, WatchListLicensePlate, Vehicle])
    db.connect()
    reid_model = FeatureExtractionDemo(cfg, parallel=args.parallel)

    redis_cache = RedisHandler(host=REDIS_HOST, port=REDIS_PORT, db=1)

    redis_cache.redis_client.flushdb()

    import threading
    milvus_cache = MilvusMonitor(uri="http://localhost:19532", token="root:anh123", tmp_collection_name="tmp_vehicle", main_collection_name="main_vehicle", stop_event=stop_event)

    topic = "reid"
    consumer = Consumer({**consumer_config, "group.id": topic})
    partition = TopicPartition(topic, 0, OFFSET_END)
    consumer.assign([partition])
    consumer.seek(partition)
    i=0
    while not stop_event.is_set():
        msg = consumer.poll(timeout=1.0)

        if msg is None:
            print("no message")
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                logger.debug(msg.error())
                break
        ikey = msg.key().decode("utf-8")
        vehicle_box_img, metadata = deserialize_data(msg.value())
        if vehicle_box_img is None or metadata is None:
            continue
        vehicle_box_img = cv2.imdecode(np.frombuffer(vehicle_box_img, dtype=np.uint8), cv2.IMREAD_COLOR)
        
        # fake vehicle_box_img  and metadata for testing
        # import time
        # time.sleep(1)
        # i+=1
        # type = "reid"
        # if i % 3 == 0:
        #     type = "lost"
        
        # vehicle_box_img = cv2.imread("vtest.jpg")
        # metadata = {
        #     "tracker_id": 123,
        #     "camera_name": "Bullet161",
        #     "service_name": "reid",
        #     "lpr": "123",
        #     "timestamp": 123,
        #     "source_service": "reid",
        #     "type": type
        # }

        source_service = metadata.get("source_service", None)
        tracker_id = metadata.get("tracker_id", None)

        type = metadata.get("type", None)
        if type == "lost":
            tracker_id = metadata.get("tracker_id", None)
            print("lost", tracker_id)
            clear_reid(milvus_cache, redis_cache, tracker_id = tracker_id)
        else:
            print("reid", tracker_id)
            embedding, optim_identity = update_reid(milvus_cache, redis_cache, reid_model, metadata, vehicle_box_img)

        # reid_managment[camera_name][tracker_id].append({"optim_identity": optim_identity, "embedding":  embedding})



def init_config_and_start():
    args = get_parser().parse_args()
    cfg = setup_cfg(args)
    PathManager.mkdirs(args.output)
    print(POSTGRES_DATABASE, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD)

    import multiprocessing

    producer_config = {
        "bootstrap.servers": KAFKA_SERVER,
        "linger.ms": 5,
        "batch.size": 20,
        "message.max.bytes": 10000000,
        "enable.ssl.certificate.verification": False,
    }
    consumer_config = {
        "bootstrap.servers": KAFKA_SERVER,
        "auto.offset.reset": "latest",
        "fetch.message.max.bytes": 10000000,
        "enable.ssl.certificate.verification": False,
        "enable.auto.commit": False,
    }


    stop_event = multiprocessing.Event()
    p = multiprocessing.Process(target=run, args=(cfg, args, producer_config, consumer_config, stop_event))
    p.start()
    try:
        while True:
            time.sleep(600)
    except KeyboardInterrupt:
        logger.info("Exiting...")
        stop_event.set()
      
    p.join()

    logger.info("All processes stopped")

if __name__ == "__main__":
    init_config_and_start()


