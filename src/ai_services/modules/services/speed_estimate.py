from utils.functions import  event_trigger
import threading
import time
import cv2
import numpy as np
from config import REDIS_HOST, REDIS_PORT
from utils.draw import DrawerObject
import redis
import supervision as sv
from modules.kafka import publish_image_to_kafka

def handle_speed_estimate(
    kafka_topic,
    frame,
    detections,
    camera_info,
    tracker,
    vga_drawer,
    org_drawer,
    kafka_producer,
    trigger_thread,
    stop_event,
    ikey,
    redis_client,
    db,
):
    mask = np.isin(detections.class_id, [1, 2, 5, 6])
    detections = detections[mask]
    annotated_frame = frame.copy()
    

    # publish_image_to_kafka(
    #     producer=kafka_producer,
    #     topic=f"speed_estimate.{kafka_topic}",
    #     img=annotated_frame,
    # )



