from confluent_kafka.admin import AdminClient, NewTopic, ConfigResource
from time import sleep
from utils.logger import logger

_DEFAULT_TOPICS = [
    "docker-connect-configs",
    "docker-connect-offsets",
    "docker-connect-status",
    "default_ksql_processing_log",
]


class AdminKafka:
    def __init__(self, configs: dict):
        self.admin = AdminClient(configs)

    def create_topic(self, topic: str):
        fs = self.admin.create_topics(
            [
                NewTopic(
                    topic,
                    num_partitions=1,
                    replication_factor=1,
                    config={
                        "retention.bytes": "500000",
                        "retention.ms": "600000",
                        "cleanup.policy": "delete",
                    },
                )
            ]
        )
        for topic, f in fs.items():
            try:
                f.result()
                return True, None
            except Exception as e:
                return False, e

    def get_topics(self):
        return [
            i
            for i in self.admin.list_topics().topics
            if not i.startswith("_") and i not in _DEFAULT_TOPICS
        ]

    def alter_topic(self, topic: str):
        self.admin.alter_configs(
            [
                ConfigResource(
                    set_config={
                        "cleanup.policy": "delete",
                        "retention.ms": "600000",
                        "retention.bytes": "500000",
                    },
                    name=topic,
                    restype=ConfigResource.Type.TOPIC,
                )
            ]
        )

    def manage_topic(self, topic):
        if topic not in self.get_topics():
            self.create_topic(topic)
            logger.info(f"Topic '{topic}' created")
        else:
            self.alter_topic(topic)
            logger.info(f"Topic '{topic}' altered")
