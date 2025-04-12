from minio import Minio
import os
from src.modules.check_con import check_minio_health
from src.modules.set_policy_bucket import set_policy_bucket
from src.modules.check_bucket import check_bucket
from src.modules.upload_folder import upload_directory_to_minio
from src.modules.upload_img import upload_base64_image_to_minio
from src.modules.upload_video import upload_video_to_minio
from src.modules.check_limitation import check_file_size_and_upload, check_file_type

# Set default values for environment variables
hostname = os.getenv("HOSTNAME") or "localhost"
access_key = os.getenv("MINIO_ACCESS_KEY") or "meme"
secret_key = os.getenv("MINIO_SECRET_KEY") or "meme@123"
bucket_name = os.getenv("MINIO_BUCKET_NAME") or "test"


def upload_object_to_minio(object_path, event_type, cam_id, bucket_name):
    # Initialize the MinIO client with the endpoint, access key, secret key and secure
    client = Minio(
        f"{hostname}",
        access_key=access_key,
        secret_key=secret_key,
        secure=False,
    )
    link = ""

    # Check the connection to the MinIO server
    check_status = check_minio_health(hostname)
    if check_status == True:
        if check_bucket(client, bucket_name) == True:
            print("Object storage connected")
            # Set the bucket policy to public
            set_policy_bucket(client, bucket_name)
        print(f"Uploading image to Minio {hostname}")

        object_dir = os.path.abspath(object_path)
        object_name = os.path.basename(object_dir)
        check_type, type = check_file_type(object_path)
        if check_type == "video":
            print("!!! Upload Video")
            if (
                check_file_size_and_upload(object_path, max_size=1 * 1024 * 1024 * 1024)
                == True
            ):
                result = upload_video_to_minio(
                    client, bucket_name, object_dir, object_name, type
                )
            else:
                return ""
        elif check_type == "directory":
            print("!!! Upload Directory")
            result = upload_directory_to_minio(
                client, bucket_name, object_dir, object_name
            )
        else:
            print("!!! Upload Image")
            result, object_name = upload_base64_image_to_minio(
                client, bucket_name, object_path, event_type, cam_id
            )
            if result == False:
                return ""
        if result:
            link = "http://{hostname}/{bucket_name}/{object_name}".format(
                hostname=hostname, bucket_name=bucket_name, object_name=object_name
            )
            print(
                f"Upload success at this link http://{hostname}/{bucket_name}/{object_name}"
            )
    else:
        print("Connection to MinIO server failed")
        link = ""
    return link


if __name__ == "__main__":

    base64_image = ""
    event_type = "human-falling"
    cam_id = "CAM6"

    object_path = "./"
    # import base64
    # with open(object_path, 'rb') as image_file:
    #     object_path = base64.b64encode(image_file.read()).decode('utf-8')

    try:
        link = upload_object_to_minio(object_path, event_type, cam_id, bucket_name)
    except KeyboardInterrupt:
        print("Exiting...")
        exit()
