from collections import defaultdict, Counter
import time
from scipy.spatial import distance
from utils.common import img_to_base64
from utils.logger import logger
import requests
import cv2
import numpy as np
import base64
from config import LPR_HOST, LPR_PORT
import multiprocessing
import re
from utils.draw import CustomLabelAnnotator
from utils.draw import get_box_annotator
import supervision as sv


class LPRTracker(multiprocessing.Process):
    def __init__(
        self,
        interval_track=6,
        iterval_summary=1,
    ):
        super(LPRTracker, self).__init__()
        self.interval_track = interval_track
        self.iterval_summary = iterval_summary
        self.input_queue = multiprocessing.Queue(maxsize=20)
        self.event_trigger_data = multiprocessing.Manager().list()
        self.summary_objects = multiprocessing.Manager().dict()
        self.triggered_ids = {}
        self.triggered_lpr = {}
        self.last_clear_time = time.time()
        self.box_annotator = get_box_annotator()
        self.label_annotator = CustomLabelAnnotator(
            color=sv.Color(r=105, g=105, b=104),
            text_position=sv.Position.TOP_RIGHT,
            text_scale=0.4,
        )
        self.buffer_objects = defaultdict(
            lambda: {
                "license_plate": [],
                "plate_img": [],
                "frame": [],
                "cropped_frame": [],
                "v_color": [],
                "class_name": [],
                "detection": [],
                "timestamp": [],
            }
        )

        self.position_tracker = defaultdict(
            lambda: {
                "prev_fixed_point": None,
                "idle_start": time.time(),
                "idle_loop": time.time(),
            }
        )
        self.tracked_objects = defaultdict(
            lambda: {
                "present_start": time.time(),
                "summary_start": time.time(),
                "lpr_start": time.time() - 3,
            }
        )

    def run(self):
        while True:
            detections, frame_full = self.input_queue.get()
            if detections.tracker_id is None or detections.xyxy is None:
                continue
            self.update_track_dict(detections, frame_full)

    def _check_and_summary(self, obj_id):
        if (
            time.time() - self.tracked_objects[obj_id]["summary_start"]
            > self.iterval_summary
        ):
            self.tracked_objects[obj_id]["summary_start"] = time.time()
            self.update_summary_trigger(obj_id)

    def _check_and_update_lpr(self, obj_id):
        for obj_id in self.tracked_objects:
            if obj_id not in self.triggered_ids:
                if time.time() - self.tracked_objects[obj_id]["lpr_start"] > 1:
                    self.tracked_objects[obj_id]["lpr_start"] = time.time()
                    self.trigger_update_lpr(obj_id=obj_id)

    def update_track_dict(self, detections, frame_full):
        for idx, (obj_id, bbox) in enumerate(
            zip(detections.tracker_id, detections.xyxy)
        ):
            self.tracked_objects[obj_id]

            if obj_id not in self.triggered_ids:
                self._process_object(obj_id, frame_full, detections[idx])
            if obj_id in self.buffer_objects:
                self._check_and_update_lpr(obj_id)
                self._check_and_summary(obj_id)
        self._handle_lost_objects(set(detections.tracker_id))
        return self.tracked_objects

    def _bbox_vga_to_hd(self, frame_full, vga_bbox):
        ratios = frame_full.shape[1] / 640, frame_full.shape[0] / 640
        return vga_bbox * np.array([*ratios, *ratios])

    def trigger_update_lpr(self, obj_id):
        import math

        if obj_id in self.buffer_objects:
            step = math.ceil(len(self.buffer_objects[obj_id]["cropped_frame"]) / 4)
            try:
                if self.buffer_objects[obj_id]["license_plate"]:
                    index = self.buffer_objects[obj_id]["license_plate"].index(None)
                    for idx in range(
                        index, len(self.buffer_objects[obj_id]["cropped_frame"]), step
                    ):

                        license_plate, plate_img, v_color = process_license_plate(
                            self.buffer_objects[obj_id]["cropped_frame"][idx]
                        )
                        self.buffer_objects[obj_id]["license_plate"][
                            idx
                        ] = license_plate
                        self.buffer_objects[obj_id]["plate_img"][idx] = plate_img
                        self.buffer_objects[obj_id]["v_color"][idx] = v_color

            except Exception as e:
                pass

    def _process_object(self, obj_id, frame_full, detection):
        full_bbox = list(map(int, detection.xyxy[0]))
        center_points = (full_bbox[0] + full_bbox[2]) / 2, (
            full_bbox[1] + full_bbox[3]
        ) / 2
        is_trigger = self.trigger_tracking(obj_id, *center_points)
        cropped_frame = frame_full[
            full_bbox[1] : full_bbox[3], full_bbox[0] : full_bbox[2]
        ]
        detection.xyxy = np.array([full_bbox], dtype=np.float32)

        class_name = detection.data["class_name"][0]
        if is_trigger:
            if obj_id not in self.buffer_objects:
                license_plate, plate_img, v_color = process_license_plate(cropped_frame)
                self.tracked_objects[obj_id]["present_start"] = time.time()
                if not license_plate or len(license_plate) < 3:
                    return
                else:
                    self._update_buffer(
                        obj_id,
                        detection,
                        frame_full,
                        cropped_frame,
                        class_name=class_name,
                        license_plate=license_plate,
                        plate_img=plate_img,
                        v_color=v_color,
                    )
                    self.update_summary_trigger(obj_id)

            else:
                self._update_buffer(
                    obj_id, detection, frame_full, cropped_frame, class_name=class_name
                )
        elif obj_id not in self.buffer_objects:
            self.tracked_objects[obj_id]["present_start"] = time.time()

        if (
            time.time() - self.tracked_objects[obj_id]["present_start"]
            > self.interval_track
        ):
            self.add_event_trigger(obj_id, "timeout")

    def update_summary_trigger(self, obj_id):
        if not self.buffer_objects[obj_id]["license_plate"]:
            return
        lpr_buffer = self.buffer_objects[obj_id]["license_plate"]
        if lpr_buffer:

            lpr_valid, lpr_invalid = filter_license_plate(lpr_buffer)
            if lpr_valid:
                license_plate = lpr_valid.most_common(1)[0][0]
            elif lpr_invalid:
                license_plate = lpr_invalid.most_common(1)[0][0]
            else:
                return
            self.summary_objects[obj_id] = {"license_plate": license_plate}

    def _update_buffer(
        self,
        obj_id,
        detection,
        frame,
        cropped_frame,
        class_name,
        license_plate=None,
        plate_img=None,
        v_color=None,
    ):
        buffer = self.buffer_objects[obj_id]
        buffer["frame"].append(frame)
        buffer["cropped_frame"].append(cropped_frame)
        buffer["license_plate"].append(license_plate)
        buffer["plate_img"].append(plate_img)
        buffer["v_color"].append(v_color)
        buffer["class_name"].append(class_name)
        buffer["detection"].append(detection)
        buffer["timestamp"].append(time.time())

    def _handle_lost_objects(self, active_object_ids):
        for obj_id in (
            set(self.tracked_objects)
            - active_object_ids
            - set(self.triggered_ids.keys())
        ):
            self._check_and_summary(obj_id)
            if (
                time.time() - self.tracked_objects[obj_id]["present_start"]
                > self.interval_track
            ):
                self.add_event_trigger(obj_id, "lost")

        to_delete = [
            obj_id
            for obj_id, last_time in self.triggered_ids.items()
            if time.time() - last_time > 30
        ]

        for obj_id in to_delete:
            self.delete_data(obj_id)

    def delete_data(self, obj_id):
        self.triggered_ids.pop(obj_id, None)
        self.triggered_lpr.pop(obj_id, None)
        self.buffer_objects.pop(obj_id, None)
        self.tracked_objects.pop(obj_id, None)
        self.summary_objects.pop(obj_id, None)

    def add_event_trigger(self, obj_id, event_type):

        buffer = self.buffer_objects[obj_id]
        lpr_valid, lpr_invalid = filter_license_plate(buffer["license_plate"])

        if not lpr_valid:
            if event_type == "lost":
                self.delete_data(obj_id)
            return
        color_results = buffer["v_color"]
        class_name_results = buffer["class_name"]
        license_plate = lpr_valid.most_common(1)[0][0]

        if license_plate in self.triggered_lpr.values():
            if event_type == "lost":
                self.delete_data(obj_id)
            return

        v_color = Counter(color_results).most_common(1)[0][0]
        class_name = Counter(class_name_results).most_common(1)[0][0]

        idx = buffer["license_plate"].index(license_plate)
        plate_img = buffer["plate_img"][idx]

        label = f"{license_plate}\n" f"{class_name}\n" f"{v_color}\n"
        frame = buffer["frame"][idx]
        detection = buffer["detection"][idx]
        annotated_frame = frame.copy()

        self.label_annotator.annotate(annotated_frame, detection, [label])
        self.box_annotator.annotate(annotated_frame, detection)
        bbox = list(detection.xyxy[0])
        timestamp = buffer["timestamp"][idx]
        cropped_frame = buffer["cropped_frame"][idx]
        self.event_trigger_data.append(
            {
                "obj_id": obj_id,
                "type": event_type,
                "data": {
                    "license_plate": license_plate,
                    "plate_img": plate_img,
                    "annotated_frame": annotated_frame,
                    "frame": frame,
                    "bbox": bbox,
                    "timestamp": timestamp,
                    "v_color": v_color,
                    "cropped_frame": cropped_frame,
                    "class_name": class_name,
                },
            }
        )
        self.triggered_lpr[obj_id] = license_plate
        self.triggered_ids[obj_id] = time.time()

    def empty_event_trigger_data(self):
        self.event_trigger_data[:] = []

    def trigger_tracking(self, obj_id, x, y):

        prev_fixed_point = self.position_tracker[obj_id]["prev_fixed_point"]
        if prev_fixed_point is None:
            prev_fixed_point = np.array([x, y])
            self.position_tracker[obj_id]["prev_fixed_point"] = prev_fixed_point
            self.position_tracker[obj_id]["idle_start"] = time.time()
        else:
            distance_fixed = distance.euclidean([x, y], prev_fixed_point)
            self.position_tracker[obj_id]["prev_fixed_point"] = prev_fixed_point

            if distance_fixed > 400:
                prev_fixed_point = np.array([x, y])
                self.position_tracker[obj_id]["prev_fixed_point"] = prev_fixed_point
                self.position_tracker[obj_id]["idle_start"] = time.time()
            elif time.time() - self.position_tracker[obj_id]["idle_start"] > 2:
                if time.time() - self.position_tracker[obj_id]["idle_loop"] > 5:
                    self.position_tracker[obj_id]["idle_loop"] = time.time()
                    return True
                return False
        self.position_tracker[obj_id]["idle_loop"] = time.time()
        return True


