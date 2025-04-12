from utils.functions import  event_trigger
from modules.kafka import publish_image_to_kafka
import threading
import numpy as np
from utils.common import get_full_hd_image
from utils.draw import DrawerObject
import supervision as sv
import queue
import cv2
           
def handle_license_plate(
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
    frame, bbox, is_org = get_full_hd_image(
        redis_client, detections, frame.copy(), ikey
    )
    annotated_frame = frame.copy()
    if is_org:
        drawer = org_drawer
        detections = sv.Detections(
            xyxy=bbox,
            class_id=detections.class_id,
            mask=detections.mask,
            tracker_id=detections.tracker_id,
            data=detections.data,
        )
        annotated_frame = org_drawer.box_annotator.annotate(
            scene=annotated_frame, detections=detections
        )

    else:
        drawer = org_drawer
        annotated_frame = vga_drawer.box_annotator.annotate(
            scene=annotated_frame, detections=detections
        )

    if drawer.zone_bottom_center and drawer.zone_annotator:
        for zone_center, zone_annotator in zip(
            drawer.zone_bottom_center, drawer.zone_annotator
        ):
            detections_filtered = detections[zone_center.trigger(detections=detections)]
            annotated_frame = zone_annotator.annotate(scene=annotated_frame)

            try:
                if tracker.input_queue.full():
                    tracker.input_queue.get_nowait()
                tracker.input_queue.put_nowait((detections_filtered, frame))
            except queue.Empty:
                pass

            xyxy = []
            lprs = []
            obj_ids = []
            timestamps = []
            cls_frames = []
            target_frames = []
            plate_imgs = []
            cropped_frames = []
            types = []
            class_names = []
            for event in tracker.event_trigger_data:
                obj_ids.append(event["obj_id"])
                types.append(event["type"])
                data = event["data"]
                lprs.append(data["license_plate"])
                xyxy.append(data["bbox"])
                timestamps.append(data["timestamp"])
                cls_frames.append(data["frame"])
                cropped_frames.append(data["cropped_frame"])
                target_frame = data["annotated_frame"]
                target_frames.append(target_frame)
                plate_imgs.append(data["plate_img"])
                class_names.append(data["class_name"])
            if not trigger_thread[0].is_alive() and lprs:
                print("Triggering event for license plate detection")
                trigger_thread[0] = threading.Thread(
                    target=event_trigger,
                    args=(
                        camera_info,
                        "license_plate",
                        annotated_frame,
                        None,
                        kafka_producer,
                        db,
                        0,
                        {
                            "xyxy": xyxy,
                            "cls_frames": cls_frames,
                            "target_frames": target_frames,
                        },
                        {
                            "lprs": lprs,
                            "obj_ids": obj_ids,
                            "timestamps": timestamps,
                            "plate_imgs": plate_imgs,
                            "cropped_frames": cropped_frames,
                            "types": types,
                            "class_names": class_names,
                        },
                    ),
                )
                trigger_thread[0].start()
            tracker.empty_event_trigger_data()

    publish_image_to_kafka(
        producer=kafka_producer,
        topic=f"license_plate.{kafka_topic}",
        img=annotated_frame,
    )
