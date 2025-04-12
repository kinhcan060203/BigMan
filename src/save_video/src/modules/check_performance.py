import psutil
import os
import time
from minio import Minio
from check_bucket import check_bucket
import subprocess

# remote_server = os.getenv("REMOTE_SERVER") or "192.168.101.15:9000"
# local_server = os.getenv("LOCAL_SERVER") or "localhost:9000"
remote_alias = os.getenv("REMOTE_ALIAS") or "minio2"
local_alias = os.getenv("LOCAL_ALIAS") or "minio1"
remote_bucket = os.getenv("REMOTE_BUCKET") or "test"
local_bucket = os.getenv("LOCAL_BUCKET") or "add"
time_interval = os.getenv("TIME_INTERVAL") or 5
access_key = os.getenv("ACCESS_KEY") or "meme"
secret_key = os.getenv("SECRET_KEY") or "meme@123"
local_addr = os.getenv("LOCAL_ADDR") or "localhost:9000"
remote_addr = os.getenv("REMOTE_ADDR") or "192.168.101.15:9000"

client = Minio(
    "192.168.101.26:9000",
    access_key="meme",
    secret_key="meme@123",
    secure=False,
)
guess = Minio(
    "192.168.101.15:9000",
    access_key="meme",
    secret_key="meme@123",
    secure=False,
)


def get_disk_usage(path="/"):
    usage = psutil.disk_usage(path)
    total_gb = round(usage.total / (1024**3), 2)
    used_gb = round(usage.used / (1024**3), 2)
    free_gb = round(usage.free / (1024**3), 2)
    percent_used = usage.percent

    cpu_usage = psutil.cpu_percent()  # Specify the interval in seconds
    ram = psutil.virtual_memory()

    print(f"RAM Usage Percentage: {ram.percent}%")
    print(f"CPU Usage: {cpu_usage}%")
    print(f"Percentage Used: {percent_used}%")
    print()
    return percent_used, cpu_usage, ram.percent


# Replace '/' with the path of the directory or drive you want to check
def handle_command():
    buckets = client.list_buckets()
    for bucket in buckets:
        print(bucket.name, bucket.creation_date)
        if check_bucket(guess, bucket.name) == True:
            print("Object storage connected")
            # Set the bucket policy to public
            os.system(
                "mc cp --recursive {}/{} {}/{}".format(
                    local_alias, bucket.name, remote_alias, bucket.name
                )
            )


def check_alias():
    # Run the command to list aliases and capture the output
    alias_list = subprocess.check_output(["mc", "alias", "list"]).decode("utf-8")
    # Check if the local alias exists in the output
    status = local_alias in alias_list and remote_alias in alias_list
    return status


def create_alias():
    os.system(
        "mc alias set {} http://{} {} {}".format(
            local_alias, local_addr, access_key, secret_key
        )
    )
    os.system(
        "mc alias set {} http://{} {} {}".format(
            remote_alias, remote_addr, access_key, secret_key
        )
    )


if __name__ == "__main__":
    start_time = time.time()
    if check_alias() == False:
        create_alias()
        status = True
    while True:
        if time.time() - start_time > time_interval:
            return_percent, return_cpu, return_ram = get_disk_usage("/")

            if return_percent >= 90 or return_cpu >= 90 or return_ram >= 90:
                handle_command()
            start_time = time.time()
