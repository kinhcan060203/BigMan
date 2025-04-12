import glob
import os


def upload_directory_to_minio(client, bucket_name, local_path, minio_path):
    """Upload a whole local directory tree to MinIO recursively."""
    # assert os.path.isdir(local_path)
    for local_file in glob.glob(local_path + "/**"):
        local_file = local_file.replace(os.sep, "/")  # Replace \ with / on Windows
        if not os.path.isfile(local_file):
            upload_directory_to_minio(
                client,
                local_file,
                bucket_name,
                minio_path + "/" + os.path.basename(local_file),
            )
        else:
            remote_path = os.path.join(minio_path, local_file[1 + len(local_path) :])
            remote_path = remote_path.replace(
                os.sep, "/"
            )  # Replace \ with / on Windows
            client.fput_object(bucket_name, remote_path, local_file)
    return True
