import os
import threading
import numpy as np
import cv2
import json
import datetime
import uuid
from utils.logger import logger
import msgpack

def publish_image_to_kafka(producer, topic, img):
    img = cv2.resize(img, (640, 480))
    _, img_encoded = cv2.imencode(".jpg", img)
    buffer = img_encoded.tobytes()
    pub_kafka(producer, topic, None, buffer)

def clean_message_producer(data):
    for k, v in data.items():
        if isinstance(data[k], datetime.datetime):
            data[k] = data[k].isoformat()
        if isinstance(data[k], uuid.UUID):
            data[k] = str(data[k])

    return data

def pub_kafka(producer, topic, key, value):
    try:
        if not key:
            key = str(uuid.uuid4())
        producer.produce(topic, key=key, value=value)
        producer.poll(0)
    except BufferError:
        logger.warning("Local queue is full, waiting for free space...")
        producer.flush()
    except BrokenPipeError:
        logger.info("Broken pipe error occurred. Check your Kafka connection.")
    except Exception as e:
        logger.info(f"An error occurred: {e}")



def publish_message_to_kafka(producer, topic, message):
    message = clean_message_producer(message)
    message["camera"] = message["camera_id"]
    message["id"] = message["event_id"]
    clean_message = json.dumps(message)
    pub_kafka(producer, topic, None, clean_message)


def deserialize_data(packed_data):
    unpacked_data = msgpack.unpackb(packed_data, raw=False)
    frame_bytes = unpacked_data["frame"]
    metadata = unpacked_data["metadata"]
    return frame_bytes, metadata

def serialize_data(frame_bytes, metadata):
    return msgpack.packb(
        {"frame": frame_bytes, "metadata": metadata}, use_bin_type=True
    )
