import cv2
import numpy as np
import msgpack
from utils.logger import logger


def pub_kafka_metadata(producer, topic, key, value):
    try:
        producer.produce(topic, key=key, value=value)
    except BufferError:
        logger.warning("Local queue is full, waiting for free space...")
        producer.flush()
    except BrokenPipeError:
        logger.info("Broken pipe error occurred. Check your Kafka connection.")
    except Exception as e:
        logger.info(f"An error occurred: {e}")
