from fastapi import (
    File,
    HTTPException,
    UploadFile,
    APIRouter,
)
import base64
import requests
from datetime import datetime
import logging as logger
from pymongo import MongoClient
from config import (
    REID_HOST,
    REID_PORT,
    LPR_HOST,
    LPR_PORT,
    MONGO_URI,  
)
router = APIRouter()
client = MongoClient(MONGO_URI)
nano = client.get_database(name="nano")


@router.post(
    "/reid_analysis/lpr",
    tags=["reid_analysis"],
)
async def lpr(
    file: UploadFile = File(...),
):
    try:
        img_base64 = base64.b64encode(await file.read()).decode("utf-8")
        url = f"http://{LPR_HOST}:{LPR_PORT}/predict/base64/"

        response = requests.post(
            url, json={"image": img_base64, "type": "car"}, timeout=10
        )

        if response.status_code == 200:
            rsp = response.json()
            license_number = rsp.get("license_number")
            plate_img = rsp.get("plate")
            color = rsp.get("color")

            return {
                "license_number": license_number,
                "plate_img": plate_img,
                "color": color,
            }

        return {}

    except requests.RequestException as e:
        logger.error(f"Error finding license plate: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to LPR service")


@router.post(
    "/reid_analysis/search_vehicle",
    tags=["reid_analysis"],
)
async def reid_analysis(
    file: UploadFile = File(...),
    confidence: float = 0.3,
):
    try:
        url = f'http://{REID_HOST}:{REID_PORT}/api/vehicle/search'
        img_base64 = base64.b64encode(await file.read()).decode("utf-8")

        response = requests.get(
            url,
            json={"top_k": 20, "image_base64": img_base64},
            timeout=20
        )

        result = response.json()

        return result

    except requests.RequestException as e:
        logger.error(f"Error connecting to ReID service: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to ReID service")

    except Exception as e:
        logger.error(e)
        from rich.console import Console
        Console().print_exception()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
