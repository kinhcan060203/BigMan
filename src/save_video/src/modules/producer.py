import cv2
import numpy as np
import json
from confluent_kafka import Producer, KafkaException
import threading
import base64
import time
import logging as logger


def on_send_success(record_metadata):
    """Callback function that is called when a message is successfully sent to Kafka."""
    print(
        "Message sent successfully to partition {} at offset {}".format(
            record_metadata.partition, record_metadata.offset
        )
    )


def on_send_error(excp, message):
    """Callback function that is called when a message fails to be sent to Kafka."""
    print("Failed to send message: {} {}".format(excp, message))


def encode_base64_image(image: np.ndarray) -> str:
    """Encodes an image array as a base64 string."""
    retval, buffer = cv2.imencode(".jpg", image)
    return buffer.tobytes()


def send_frame_to_kafka(producer, frame_bytes, topic):
    try:
        producer.produce(
            topic,
            value=frame_bytes,
            callback=lambda err, msg: (
                on_send_success(msg) if err is None else on_send_error(err, msg)
            ),
        )
        print(f"Sent frame to Kafka topic: {topic}")
    except BufferError:
        logger.warning("Local queue is full, waiting for free space...")
        producer.poll(1)  # Poll to free up space in the queue
        time.sleep(0.1)

    # producer.flush()


def produce(cap, topic, producer):
    while True:
        ret, frame = cap.read()
        if ret:
            frame_bytes = encode_base64_image(np.array(frame))
            send_frame_to_kafka(producer, frame_bytes, topic)
        else:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            print("Reset Video")
            continue
        # time.sleep(0.1)  # Add a small delay to avoid overwhelming the broker


cap1 = cv2.VideoCapture(
    "rtsp://admin:admin%40123@192.168.10.5:554/cam/realmonitor?channel=19&subtype=1"
)
producer1 = Producer({"bootstrap.servers": "192.168.103.219:9092"})
thread1 = threading.Thread(
    target=produce,
    args=(cap1, "crowd_detection.5F_LOBBY_P8-P9_CAM_08", producer1),
    daemon=True,
)
thread1.start()

cap2 = cv2.VideoCapture(
    "rtsp://admin:admin%40123@192.168.10.5:554/cam/realmonitor?channel=18&subtype=1"
)
producer2 = Producer({"bootstrap.servers": "192.168.103.219:9092"})
thread2 = threading.Thread(
    target=produce,
    args=(cap2, "face_detection.5F_LOBBY_P8-P9_CAM_08", producer2),
    daemon=True,
)
thread2.start()

while True:
    try:
        time.sleep(100000000)
    except Exception as e:
        print(e)
        break
