import requests
import queue


def check_minio_health(hostname):
    url = "http://{}/minio/health/live".format(hostname)
    response = requests.get(url)

    if response.status_code == 200:
        # print("MinIO server health check passed")
        return True
    else:
        print(
            f"MinIO server health check failed with status code: {response.status_code}"
        )
        return False
