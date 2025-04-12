from utils.functions import trigger_reid
from modules.kafka import publish_image_to_kafka

import threading
import numpy as np
from utils.common import get_full_hd_image
from utils.draw import DrawerObject
import supervision as sv
import queue
import cv2

def handle_reid(
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


            if not trigger_thread[0].is_alive():

                cropped_frames = []
                annotated_frames = []
                metadatas = []

                for metadata in tracker.event_trigger_data:
                    # import os
                    # os.makedirs("test", exist_ok=True)
                    # folder = f'test/{metadata["tracker_id"]}'
                    # os.makedirs(folder, exist_ok=True)
                    # index = len(os.listdir(folder))
                    # cv2.imwrite(f"{folder}/{index}.{metadata['type']}.jpg", metadata["annotated_frame"])
                    
                    cropped_frames.append(metadata["cropped_frame"])
                    annotated_frames.append(metadata["annotated_frame"])
                    metadata.pop("cropped_frame")
                    metadata.pop("annotated_frame")
                    metadatas.append(metadata)
                if metadatas:
                    trigger_thread[0] = threading.Thread(
                        target=trigger_reid,
                        args=(
                            "reidentify",
                            camera_info["camera_name"],
                            cropped_frames, 
                            metadatas,
                            annotated_frames,
                            None,
                            kafka_producer,
                            5,
                        ),
                    )
                    trigger_thread[0].start()
                    tracker.empty_event_trigger_data()
    publish_image_to_kafka(
        producer=kafka_producer,
        topic=f"reid.{kafka_topic}",
        img=annotated_frame,
    )