def process_license_plate(annotated_frame):
    try:
        response = find_license_plate(img_to_base64(annotated_frame))
        license_number = response.get("license_number")
        plate_img = base64_to_cv2_image(response.get("plate"))
        color = response.get("color")

        return license_number, plate_img, ""
    except Exception as e:
        logger.error(f"Error in process_license_plate: {e}")
        return None, None, None


def find_license_plate(img_base64):
    url = f"http://{LPR_HOST}:{LPR_PORT}/predict/base64/"
    try:
        response = requests.post(
            url, json={"image": img_base64, "type": "car"}, timeout=10
        )
        return response.json() if response.status_code == 200 else {}
    except requests.RequestException as e:
        logger.error(f"Error finding license plate: {e}")
        return {}


def base64_to_cv2_image(base64_string):
    if base64_string:
        return cv2.imdecode(
            np.frombuffer(base64.b64decode(base64_string), np.uint8), cv2.IMREAD_COLOR
        )
    return None


def filter_license_plate(lpr_buffer):
    pattern = r"^[1-9][0-9][A-Z][A-Z0-9]\d{3}\d{0,3}$"
    invalid_lpr = []
    valid_lpr = []
    for lpr in lpr_buffer:
        if lpr:
            if re.match(pattern, lpr):
                valid_lpr.append(lpr)
            else:
                invalid_lpr.append(lpr)
    valid_lpr = Counter(valid_lpr)
    invalid_lpr = Counter(invalid_lpr)
    return valid_lpr, invalid_lpr
