import base64
import cv2
import numpy as np
import random
import string


def generate_random_id(length=8):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def decode_base64_image(buffer) -> np.ndarray:
    """Decodes a base64 string to an image array."""
    if isinstance(buffer, str):
        buffer = base64.b64decode(buffer)
    image = cv2.imdecode(np.frombuffer(buffer, dtype="uint8"), cv2.IMREAD_COLOR)
    return image


def encode_image_to_base64(image: np.ndarray) -> str:
    """Encodes an image array to a base64 string."""
    _, buffer = cv2.imencode(".jpg", image)
    base64_image = base64.b64encode(buffer).decode("utf-8")
    return base64_image
