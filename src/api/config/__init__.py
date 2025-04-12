import json
import os
from os.path import join
from dotenv import load_dotenv, find_dotenv

load_dotenv(override=True)

LOGGING_LEVEL= os.getenv("LOGGING_LEVEL", "INFO")

MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", None)
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", None)
MINIO_BUCKET_EVENTS = os.getenv("MINIO_BUCKET_EVENTS", None)
MINIO_SERVER = os.getenv("MINIO_SERVER", None)

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
WS_ENDPOINT = os.getenv("WS_ENDPOINT", "ws://127.0.0.1:8001/events")

REID_HOST = os.getenv("REID_HOST", "127.0.0.1")
REID_PORT = os.getenv("REID_PORT", "5123")

LPR_HOST = os.getenv("LPR_HOST", "127.0.0.1")
LPR_PORT = os.getenv("LPR_PORT", "9999")


KAFKA_SERVER = os.getenv("KAFKA_SERVER", "127.0.0.1:9092")

CROWD_MINIMUM_NUMBER = int(os.getenv("CROWD_MINIMUM_NUMBER", "5"))
CROWD_MINIMUM_DISTANCE = int(os.getenv("CROWD_MINIMUM_DISTANCE", "200"))

MONGO_DATABASE = os.getenv("MONGO_DATABASE", "nano")
MONGO_HOST = os.getenv("MONGO_HOST", "0.0.0.0")
MONGO_PORT = os.getenv("MONGO_PORT", "5432")
MONGO_USER = os.getenv("MONGO_USER", "root")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "secret")
MONGO_URI = (
     f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
)
HLS_HOST, HLS_PORT = os.getenv("HLS_SERVER", "localhost:12346").split(":")

API_PORT = os.getenv("API_PORT", "8000")


HLS_HOST, HLS_PORT = os.getenv("HLS_SERVER", "localhost:12346").split(":")

HLS_SERVER = f"http://demo:demo@{HLS_HOST}:{HLS_PORT}/"
HTTP_STREAMING_SERVER = (
    f"http://{os.getenv('HTTP_STREAMING_SERVER', '192.168.103.219:8081')}"
)
