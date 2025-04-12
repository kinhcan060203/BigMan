import subprocess
import os


def get_quota_info():
    command = "mc quota info minio2/test3 | awk '/hard quota of/ {print $7 $8}'"
    quota_info = subprocess.check_output(command, shell=True).decode("utf-8").strip()
    print(quota_info[:3], quota_info[3:])
    if quota_info[3:] == "MiB":
        quota_info = float(quota_info[:3]) * 1024
    elif quota_info[3:] == "GiB":
        quota_info = float(quota_info[:3]) * 1024 * 1024
    elif quota_info[3:] == "TiB":
        quota_info = float(quota_info[:3]) * 1024 * 1024 * 1024
    elif quota_info[3:] == "PiB":
        quota_info = float(quota_info[:3]) * 1024 * 1024 * 1024 * 1024
    elif quota_info[3:] == "EiB":
        quota_info = float(quota_info[:3]) * 1024 * 1024 * 1024 * 1024 * 1024
    return quota_info


def check_file_type(file_path):
    """Check the file type: image, video, folder or unknown"""
    if os.path.isdir(file_path):
        return "directory", None
    # Get the file extension
    file_extension = os.path.splitext(file_path)[1].lower()

    # Check if the file extension corresponds to an image or video format
    if file_extension in [".jpg", ".jpeg", ".png", ".gif"]:
        return "image", file_extension
    elif file_extension in [".mp4", ".avi", ".mov"]:
        return "video", file_extension
    else:
        return "unknown", None


def check_file_size_and_upload(file_path, max_size):
    file_size = os.path.getsize(file_path)
    if file_size > max_size:
        print("File size is too large", file_size)
        return False
    return True


def get_directory_size(directory):
    total = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total += os.path.getsize(fp)

    return total
