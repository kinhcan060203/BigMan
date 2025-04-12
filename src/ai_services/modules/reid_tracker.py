from collections import defaultdict, Counter
import time
from utils.logger import logger
import numpy as np
from config import LPR_HOST, LPR_PORT
import multiprocessing
import re
from utils.draw import CustomLabelAnnotator
from utils.draw import get_box_annotator
import supervision as sv


class REIDTracker(multiprocessing.Process):
    def __init__(
        self,
        iterval_loss=10,
        iou_threshold=0.2,
    ):
        self.iterval_loss = iterval_loss
        self.iou_threshold = iou_threshold
        self.input_queue = multiprocessing.Queue(maxsize=20)
        self.event_trigger_data = multiprocessing.Manager().list()
        self.last_clear_time = time.time()

        self.tracked_objects = defaultdict(
            lambda: {
                "present_start": time.time(),
                "prev_center_point": None,
                "prev_bbox": None,
                "prev_cropped_frame": None,
                "frame": None,
                "class_name": None,
            }
        )
        self.box_annotator = get_box_annotator()
        self.label_annotator = CustomLabelAnnotator(
            color=sv.Color(r=105, g=105, b=104),
            text_position=sv.Position.TOP_RIGHT,
            text_scale=0.4,
        )
        
        super(REIDTracker, self).__init__()

    def run(self):
        while True:
            detections, frame_full = self.input_queue.get()
            if detections.tracker_id is None or detections.xyxy is None:
                continue
            self.update_track_dict(detections, frame_full)



    def update_track_dict(self, detections, frame_full):
        for idx, (obj_id, bbox) in enumerate(
            zip(detections.tracker_id, detections.xyxy)
        ):
            is_reid = self.trigger_tracking(obj_id, bbox, frame_full, detections[idx])
            if is_reid:
                self.add_event_trigger(obj_id, "active")
        self._handle_lost_objects(set(detections.tracker_id))
        return self.tracked_objects


    def _handle_lost_objects(self, active_object_ids):
        for obj_id in (
            set(self.tracked_objects)
            - active_object_ids
        ):
            if (
                time.time() - self.tracked_objects[obj_id]["present_start"]
                > self.iterval_loss
            ):
                self.add_event_trigger(obj_id, "lost")
                self.tracked_objects.pop(obj_id)

                
    def add_event_trigger(self, obj_id, event_type):
        data = {
            "type": event_type,
            "source_service": "reid",
            "tracker_id": str(obj_id),
            "timestamp": time.time(),
            "bbox": self.tracked_objects[obj_id]["prev_bbox"],
            "cropped_frame": self.tracked_objects[obj_id]["prev_cropped_frame"],
            "annotated_frame": self.tracked_objects[obj_id]["frame"],
            "class_name": self.tracked_objects[obj_id]["class_name"],
        }
        self.event_trigger_data.append(data)

    def empty_event_trigger_data(self):
        self.event_trigger_data[:] = []
    def annotate_frame(self, frame, obj_id, detection):
        annotated_frame = frame.copy()
        class_name = detection.data["class_name"][0]
        self.box_annotator.annotate(
            scene=annotated_frame, detections=detection
        )

        label = f"ID: {obj_id}\n" f"{class_name}\n"
        self.label_annotator.annotate(annotated_frame, detection, [label])
        return annotated_frame

    def trigger_tracking(self, obj_id, bbox, frame_full, detection):
        annotated_frame = self.annotate_frame(frame_full, obj_id, detection)
        class_name = detection.data["class_name"][0]
        prev_bbox = self.tracked_objects[obj_id]["prev_bbox"]
        bbox = list(map(int, bbox))
        cropped_frame = frame_full[
            bbox[1] : bbox[3], bbox[0] : bbox[2]
        ]
        self.tracked_objects[obj_id]["present_start"] = time.time()
        if prev_bbox is None:
            self.tracked_objects[obj_id]["prev_bbox"] = bbox
            self.tracked_objects[obj_id]["prev_cropped_frame"] = cropped_frame
            self.tracked_objects[obj_id]["frame"] = annotated_frame
            self.tracked_objects[obj_id]["class_name"] = class_name

        else:
            iou = self.calculate_iou(bbox, prev_bbox)
            if iou < self.iou_threshold:
                self.tracked_objects[obj_id]["prev_bbox"] = bbox
                self.tracked_objects[obj_id]["prev_cropped_frame"] = cropped_frame
                self.tracked_objects[obj_id]["frame"] = annotated_frame
                self.tracked_objects[obj_id]["class_name"] = class_name
            else:
                return False
            
        return True

    def calculate_iou(self, bbox1, bbox2):
        bbox1 = np.array(bbox1)
        bbox2 = np.array(bbox2)

        x_left = max(bbox1[0], bbox2[0])
        y_top = max(bbox1[1], bbox2[1])
        x_right = min(bbox1[2], bbox2[2])
        y_bottom = min(bbox1[3], bbox2[3])

        intersection_area = max(0, x_right - x_left) * max(0, y_bottom - y_top)

        bbox1_area = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        bbox2_area = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union_area = bbox1_area + bbox2_area - intersection_area

        iou = intersection_area / union_area if union_area > 0 else 0.0

        return iou