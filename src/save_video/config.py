import os
from dotenv import load_dotenv

load_dotenv(".env.prod", override=True)

KAFKA_HOSTNAME = os.environ.get("KAFKA_HOST", None)
MINIO_USERNAME = os.environ.get("MINIO_USERNAME", "meme")
MINIO_PASSWORD = os.environ.get("MINIO_PASSWORD", "meme@123")
MINIO_HOSTNAME = f'{os.environ.get("MINIO_HOST", "localhost")}:{os.environ.get("MINIO_PORT", "9000")}'
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", 5432)
POSTGRES_USER = os.environ.get("POSTGRES_USER", "root")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "secret")
LENGTH_VIDEO = os.environ.get("LENGTH_VIDEO")
REDIS_HOST = os.environ.get("REDIS_HOST", "")
REDIS_PORT = os.environ.get("REDIS_PORT", "")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "")
SERVER = os.getenv("SERVER_IP") or "10.71.0.199"
