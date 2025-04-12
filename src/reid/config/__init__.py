import os
from dotenv import load_dotenv, find_dotenv
import logging

ENV = os.getenv("ENV", "dev")
if ENV == "dev":
    load_dotenv(find_dotenv(".env.dev"), override=True)
elif ENV == "prod":
    load_dotenv(find_dotenv(".env.prod"), override=True)
BROKER_IP = os.getenv("BROKER_IP", None)
BROKER_PORT = os.getenv("BROKER_PORT", None)
TOPIC = str(os.getenv("TOPIC", None))
BROKER_USERNAME = os.getenv("BROKER_USERNAME", None)
BROKER_PASSWORD = os.getenv("BROKER_PASSWORD", None)


MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", None)
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", None)
MINIO_BUCKET_EVENTS = os.getenv("MINIO_BUCKET_EVENTS", None)
MINIO_SERVER = os.getenv("MINIO_SERVER", None)

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")


GRPC_HOST = os.getenv("GRPC_HOST", "127.0.0.1")
GRPC_PORT = os.getenv("GRPC_PORT", "50051")

LPR_API_URL = os.getenv("LPR_API_URL", "http://127.0.0.1:9999/predict_img_link/")

LOGGING_LEVEL = logging.getLevelName(os.getenv("LOGGING_LEVEL", "INFO"))

SHOW = os.getenv("SHOW", "False") == "True"

MONGODB_SERVER = f"mongodb://{os.getenv('MONGO_HOST', '127.0.0.1:27017')}/"

KAFKA_SERVER = os.getenv("KAFKA_SERVER", "192.168.103.219:9092")
KAFKA_CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "test")

POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE") or "nano"
POSTGRES_HOST = os.getenv("POSTGRES_HOST") or "192.168.103.219"
POSTGRES_PORT = os.getenv("POSTGRES_PORT") or "5434"
POSTGRES_USER = os.getenv("POSTGRES_USER") or "root"
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD") or "secret"

HLS_HOST, HLS_PORT = os.getenv("HLS_SERVER", "localhost:12346").split(":")
HLS_SERVER = f"http://demo:demo@{HLS_HOST}:{HLS_PORT}/"
RTSP_SERVER = f"rtsp://{HLS_HOST}:5541"
