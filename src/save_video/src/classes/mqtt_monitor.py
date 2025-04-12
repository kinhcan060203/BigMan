import paho.mqtt.client as mqtt
import json
import queue
import logging as logger
import uuid
from src.classes.mongo_monitor import MongoMonitor


class MQTTMonitor:
    def __init__(self, broker, port, username, password, topic_subcribe):
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        random = str(uuid.uuid1())
        self.client = mqtt.Client(random, clean_session=True)
        self.topic_subcribe = topic_subcribe
        topics, _ = MongoMonitor("metadata", "save_video").find_documents()
        self.trigger_queues = {topic: queue.Queue() for topic in topics}

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(self.topic_subcribe)
            logger.info(
                f"Connected to MQTT Broker with {self.broker}:{self.port}, topic: {self.topic_subcribe}, username {self.username}, password {self.password}"
            )
        else:
            logger.info("Connection failed with code", rc)

    def on_message(self, client, userdata, msg):
        data = msg.payload.decode()
        data = json.loads(data)
        topic = data["cam_id"]
        timestamp = data["timestamp"]
        event_type = data["event_type"]
        if event_type == "human_out" or event_type == "human_in":
            event_type = "human-count"
        if event_type == "human_falling":
            event_type = "human-falling"
        topic = event_type + "." + topic
        if topic in self.trigger_queues:
            self.trigger_queues[topic].put([topic, timestamp, True])
            logger.info(f"Trigger {topic} at {timestamp}")

    def connect(self):
        self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.broker, self.port)
        self.client.loop_forever()

    def start(self):
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
