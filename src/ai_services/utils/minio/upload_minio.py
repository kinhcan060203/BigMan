import base64
import sys
import io
import uuid
from minio import Minio

from utils.logger import logger
from config import (
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET_EVENTS,
    MINIO_SERVER,
)


def upload_base64_image_to_minio(base64_image, event_type, cam_id, dir_name):

    client = Minio(
        MINIO_SERVER,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )

    img_id = uuid.uuid4()  
    if dir_name:
        img_name = f"{event_type}/{cam_id}/{dir_name}/{img_id}.jpg"
    else:
        img_name = f"{event_type}/{cam_id}/{img_id}.jpg"
    
    logger.info(f"Image name: {img_name}")
    image_data = base64.b64decode(base64_image)
    image_file = io.BytesIO(image_data)

    try:
        result = client.put_object(
            MINIO_BUCKET_EVENTS,
            img_name,
            image_file,
            len(image_data),
            content_type="image/jpg",
        )
    except Exception as error:
        logger.error(error)
        result = None

    if result:
        img_url = f"http://{MINIO_SERVER}/{MINIO_BUCKET_EVENTS}/{img_name}"
        return img_url

    return None



