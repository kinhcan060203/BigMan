import json
import time
import logging as logger
import threading
import queue
import multiprocessing as mp
from confluent_kafka import Consumer, KafkaError, OFFSET_END, TopicPartition
from multiprocessing.synchronize import Event as MpEvent
from config import (
    KAFKA_HOSTNAME,
    LENGTH_VIDEO,
    REDIS_HOST,
    REDIS_PORT,
)
from src.classes.redis_monitor import RedisMonitor
from src.classes.kafka_monitor import KafkaMonitor
from src.modules.models import Camera, CameraService, Service, Event
from src.db.database import db

logger.basicConfig(
    level=logger.INFO, format="%(asctime)s - [%(levelname)s]: %(message)s"
)

# Get the logger for 'kafka' (used by the Kafka client)
kafka_logger = logger.getLogger("kafka")

# Set the log level to WARNING to ignore INFO and DEBUG messages
kafka_logger.setLevel(logger.WARNING)


class VideoDecoder:
    def __init__(self) -> None:
        self.db = db

        self.redis_monitor = RedisMonitor(REDIS_HOST, REDIS_PORT)
        self.kafka_hostname = KAFKA_HOSTNAME
        self.event_topic = "event"
        self.camera_topics = None
        self.camera_fps = None
        self.event_queue = []
        self.stop_events = {str: threading.Event()}
        self.trigger = {str: False}
        self.processes = [threading.Thread()]

    def consume_multi_topic(self, camera_topic, fps):
        # Create a new KafkaMonitor instance for each process
        kafka_monitor = KafkaMonitor(KAFKA_HOSTNAME, self.redis_monitor.redis_client)
        kafka_monitor.consumer.subscribe([camera_topic])
        partition = TopicPartition(camera_topic, 0, OFFSET_END)
        kafka_monitor.consumer.assign([partition])
        kafka_monitor.consumer.seek(partition)
        self.redis_monitor.redis_client.delete(camera_topic)
        logger.info("#########################")
        logger.info(
            f"Delete message in redis and starting new process for added topic: {camera_topic}"
        )
        try:
            while not self.stop_events[camera_topic].is_set():
                frame = kafka_monitor.consumer_message(camera_topic)
                if frame is not None:
                    # logger.info(f"Consume message from topic: {camera_topic}")
                    timestamp = time.time()
                    resized_frame_base64, height, width = kafka_monitor.process_message(
                        frame
                    )
                    data = {
                        "timestamp": timestamp,
                        "frame": resized_frame_base64,
                    }
                    self.redis_monitor.redis_client.rpush(
                        camera_topic, json.dumps(data)
                    )
                    if (
                        self.redis_monitor.redis_client.llen(camera_topic)
                        == (int(fps) * int(LENGTH_VIDEO)) / 2 + 1
                    ):
                        popped_data = self.redis_monitor.redis_client.lpop(camera_topic)
                        if popped_data is not None:
                            popped_data = json.loads(popped_data)

                    if not self.event_queue[camera_topic].empty():
                        logger.info(f"{camera_topic} has event")
                        event_message = self.event_queue[camera_topic].get()
                        self.trigger[camera_topic] = True
                    if camera_topic not in self.trigger:
                        self.trigger[camera_topic] = False
                    if self.trigger[camera_topic]:
                        self.trigger[camera_topic] = False
                        logger.info(f"Start collecting frames for {camera_topic}")
                        list_params = [fps, height, width]
                        old_frames = self.redis_monitor.redis_client.lrange(
                            camera_topic, 0, -1
                        )
                        threading.Thread(
                            target=kafka_monitor.collect_frames,
                            args=(
                                old_frames,
                                camera_topic,
                                list_params,
                                event_message,
                            ),
                            # daemon=True,
                        ).start()
        except KeyboardInterrupt:
            kafka_monitor.consumer.close()

    def recv_event(self):
        kafka_monitor = KafkaMonitor(KAFKA_HOSTNAME, None)
        kafka_monitor.consumer.subscribe([self.event_topic])
        while True:
            event = kafka_monitor.consumer_message(self.event_topic)
            if event is not None:
                logger.info("#########################")
                logger.info(
                    f"Received event from topic {self.event_topic} with values: {event}"
                )

                message = json.loads(event)
                self.event_queue[message["event_type"] + "." + message["camera"]].put(
                    message
                )
                logger.info("Topic: " + message["event_type"] + "." + message["camera"])

    def get_config(self):
        # Fetch the camera topics and FPS from the database
        camera_services = (
            CameraService.select(Camera.camera_id, Service.name)
            .join(Camera, on=(CameraService.camera_id == Camera.id))
            .join(Service, on=(CameraService.service_id == Service.id))
        )
        camera_topics = [f"{srv}.{cam}" for cam, srv in camera_services.tuples()]

        camera_data = CameraService.select(
            CameraService.camera_id, Camera.data["fps"].alias("fps")
        ).join(Camera, on=(CameraService.camera_id == Camera.id))
        camera_fps = [camera.fps for camera in camera_data]
        return camera_topics, camera_fps

    def stop_thread(self, camera_topic):
        """Stop a specific thread by setting its stop event and waiting for the thread to terminate."""
        stop_event = self.stop_events.get(camera_topic)
        if stop_event:
            logger.info("############################################")
            logger.info(f"Stopping thread for camera topic: {camera_topic}")
            stop_event.set()  # Signal the thread to stop
            thread = next(
                (t for t in threading.enumerate() if t.name == camera_topic), None
            )
            if thread:
                thread.join()  # Wait for the thread to finish
                logger.info(f"Thread for {camera_topic} has been stopped.")
                logger.info("############################################")
                self.processes.remove(thread)
                self.stop_events.pop(camera_topic)
                self.event_queue.pop(camera_topic)

    def update_config(self):
        """Update camera configurations by stopping and starting threads based on database config."""
        new_camera_topics, new_camera_fps = self.get_config()
        # Stop threads for removed topics
        for camera_topic in set(self.camera_topics) - set(new_camera_topics):
            self.stop_thread(camera_topic)

        # Start new threads for added topics
        for camera_topic, fps in zip(new_camera_topics, new_camera_fps):
            if camera_topic not in self.camera_topics:
                self.event_queue[camera_topic] = queue.Queue()
                stop_event = threading.Event()
                self.stop_events[camera_topic] = stop_event
                self.stop_events[camera_topic].clear()
                new_thr = threading.Thread(
                    target=self.consume_multi_topic,
                    args=(camera_topic, fps),
                    name=camera_topic,
                )
                new_thr.start()
                self.processes.append(new_thr)

        self.camera_topics = new_camera_topics
        self.camera_fps = new_camera_fps

    def start(self):
        self.camera_topics, self.camera_fps = self.get_config()
        logger.info(f"Camera topics: {self.camera_topics} and FPS: {self.camera_fps}")

        # Create a queue for each camera topic to update config from db
        self.event_queue = {
            camera_topic: queue.Queue() for camera_topic in self.camera_topics
        }

        # check length of camera and fps if error then exit
        if len(self.camera_topics) == 0 and len(self.camera_fps) == 0:
            logger.error("No camera topics found in the database")

        logger.info("Length video: " + LENGTH_VIDEO)
        # Start a process to receive events from Kafka
        rev_event_mp = threading.Thread(target=self.recv_event, name="rev_event")
        rev_event_mp.start()

        for camera_topic, fps in zip(self.camera_topics, self.camera_fps):
            stop_event = threading.Event()
            self.trigger[camera_topic] = False
            self.stop_events[camera_topic] = stop_event
            consume_mp = threading.Thread(
                target=self.consume_multi_topic,
                args=(camera_topic, fps),
                name=camera_topic,
            )
            consume_mp.start()
            self.processes.append(consume_mp)

        try:
            while True:
                self.update_config()
                time.sleep(1)
        except KeyboardInterrupt:
            for process in self.processes:
                process.join()
            self.db.close()
            self.stop()

    def stop(self):
        self.redis_monitor.redis_client.close()
        exit()
