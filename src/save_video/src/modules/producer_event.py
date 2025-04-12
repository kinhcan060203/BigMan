from confluent_kafka import Producer
import uuid

import psycopg2
import logging as logger


class Pg_Monitor:
    def __init__(self, host, port, username, password, database):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.connection = None

    def connect(self):
        # Add code to establish a connection to the PostgreSQL database
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                database=self.database,
            )
            logger.info("Connection to PostgreSQL DB successful")
            return self.connection
        except Exception as e:
            logger.error(f"Connection to PostgreSQL DB failed: {e}")
            exit

    def disconnect(self):
        # Add code to disconnect from the PostgreSQL database

        pass

    def execute_query(self, query):
        # Add code to execute a query on the PostgreSQL database
        pass

    def fetch_data(self, query):
        if self.connection is None:
            logger.error("Database connection is not established")
            return []

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            return []

    def insert_data(self, table: str, data: dict):
        # Add code to insert data into a table in the PostgreSQL database
        try:
            with self.connection.cursor() as cursor:
                columns = ", ".join(data.keys())
                placeholders = ", ".join(["%s"] * len(data))
                query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                cursor.execute(query, list(data.values()))
                self.connection.commit()
                logger.info("Data inserted successfully")
        except Exception as e:
            logger.error(f"Failed to insert data: {e}")
            return False

    def update_data(self, table, data, condition):
        # Add code to update data in a table in the PostgreSQL database
        pass

    def delete_data(self, table, condition):
        # Add code to delete data from a table in the PostgreSQL database
        pass


# Define the Kafka configuration
conf = {
    "bootstrap.servers": "192.168.103.219:9092"  # Change this to your Kafka broker address
}

# Create a Kafka Producer instance
producer = Producer(conf)


# Callback function to handle delivery reports
def delivery_report(err, msg):
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")


# Produce a message to the Kafka topic
def produce_message(topic, message):
    producer.produce(topic, message, callback=delivery_report)
    producer.flush()


import random
import string


def generate_random_id(length=8):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


import datetime

# Example usage
if __name__ == "__main__":
    pg_monitor = Pg_Monitor("localhost", 5432, "root", "secret", "nano")
    topic = "event"
    id = generate_random_id()
    print(id)
    start_time = datetime.datetime.now()
    pg_monitor.connect()
    messages = {
        "id": id,
        "event_type": "crowd_detection",
        "camera": "5F_LOBBY_P8-P9_CAM_08",
        "start_time": start_time.isoformat(),
        "end_time": (start_time + datetime.timedelta(seconds=10)).isoformat(),
        "thumb_path": f"http://localhost:9000/nano/thumb_nail/crowd_detection/5F_LOBBY_P8-P9_CAM_08/{id}.jpg",
        "data": "data",
    }

    import json

    messages = json.dumps(messages)
    # for msg in messages:
    input("Press Enter to send message")
    produce_message(topic, messages)
    pg_monitor.insert_data(
        "event",
        {
            "id": id,
            "event_type": "crowd_detection",
            "camera": "5F_LOBBY_P8-P9_CAM_08",
            "start_time": start_time,
            "end_time": start_time + datetime.timedelta(seconds=10),
            "thumb_path": f"http://localhost:9000/nano/thumb_nail/crowd_detection/5F_LOBBY_P8-P9_CAM_08/{id}.jpg",
            "data": json.dumps("data"),
        },
    )
