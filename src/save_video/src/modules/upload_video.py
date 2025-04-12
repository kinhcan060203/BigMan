from src.modules.check_bucket import check_bucket
from src.modules.check_con import check_minio_health
from src.modules.set_policy_bucket import set_policy_bucket
import logging as logger
from config import MINIO_HOSTNAME


def upload_video_to_minio(
    hostname, client, bucket_name, object_path, object_name, type
):

    # Check the connection to the MinIO server
    check_status = check_minio_health(MINIO_HOSTNAME)
    if check_status == True:
        if check_bucket(client, bucket_name) == True:
            logger.info("Object storage connected")
            # Set the bucket policy to public
            set_policy_bucket(client, bucket_name)

        result = client.fput_object(
            bucket_name,
            object_name,
            object_path,
            content_type="video/{}".format(type[1:]),
        )
        url_link = f"http://{hostname}/{bucket_name}/{object_name}"
        logger.info(f"Upload video success: {url_link}")
        return url_link
