from fastapi import FastAPI, HTTPException, APIRouter
from pymongo import MongoClient
from datetime import datetime
from collections import defaultdict
from bson import ObjectId
from config import MONGO_URI
import logging

router = APIRouter()
client = MongoClient(MONGO_URI)
nano = client.get_database(name="nano")

Camera = nano.camera
Event = nano.event 

logger = logging.getLogger(__name__)

from fastapi import Query
from collections import defaultdict

@router.get("/counting/total_in_out", tags=["counting"])
async def get_in_out_counts(
    camera_id: str ,
    start_time: float = 0,
    end_time: float = None,
    interval: int = 60,  
):
    if end_time is None:
        end_time = datetime.now().timestamp()

    try:
        end_time_dt = datetime.fromtimestamp(end_time)
        start_time_dt = datetime.fromtimestamp(start_time)
    except (OSError, OverflowError, ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid timestamp.")

    match_conditions = {
        "event_type": "vehicle_counting",
        "start_time": {"$gte": start_time_dt},
        "end_time": {"$lte": end_time_dt}
    }

    if camera_id != "all":
        match_conditions["camera_id"] = camera_id

    pipeline = [
        {"$match": match_conditions},
        {"$group": {
            "_id": None if camera_id == "all" else "$camera_id",
            "total_in": {"$sum": {"$ifNull": ["$data.counted_in", 0]}},
            "total_out": {"$sum": {"$ifNull": ["$data.counted_out", 0]}},
            "metadata": {"$push": "$data.metadata"}
        }},
    ]

    result = list(Event.aggregate(pipeline))
    
    if not result:
        raise HTTPException(status_code=404, detail="No events found for this camera")

    result = result[0]  
    total_in = result["total_in"]
    total_out = result["total_out"]
    metadata_list = result["metadata"]

    def summarize_metadata(metadata_list):
        summary = []

        for metadata in metadata_list:
            summary.extend({**item, "action": "in"} for item in metadata.get("_in", []))
            summary.extend({**item, "action": "out"} for item in metadata.get("_out", []))

        summary.sort(key=lambda x: x["timestamp"])

        if not summary:
            return {}

        start_time = summary[-1]["timestamp"]
        pages = defaultdict(list)
        page_names = {}

        for item in summary:
            page_index = int((item["timestamp"] - start_time) // interval)
            pages[page_index].append(item)

            if page_index not in page_names:
                page_start_time = datetime.fromtimestamp(item["timestamp"])
                page_names[page_index] = page_start_time.strftime("%d-%m-%Y %H:%M:%S")

        return {page_names[idx]: pages[idx] for idx in sorted(pages.keys())}

    summary = summarize_metadata(metadata_list)

    return {
        "camera_id": camera_id,
        "total_in": total_in,
        "total_out": total_out,
        "summary": summary
    }
