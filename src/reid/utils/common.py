import msgpack
import cv2
import numpy as np
from PIL import Image
import io
import base64
from utils.logger import logger
import uuid
from minio import Minio

from utils.logger import logger
from config import (
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET_EVENTS,
    MINIO_SERVER,
)



def deserialize_data(packed_data):
    unpacked_data = msgpack.unpackb(packed_data, raw=False)
    frame_bytes = unpacked_data["frame"]
    metadata = unpacked_data["metadata"]
    return frame_bytes, metadata

def decode_image(image_bytes):
    return cv2.imdecode(np.frombuffer(image_bytes, dtype="uint8"), cv2.IMREAD_COLOR)




def serialize_data(frame_bytes, metadata):
    return msgpack.packb(
        {"frame": frame_bytes, "metadata": metadata}, use_bin_type=True
    )

def upload_image_to_minio(annotated_frame, service_name, camera_name, dir_name=None):
    return upload_base64_image_to_minio(
        img_to_base64(annotated_frame),
        service_name,
        camera_name,
        dir_name=dir_name,
    )


def img_to_base64(image_input):

    image_input = cv2.cvtColor(image_input, cv2.COLOR_RGB2BGR)
    # Convert numpy arr to pil_img
    pil_image = Image.fromarray(image_input)
    # Save pil_img into buffer
    buff = io.BytesIO()
    pil_image.save(buff, format="JPEG")

    # Convert buff to base64 str
    base64_image = base64.b64encode(buff.getvalue()).decode("utf-8")
    return base64_image



def upload_base64_image_to_minio(base64_image, event_type, cam_id, dir_name):

    client = Minio(
        MINIO_SERVER,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )

    img_id = uuid.uuid4()  # Generate a UUID
    if dir_name:
        img_name = f"{event_type}/{cam_id}/{dir_name}/{img_id}.jpg"
    else:
        img_name = f"{event_type}/{cam_id}/{img_id}.jpg"
    
    logger.debug(f"Image name: {img_name}")
    # Convert base64 string to file-like object
    image_data = base64.b64decode(base64_image)
    image_file = io.BytesIO(image_data)

    # Upload data
    try:
        result = client.put_object(
            MINIO_BUCKET_EVENTS,
            img_name,
            image_file,
            len(image_data),
            content_type="image/jpg",
        )
    except Exception as error:
        logger.debug(error)
        result = None

    if result:
        img_url = f"http://{MINIO_SERVER}/{MINIO_BUCKET_EVENTS}/{img_name}"
        logger.debug(f"Upload success at this link {img_url}")
        logger.debug("#############################################")
        return img_url

    return None
