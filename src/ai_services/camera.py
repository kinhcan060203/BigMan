from asyncio import Queue
import asyncio
import threading
import cv2
from time import sleep
import numpy as np
from utils.logger import logger
import requests
from confluent_kafka import Consumer, KafkaError, TopicPartition, Producer, OFFSET_END
import msgpack
from utils.common import get_detections
from modules.kafka import deserialize_data
from multiprocessing.shared_memory import SharedMemory


class FrameQueue(threading.Thread):
    def __init__(self, consumer_config, topic):
        super().__init__()
        self.topic = topic
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        self.img_queue = asyncio.Queue(maxsize=40)
        self.consumer_config = consumer_config
        self.is_running = True
        self.consumer = self.init_kafka(topic)

    def init_kafka(self, topic):
        consumer = Consumer(
            {**self.consumer_config, "group.id": "ai_services." + self.topic}
        )
        partition = TopicPartition("stream." + topic, 0, OFFSET_END)
        consumer.assign([partition])
        consumer.seek(partition)
        return consumer
    
    def run(self):

        import time
        start = time.time()
        while True:
            try:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None:
                    # if self.topic == "Bullet142":
                    #     print("No message received from Bullet142")
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.debug(msg.error())
                        break
                ikey = msg.key().decode("utf-8")
                img, metadata = deserialize_data(msg.value())
                if img is None or metadata.get("detections", None) is None:
                    continue

                img = cv2.imdecode(np.frombuffer(img, dtype=np.uint8), cv2.IMREAD_COLOR)
                detections = get_detections(metadata)
                if self.img_queue.full():
                    self.img_queue.get_nowait()
                self.img_queue.put_nowait((img, detections, ikey))

            except KeyboardInterrupt:
                break
            except Exception as e:
                import rich
                rich.console.Console().print_exception()    
                logger.error(f"Error in camera {e}")
                break
    def stop(self):
        self.is_running = False
        self.consumer.close()
        self.join()

    def get(self):
        
        if self.img_queue.empty():
            return False, (None, None, None)
        return True, self.img_queue.get_nowait()
    

