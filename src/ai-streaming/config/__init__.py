import os
from dotenv import load_dotenv, find_dotenv
import logging

load_dotenv(find_dotenv(".env"), override=True)

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

LOGGING_LEVEL = logging.getLevelName(os.getenv("LOGGING_LEVEL", "INFO"))

MONGODB_SERVER = f"mongodb://{os.getenv('MONGO_HOST', '127.0.0.1:27017')}/"
KAFKA_SERVER = f"{os.getenv('KAFKA_SERVER', '127.0.0.1:9092')}"

