import time
from confluent_kafka import Consumer, KafkaError, OFFSET_END, TopicPartition
import json
from rich import print
import asyncio
from rich.console import Console
from time import sleep
import cv2
import numpy as np

# Define Kafka consumer configuration
consumer_config = {
    "bootstrap.servers": "10.71.0.199:9092",  # Replace with your Kafka broker(s)z
    "group.id": "my-consumer-group",  # Consumer group ID
    "auto.offset.reset": "latest",  # Start consuming from the beginning of the topic
}

# Create a Kafka consumer instance
consumer = Consumer(consumer_config)
# Subscribe to the Kafka topic
topic = "illegal_intrusion.2F_ST_A_CAM_01"
consumer.subscribe([topic])  # Replace with your topic name
partition = TopicPartition(topic, 0, OFFSET_END)
consumer.assign([partition])
consumer.seek(partition)
console = Console()

with console.status("Start Consumer") as status:
    try:
        while True:
            start_time = time.time()
            # consumer.seek(partition)
            msg = consumer.poll(1)  # Poll for new messages with a timeout of 1 second
            if msg is None:
                status.update("Waiting...")
                continue

            if msg.error():
                # Handle Kafka errors
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print("Reached end of partition")
                else:
                    print("Error: {}".format(msg.error()))
            else:
                np_array = np.frombuffer(msg.value(), np.uint8)
                image = cv2.imdecode(np_array, cv2.IMREAD_UNCHANGED)
                cv2.imshow("img", image)
                fps = f"{(1 / (time.time() - start_time)):.2f}"
                key = cv2.waitKey(1)
                if key & 0xFF == ord("q"):
                    break
                # print(msg.value())
                status.update(f"Receiving with FPS: {fps}")
                pass
    except KeyboardInterrupt:
        pass

    finally:
        # Close the Kafka consumer gracefully
        # print("Closing Kafka consumer...", end="\r")
        cv2.destroyAllWindows()
        # print("Kafka consumer closed.")
        status.update("Closing kafka consumer...")
        consumer.close()
        sleep(1)
