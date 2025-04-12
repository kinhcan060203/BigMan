import requests
from rich import print, console

con = console.Console()


class HLSStreamManager:
    def __init__(self, server):
        self.server = server

    def create_hls_stream(self, camera):
        package = {
            "name": camera.camera_name,
            "channels": {"0": {"name": "0", "url": camera.url, "on_demand": False}},
        }
        response = requests.post(
            f"{self.server}/stream/{camera.camera_id}/add", json=package
        )
        return response.status_code

    def delete_hls_stream(self, camera):
        response = requests.get(f"{self.server}/stream/{camera.camera_id}/delete")
        return response.status_code

    def update_hls_stream(self, camera):
        self.delete_hls_stream(camera)
        package = {
            "name": camera.camera_name,
            "channels": {"0": {"name": "0", "url": camera.url, "on_demand": False}},
        }
        response = requests.post(
            f"{self.server}/stream/{camera.camera_id}/add", json=package
        )
        return response.status_code


class HTTPStreamManager:
    def __init__(self, server):
        self.server = server

    def get_streams(self):
        response = requests.get(f"{self.server}/stream/all")
        if response.status_code == 200:
            return response.json()
        return None

    def create_collection(self, new_collection_name):
        form_data = {"new_collection_name": new_collection_name, "action": "create"}
        files = {"json_file": ("", b"", "application/octet-stream")}
        response = requests.post(f"{self.server}/", data=form_data, files=files)
        return response.status_code

    def delete_collection(self, collection_name):
        request_url = f"{self.server}/delete/{collection_name}"
        response = requests.get(request_url)
        return response.status_code

    def create_stream(
        self,
        collection_name,
        stream_name,
        kafka_server,
        kafka_topic,
        fps,
        sublink,
        http_enabled="on",
        rtsp_enabled="off",
    ):
        form_data = {
            "stream_name": stream_name,
            "kafka_server": kafka_server,
            "kafka_topic": kafka_topic,
            "fps": fps,
            "sublink": sublink,
            "http_enabled": http_enabled,
            "rtsp_enabled": rtsp_enabled,
        }
        request_url = f"{self.server}/collection/{collection_name}"
        response = requests.post(request_url, data=form_data)
        return response.status_code

    def update_stream(
        self,
        collection_name,
        stream_name,
        kafka_server,
        kafka_topic,
        fps,
        sublink,
        http_enabled="on",
        rtsp_enabled="off",
    ):
        form_data = {
            "stream_name": stream_name,
            "kafka_server": kafka_server,
            "kafka_topic": kafka_topic,
            "fps": fps,
            "sublink": sublink,
            "http_enabled": http_enabled,
            "rtsp_enabled": rtsp_enabled,
        }

        stream_id = self.map_stream_name_to_id(collection_name, stream_name)
        if stream_id is None:
            return 404
        request_url = f"{self.server}/update/{collection_name}/{stream_id}"

        response = requests.post(request_url, data=form_data)
        return response.status_code

    def delete_stream(self, collection_name, stream_name):
        stream_id = self.map_stream_name_to_id(collection_name, stream_name)
        if stream_id is None:
            return 404
        request_url = f"{self.server}/remove/{collection_name}/{stream_id}"
        response = requests.get(request_url)
        return response.status_code

    def map_stream_name_to_id(self, collection_name, stream_name):
        streams = self.get_streams()
        if streams is None:
            return None
        for collection in streams["collection"]:
            if list(collection.keys())[0] == collection_name:
                for stream in collection[collection_name]:
                    if stream["name"] == stream_name:
                        return stream["id"]
        return None


class ServiceHTTPManager:
    def __init__(self, manager: HTTPStreamManager):
        self.manager = manager

    def create_http_for_all_service(self, service_list, camera_id, kafka_server):
        for service in service_list:
            service_name = service["service_name"]
            try:
                self.manager.create_collection(service_name)
            except:
                con.print_exception()
                pass

            try:
                self.manager.create_stream(
                    collection_name=service_name,
                    stream_name=service_name + "_" + camera_id,
                    kafka_server=kafka_server,
                    kafka_topic=service_name + "." + camera_id,
                    fps="25",
                    sublink=camera_id + "/" + service_name,
                )
            except:
                con.print_exception()
                pass

    def delete_http_for_all_service(self, camera_id):
        # Get all http services
        services = self.manager.get_streams()
        if services is None:
            return 404

        # Delete all http services
        for collection in services["collection"]:
            collection_name = list(collection.keys())[0]
            for stream in collection[collection_name]:
                stream_name = stream["name"]
                if stream_name.endswith("_" + camera_id):
                    self.manager.delete_stream(collection_name, stream_name)
        return 200


# Example usage:
# hls_manager = HLSStreamManager(HLS_SERVER)
# status_code = hls_manager.create_hls_stream(camera)
if __name__ == "__main__":
    maneger = HTTPStreamManager("http://180.148.0.215:8081")

    # res = maneger.get_streams()
    # res = maneger.create_collection("test")
    # res = maneger.delete_collection("test")
    # res = maneger.map_stream_name_to_id("test", "test")
    # res = maneger.create_stream(
    #     collection_name="test",
    #     stream_name="alo",
    #     kafka_server="180.148.0.215:9092",
    #     kafka_topic="alo",
    #     fps="30",
    #     sublink="alo",
    #     http_enabled="on",
    #     rtsp_enabled="off",
    # )
    # res = maneger.update_stream(
    #     collection_name="test",
    #     stream_name="aa",
    #     kafka_server="180.148.0.215:9092",
    #     kafka_topic="alo",
    #     fps="30",
    #     sublink="alo",
    #     http_enabled="on",
    #     rtsp_enabled="off",
    # )
    # res = maneger.delete_stream("test", "alo")

    full_maneger = ServiceHTTPManager(maneger)
    # res = full_maneger.create_http_for_all_service(
    #     [
    #         {"name": "test"},
    #         {"name": "test2"},
    #     ],
    #     "test",
    #     "180.148.0.215:9092",
    # )
    res = full_maneger.delete_http_for_all_service("test")
    print(res)
