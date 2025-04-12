import cv2
import numpy as np
import msgpack
from utils.logger import logger
from PIL import Image
import io
import base64
import supervision as sv

def decode_image(image_bytes):
    return cv2.imdecode(np.frombuffer(image_bytes, dtype="uint8"), cv2.IMREAD_COLOR)


def img_to_base64(image_input):

    image_input = cv2.cvtColor(image_input, cv2.COLOR_RGB2BGR)
    pil_image = Image.fromarray(image_input)
    buff = io.BytesIO()
    pil_image.save(buff, format="JPEG")

    base64_image = base64.b64encode(buff.getvalue()).decode("utf-8")
    return base64_image



def get_detections(metadata):
    if metadata["detections"]:
        return sv.Detections(
            np.array(metadata["detections"]),
            class_id=np.array(metadata["class_ids"]),
            confidence=np.array(metadata["confidences"]),
            data=metadata["data"],
            tracker_id=np.array(metadata["track_ids"]),
        )

    return sv.Detections.empty()

def get_full_hd_image(redis_client, detections, frame, ikey):
    bbox = detections.xyxy
    try:
        buffer = redis_client.get(ikey)
        if isinstance(buffer, bytes):
            frame_full = cv2.imdecode(
                np.frombuffer(buffer, dtype="uint8"), cv2.IMREAD_COLOR
            )
            ratio_width = frame_full.shape[1] / 640
            ratio_height = frame_full.shape[0] / 480
            bbox = bbox * np.array(
                [ratio_width, ratio_height, ratio_width, ratio_height]
            )

            return frame_full, bbox, True
        else:
            return frame, bbox, False
    except Exception as e:
        logger.error(f"Error in get_full_hd_image: {e}")
        import rich
        rich.console.Console().print_exception()
        return frame, bbox, False


def base64_to_cv2_image(base64_string):
    if base64_string is None:
        return None
    img_data = base64.b64decode(base64_string)
    np_array = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

    return img