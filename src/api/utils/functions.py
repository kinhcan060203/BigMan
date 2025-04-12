import msgpack

import pathlib

dir = pathlib.Path(__file__).parent.resolve()
from utils.logger import logger


def deserialize_data(packed_data):
    unpacked_data = msgpack.unpackb(packed_data, raw=False)
    frame_bytes = unpacked_data["frame"]
    metadata = unpacked_data["metadata"]

    return frame_bytes, metadata


