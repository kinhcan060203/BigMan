from utils.functions import event_trigger
from modules.kafka import publish_image_to_kafka
import threading
import time
import redis
import cv2
import numpy as np
from collections import defaultdict

count_start_time = time.time()
crossed_in_all = defaultdict(lambda: defaultdict(dict))
crossed_out_all = defaultdict(lambda: defaultdict(dict))

def handle_vehicle_counting(
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
    global count_start_time, crossed_in_all, crossed_out_all
    if vga_drawer:
        annotated_frame = vga_drawer.box_annotator.annotate(scene=frame, detections=detections)
    else:
        annotated_frame = frame.copy()
    for line_annotator, line in zip(
        vga_drawer.line_annotator, vga_drawer.line
    ):

        crossed_in, crossed_out = line.trigger(detections)
        line_annotated_frame = line_annotator.annotate(annotated_frame, line)
        line_name = line.name
        if detections.tracker_id is None:
            break
        for idx, (obj_id, is_crossed) in enumerate(zip(detections.tracker_id, crossed_in)):
            if is_crossed:
                crossed_in_all[line_name][obj_id] = {
                    "obj_id": obj_id,
                    "timestamp": time.time(),
                    "direction": "in",
                    "annotated_frame": line_annotated_frame,
                    "class_name": detections.data["class_name"][idx] if "class_name" in detections.data else None,
                }
        for idx, (obj_id, is_crossed) in enumerate(zip(detections.tracker_id, crossed_out)):
            if is_crossed:
                crossed_out_all[line_name][obj_id] = {
                    "obj_id": obj_id,
                    "timestamp": time.time(),
                    "direction": "out",
                    "annotated_frame": line_annotated_frame,
                    "class_name": detections.data["class_name"][idx] if "class_name" in detections.data else None,
                }
        if (crossed_in_all or crossed_out_all) and not trigger_thread[0].is_alive():
            trigger_thread[0] = threading.Thread(
                target=event_trigger,
                args=(
                    camera_info,
                    "vehicle_counting",
                    line_annotated_frame,
                    None,
                    kafka_producer,
                    db,
                    15,
                    {},
                    {
                        "line_name": line_name,
                        "crossed_in_all": crossed_in_all[line_name],
                        "crossed_out_all": crossed_out_all[line_name],
                        "start_time": count_start_time,
                        "end_time"  : time.time(),
                    },
                ),
            )
            crossed_in_all.clear()
            crossed_out_all.clear()
            count_start_time = time.time()
            trigger_thread[0].start()
    
    publish_image_to_kafka(
        producer=kafka_producer,
        topic=f"vehicle_counting.{kafka_topic}",
        img=annotated_frame,
    )


