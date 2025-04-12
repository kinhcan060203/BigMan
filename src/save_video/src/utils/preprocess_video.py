import cv2
import os
import uuid
import logging as logger

from src.modules.check_size import check_vd_size
from src.modules.upload_object import upload_video_to_minio
from src.modules.models import Recordings
from config import MINIO_HOSTNAME, LENGTH_VIDEO
from src.utils.image_handler import decode_base64_image, generate_random_id
from src.db.database import db

folder = "./video"
if os.path.exists(folder) == False:
    os.mkdir(folder)


def convert_video(folder, list_frame, fps, height, width):
    try:
        random_id = uuid.uuid4()
        video = f"./{folder}/output_{random_id}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"avc1")
        out = cv2.VideoWriter(video, fourcc, int(fps), (width, height))
        for frame in list_frame:
            decoded_frame = decode_base64_image(frame)
            out.write(decoded_frame)
        out.release()
        logger.info("CONVERT VIDEO SUCCESS")
        return video
    except Exception as e:
        logger.info(f"Error converting video: {e}")
        return None


def upload_video(client, list_frame, camera_topic, list_params, event_message):
    if db.is_closed():
        db.connect()
    random_id = generate_random_id()
    random_id = uuid.uuid4()
    logger.info("########################")
    logger.info(f"topic: {camera_topic} with total frame: {len(list_frame)}")
    logger.info("UPLOAD VIDEO")
    fps, height, width = list_params
    file_name = convert_video(folder, list_frame, fps, height, width)
    type_event = camera_topic.split(".")[0]
    cam_topic = camera_topic.split(".")[1]
    upload_video_to_minio(
        MINIO_HOSTNAME,
        client,
        "video-record",
        file_name,
        f"{type_event}/{cam_topic}/{event_message['id']}.mp4",
        ".mp4",
    )
    os.remove(file_name)
    logger.info("########################")
    Recordings.insert(
        # id=random_id,
        event_id=event_message["id"],
        path=f"http://{MINIO_HOSTNAME}/video-record/{type_event}/{cam_topic}/{event_message['id']}.mp4",
        start_time=event_message["start_time"],
        end_time=event_message["end_time"],
        duration=LENGTH_VIDEO,
        segment_size=0,
    ).execute()
