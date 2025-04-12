import threading
from confluent_kafka import Consumer, KafkaError, TopicPartition
import msgpack

consumer_config = {
    "bootstrap.servers": "192.168.101.4:9089",
    "group.id": "frame_rate_monitor_group7",
    "auto.offset.reset": "latest",
    "fetch.max.bytes": 10485760,
    "max.partition.fetch.bytes": 10485760,
}
def deserialize_data(packed_data):
    unpacked_data = msgpack.unpackb(packed_data, raw=False)
    frame_bytes = unpacked_data["frame"]
    metadata = unpacked_data["metadata"]
    return frame_bytes, metadata

topic = ["stream.LH-HV-LL_CAM-04"]
consumer = Consumer(
  consumer_config
)
consumer.subscribe(topic)

while True:
    try:
        msg = consumer.poll(timeout=1.0)

        if msg is None:
            print("Die")
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                print(msg.error())
                break


        import time
        print(time.time())
    except KeyboardInterrupt:
        print("Consumer interrupted by user")
        break
    except Exception as e:
        print(f"Error: {e}")
consumer.close()
print("Consumer closed")
        
