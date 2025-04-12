import logging as logger


# bucket_name = os.getenv("MINIO_BUCKET") or "test1"
def check_bucket(client, bucket_name):
    """Check bucket exists or not"""
    if client.bucket_exists(bucket_name):
        logger.info("Sending data to MINIO server")
    else:
        logger.info("{} does not exist".format(bucket_name))
        # Create bucket.
        client.make_bucket(bucket_name)
        logger.info("Have created {}".format(bucket_name))
    return True
