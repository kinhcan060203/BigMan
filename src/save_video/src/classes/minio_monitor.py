from minio import Minio
from config import MINIO_HOSTNAME, MINIO_PASSWORD, MINIO_USERNAME


class MinioMonitor:
    def __init__(self):
        self.client = Minio(
            f"{MINIO_HOSTNAME}",
            access_key=MINIO_USERNAME,
            secret_key=MINIO_PASSWORD,
            secure=False,
        )
