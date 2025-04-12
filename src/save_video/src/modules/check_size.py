from minio import Minio


def check_vd_size(video_path):
    # Check the size of the video on minio
    bucket_name = video_path.split("/")[3]
    object_name = video_path.split("/")[-1]
    print("Bucket name: ", bucket_name)
    return client.stat_object(bucket_name, object_name).size
