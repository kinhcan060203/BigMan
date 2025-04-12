from pymongo import MongoClient


class MongoMonitor:
    def __init__(self, host, port, database, collection):
        self.database = database
        self.collection = collection
        self.client = MongoClient(f"mongodb://{host}:{port}:27017")
        self.db = self.client[self.database]
        self.col = self.db[self.collection]

    def find_documents(self):
        list_attr_camera = []
        for camera_topic in self.col.find():
            list_attr_camera = camera_topic["streams"]

        topics = [stream["source"]["topic"] for stream in list_attr_camera]
        list_fps = [stream["source"]["fps"] for stream in list_attr_camera]
        return topics, list_fps
