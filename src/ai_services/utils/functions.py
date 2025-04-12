import numpy as np
import cv2

from modules.kafka import pub_kafka, clean_message_producer, serialize_data
from utils.minio.upload_minio import upload_base64_image_to_minio
from utils.common import img_to_base64
import datetime
from time import sleep
import json
import uuid
from utils.logger import logger
import io
import cv2
from config import  WS_ENDPOINT
import msgpack
import asyncio
import websockets



def event_trigger(
    camera_info,
    event_type,
    annotated_frame,
    stop_event,
    producer,
    db,
    time_limit=15,
    annotation=None,
    service_params=None,
    
):
    try:
        camera_name = camera_info["camera_name"]
        current_time = datetime.datetime.now()
        event_item = None
        event_id = uuid.uuid4()
        if event_type == "license_plate":
            for i in range(len(service_params["lprs"])):

                plate_img = service_params["plate_imgs"][i]
                target_frame = annotation["target_frames"][i]
                cropped_frame = service_params["cropped_frames"][i]
                timestamp = service_params["timestamps"][i]
                obj_id = service_params["obj_ids"][i]
                bbox = annotation["xyxy"][i]
                action_type = service_params["types"][i]
                class_name = service_params["class_names"][i]
                if plate_img is not None:

                    full_thumb_path = upload_image_to_minio(
                        target_frame, event_type, camera_name, dir_name="full"
                    )
                    target_thumb_path = upload_image_to_minio(
                        cropped_frame, event_type, camera_name, dir_name="target"
                    )
                    plate_thumb_path = upload_image_to_minio(
                        plate_img, event_type, camera_name, dir_name="plate"
                    )
                    lpr = service_params["lprs"][i]
                    trigger_reid(
                        service_name=event_type,
                        camera_name=camera_name,
                        cropped_images=[cropped_frame],
                        metadatas=[{"lpr": lpr,  "timestamp": timestamp, "tracker_id": str(obj_id), "source_service": "license_plate", "type": 'active', "class_name": class_name}],
                        annotated_frames=[annotated_frame],
                        stop_event=stop_event,
                        producer=producer,
                        time_limit=0,
                    )
                    event_id, event_item = insert_db_event_item(
                        db,
                        event_type,
                        camera_name,
                        current_time,
                        current_time,
                        full_thumb_path,
                        target_thumb_path,
                        data={
                            "plate_thumb_path": plate_thumb_path,
                            "target_label": lpr,
                            "metadata": {},
                        },
                    )
            if event_item is None:
                return
       
        elif event_type == "vehicle_counting":
            full_thumb_path = upload_image_to_minio(
                annotated_frame, event_type, camera_name, dir_name="full"
            )
            target_in = []
            target_out = []

            for obj_id, crossed_in_data in service_params["crossed_in_all"].items():
                target_thumb_path = upload_image_to_minio(
                    crossed_in_data["annotated_frame"], event_type, camera_name, dir_name="target"
                )
                class_name = crossed_in_data["class_name"]
                target_in.append({
                    "thumb_path": target_thumb_path,
                    "class_name": class_name,
                    "timestamp": crossed_in_data["timestamp"],
                })
                

            for obj_id, crossed_out_data in service_params["crossed_out_all"].items():
                target_thumb_path = upload_image_to_minio(
                    crossed_out_data["annotated_frame"], event_type, camera_name, dir_name="target"
                )
                class_name = crossed_out_data["class_name"]
                target_out.append({
                    "thumb_path": target_thumb_path,
                    "class_name": class_name,
                    "timestamp": crossed_out_data["timestamp"],
                })

            
            start_time = service_params["start_time"]
            end_time = service_params["end_time"]
            start_time = datetime.datetime.fromtimestamp(start_time)
            end_time = datetime.datetime.fromtimestamp(end_time)
            event_id, event_item = insert_db_event_item(
                db,
                event_type,
                camera_name,
                start_time,
                end_time,
                full_thumb_path,
                full_thumb_path,
                data={
                    "line_name": service_params["line_name"],
                    "counted_in": len(service_params["crossed_in_all"]),
                    "counted_out": len(service_params["crossed_out_all"]),
                    "metadata": {
                        "_in": target_in,
                        "_out": target_out,
                
                    },
                },
            )

            if event_item is None:
                return


        if event_item:
            logger.info(
                f"Success trigger: {event_type} for camera {camera_name}, EID={event_id}"
            )

        wait_for_stop_event(stop_event, time_limit)

    except Exception as e:
        import rich
        rich.console.Console().print_exception()
        logger.error(f"Error in event_trigger: {e} {event_type} {camera_name}")
        sleep(2)


def trigger_reid(
    service_name,
    camera_name,
    cropped_images,
    metadatas,
    annotated_frames,
    stop_event,
    producer,
    time_limit=15,
):
    try:
        for cropped_image, metadata, annotated_frame in zip(cropped_images, metadatas, annotated_frames):
            cropped_frame_bytes = cv2.imencode(".jpg", cropped_image, [int(cv2.IMWRITE_JPEG_QUALITY), 80])[
                1
            ].tobytes()
            annotated_frame_bytes = cv2.imencode(".jpg", annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])[
                1
            ].tobytes()
            metadata["camera_name"] = camera_name
            metadata["service_name"] = service_name
            metadata["annotated_frame"] = annotated_frame_bytes
            buffer = serialize_data(cropped_frame_bytes, metadata)
            # size = len(buffer) / 1024 / 1024
            # print(size)
            pub_kafka(producer,"reid", None, buffer)
        wait_for_stop_event(stop_event, time_limit)

    except Exception as e:
        import rich
        rich.console.Console().print_exception()
        logger.error(f"Error in trigger_reid: {e} {camera_name}")
        sleep(2)




def upload_image_to_minio(annotated_frame, event_type, camera_name, dir_name=None):
    return upload_base64_image_to_minio(
        img_to_base64(annotated_frame),
        event_type,
        camera_name,
        dir_name=dir_name,
    )


def insert_db_event_item(
    db, event_type, camera_name, start_time, end_time, full_thumb_path, target_thumb_path, data
):  
    item_data = {
        "event_type":event_type,
        "camera_id":camera_name,
        "start_time":start_time,
        "end_time":end_time,
        "full_thumbnail_path":full_thumb_path,
        "target_thumbnail_path":target_thumb_path,
        "is_reviewed":False,
        "has_snapshot":True,
        "data":data,
    }
    new_event = db["event"].insert_one(item_data)
    asyncio.run(send_ws(item_data))
    return new_event.inserted_id, item_data




async def send_ws(event_item):
    data = clean_message_producer(event_item)
    try:
        async with websockets.connect(WS_ENDPOINT) as websocket:
            await websocket.send(json.dumps(data))
    except Exception as e:
        logger.error(f"Error in send_ws: {e}")


def wait_for_stop_event(stop_event, time_limit):
    for _ in range(time_limit):
        if stop_event and stop_event.is_set():
            break
        sleep(1)




