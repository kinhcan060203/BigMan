import cv2
import numpy as np
import msgpack
from utils.logger import logger


def decode_image(image_bytes):
    return cv2.imdecode(np.frombuffer(image_bytes, dtype="uint8"), cv2.IMREAD_COLOR)

def encode_image(image):
    frame_encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])[1]
    return frame_encoded.tobytes()


def serialize_data(frame_bytes, metadata):
    return msgpack.packb(
        {"frame": frame_bytes, "metadata": metadata}, use_bin_type=True
    )