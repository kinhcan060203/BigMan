from fastapi import FastAPI, HTTPException, APIRouter
from pymongo import MongoClient
from bson.objectid import ObjectId
from utils.logger import logger
from config import MONGO_URI, KAFKA_SERVER
from modules.camera import HLSStreamManager
from utils.functions import deserialize_data
from confluent_kafka import Consumer, TopicPartition, OFFSET_END
from bson.json_util import dumps
import json



router = APIRouter()

client = MongoClient(MONGO_URI)
nano = client.get_database(name="nano")
Camera = nano.camera

@router.get("/{id}/latest.webp", tags=["camera"])
async def latest_frame(id):
    topic = "stream." + id
    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_SERVER,
            "group.id": "api",
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([topic])
    partition = TopicPartition(topic, 0, OFFSET_END)
    consumer.assign([partition])
    consumer.seek(partition)
    msg = consumer.poll(timeout=3.0)
    import base64
    if msg is None:
        raise HTTPException(status_code=404, detail="No frame available")
    try:
        image_bytes, _ = deserialize_data(msg.value())
        base64_string= base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        import rich
        rich.console.Console().print_exception()
        raise HTTPException(status_code=500, detail="Error decoding image")
    return base64_string

@router.get("/cameras", tags=["camera"])
async def get_cameras():
    try:
        cameras = Camera.find()
        return {"statusCode": 200, "data": json.loads(dumps(cameras))}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error {e}")


@router.get("/cameras/{id}", tags=["camera"])
async def get_camera(id: str):
    try:
        camera = Camera.find_one({"camera_id": id})
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        return {"statusCode": 200, "data": json.loads(dumps(camera))}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error {e}")
    
    

@router.put("/cameras/{camera_id}/resolution", tags=["camera"])
async def update_camera_resolution(camera_id: str, resolution: dict):
    try:
        camera = Camera.find_one({"camera_id": camera_id})
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")

        if not all(k in resolution for k in ("width", "height")):
            raise HTTPException(
                status_code=400, detail="Resolution must have width and height"
            )

        Camera.update_one(
            {"camera_id": camera_id},
            {"$set": {"resolution": resolution}},
        )

        updated_camera = Camera.find_one({"camera_id": camera_id})

        return {"statusCode": 200, "resolution": updated_camera.get("resolution")}

    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))

    
@router.put("/cameras/{id}", tags=["camera"])
async def update_camera(id: str, data: dict):
    try:
        camera = Camera.find_one({"camera_id": id})
        print("Before:", camera)
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")

        camera_name = data.get("camera_name", camera.get("camera_name"))
        if camera_name == "":
            raise HTTPException(status_code=400, detail="Name cannot be empty")
        
        old_url = camera.get("url")
        new_url = data.get("url", old_url)
        if new_url == "":
            raise HTTPException(status_code=400, detail="URL cannot be empty")

        camera["camera_name"] = camera_name.strip()
        camera["url"] = new_url.strip()

        new_area_id = data.get("area_id", camera.get("area_id"))
        new_area_name = data.get("area_name", camera.get("area_name"))
        status = data.get("status", camera.get("status"))
        if not isinstance(status, bool):
            raise HTTPException(status_code=400, detail="Invalid camera status")
        if new_area_id == "":
            raise HTTPException(status_code=400, detail="Area ID cannot be empty")
        if new_area_name == "":
            raise HTTPException(status_code=400, detail="Area name cannot be empty")
        
        camera["area_id"] = new_area_id
        camera["area_name"] = new_area_name
        camera["status"] = status
        
        Camera.update_one(
            {"camera_id": id}, {"$set": {"camera_name": camera_name.strip(), "url": new_url.strip(), "area_id": new_area_id, "area_name": new_area_name}}
        )

        # if old_url != new_url:
        #     hls_manager.update_hls_stream(camera)

        return {"statusCode": 200, "data": json.loads(dumps(camera))} 

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error {e}")




@router.post("/cameras", tags=["camera"])
async def add_camera(
    camera_id: str,
    camera_name: str,
    area_id: str,
    area_name: str,
    url: str,
    data: dict = {},
    status: bool = True,
):
    try:
        camera_id = camera_id.strip()
        camera_name = camera_name.strip()
        url = url.strip()

        if not camera_id or not camera_name:
            raise HTTPException(
                status_code=400, detail="Camera ID and camera_name must not be empty"
            )

        if not url:
            raise HTTPException(status_code=400, detail="URL must not be empty")

        existing_camera = Camera.find_one({"camera_id": camera_id})
        if existing_camera:
            raise HTTPException(status_code=400, detail=f"Camera with id {camera_id} already exists.")

        if not isinstance(status, bool):
            raise HTTPException(status_code=400, detail="Invalid camera status")

        services = data.pop("services", [])
        
        camera_data = {
            "camera_id": camera_id,
            "camera_name": camera_name,
            "area_id": area_id,
            "area_name": area_name,
            "url": url,
            "resolution": data.get("resolution", {"width": 1920, "height": 1080}),
            "data": {**data, "status": status},
            "services": services,
        }

        Camera.insert_one(camera_data)

        # hls_manager.create_hls_stream(camera_data)

        return {"statusCode": 200, "data": camera_data}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(str(e))
        Camera.delete_one({"camera_id": camera_id})
        raise HTTPException(status_code=400, detail=str(e))



@router.delete("/cameras/{id}", tags=["camera"])
async def delete_camera(id: str):
    try:
        id = id.strip()

        camera = Camera.find_one({"camera_id": id})
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")

        # hls_manager.delete_hls_stream(camera)

        # service_http_manager.delete_http_for_all_service(id)

        Camera.delete_one({"camera_id": id})

        logger.info(f"Camera {id} has been deleted.")
        return {"statusCode": 200, "message": "Camera deleted"}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error while deleting camera {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/cameras/{id}/status", tags=["camera"])
async def update_camera_status(id: str, status: bool):
    try:
        camera = Camera.find_one({"camera_id": id})

        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        Camera.update_one(
            {"camera_id": id}, 
            {"$set": {"status": status}}  
        )
        
        return {"statusCode": 200, "message": "Camera status updated successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")