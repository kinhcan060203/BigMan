import base64
import uuid
import io
from src.modules.check_bucket import check_bucket
from src.modules.check_con import check_minio_health
from src.modules.set_policy_bucket import set_policy_bucket
from config import MINIO_HOSTNAME


def upload_base64_image_to_minio(
    client, bucket_name, base64_image, event_type, cam_id, img_id
):
    img_name = f"{event_type}/{cam_id}/{img_id}.jpg"

    # Check the connection to the MinIO server
    check_status = check_minio_health(MINIO_HOSTNAME)
    if check_status == True:
        if check_bucket(client, bucket_name) == True:
            print("Object storage connected")
            # Set the bucket policy to public
            set_policy_bucket(client, bucket_name)

    # Convert base64 string to file-like object
    image_data = base64.b64decode(base64_image)
    image_file = io.BytesIO(image_data)

    if len(image_data) > 5 * 1024 * 1024:
        print("File size is too large", len(image_data))
        return False
    # Upload data
    result = client.put_object(
        bucket_name,
        img_name,
        image_file,
        len(image_data),
        content_type="image/jpg",
    )
    return result, img_name
