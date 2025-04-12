"""events apis."""

from fastapi import (
    APIRouter,
    Request,
    Query,
    HTTPException,
    Body,
    WebSocket,
    WebSocketException,
)
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING
from config import MONGO_URI
from bson.son import SON
from functools import reduce
import uuid
from modules.websocket_manager import WebsocketManager
from rich import inspect, print
from rich.console import Console
from utils.logger import logger
from bson.json_util import dumps
import json
from datetime import datetime, timezone


console = Console()

days = 1
router = APIRouter()
manager = WebsocketManager()

EVENTS_TYPE = [
    "crowd_detection",
    "vehicle_counting",
    "license_plate",
    "reidentify",
    "speed_estimate",
]

router = APIRouter()
client = MongoClient(MONGO_URI)
nano = client.get_database(name="nano")

Event = nano.event
Watchlist = nano.watchlist_license_plate 


@router.get("/events/summary", tags=["events"])
async def get_summary(
    cameras: str = Query(None, description="Comma separated list of camera ids"),
    before: float = Query(None, description="End time in unix timestamp"),
    after: float = Query(None, description="Start time in unix timestamp"),
):
    try:
        if before is None:
            before = datetime.now().timestamp() 

        if after is None:
            after = 0

        before_dt = datetime.fromtimestamp(before)
        after_dt = datetime.fromtimestamp(after)
    except (OSError, OverflowError, ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Time must be a valid timestamp.")

    match_conditions = {
        "end_time": {"$lte": before_dt},
        "start_time": {"$gte": after_dt}
    }
    if cameras:
        camera_list = cameras.split(",")
        match_conditions["camera_id"] = {"$in": camera_list}
        
    print(match_conditions)
    pipeline = [
        {"$match": match_conditions},
        {"$group": {
            "_id": None,
            **{
                f"total_{etype}": {
                    "$sum": {
                        "$cond": [{"$eq": ["$event_type", etype]}, 1, 0]
                    }
                } for etype in EVENTS_TYPE
            },
            **{
                f"reviewed_{etype}": {
                    "$sum": {
                        "$cond": [
                            {
                                "$and": [
                                    {"$eq": ["$event_type", etype]},
                                    {"$eq": ["$is_reviewed", True]},
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                } for etype in EVENTS_TYPE
            },
        }},
        {"$project": {"_id": 0}}
    ]

    agg_result = list(Event.aggregate(pipeline))
    data = agg_result[0] if agg_result else {
        **{f"total_{etype}": 0 for etype in EVENTS_TYPE},
        **{f"reviewed_{etype}": 0 for etype in EVENTS_TYPE}
    }

    return {
        "data": data,
        "start_time": datetime.fromtimestamp(after).isoformat(),
        "end_time": datetime.fromtimestamp(before).isoformat()
    }

@router.post("/events/overview", tags=["events"])
async def get_events_overview(
    event_type: str = Query(None, description="Event type"),
    start_time: float = Query(None, description="Start time in unix timestamp"),
    end_time: float = Query(None, description="End time in unix timestamp"),
    filter_data: dict = Body(None, description="Filter data"),
):
    try:
        if end_time is None:
            end_time = datetime.now().timestamp()
        if start_time is None:
            start_time = 0

        start_time_dt = datetime.fromtimestamp(start_time)
        end_time_dt = datetime.fromtimestamp(end_time)

    except (OSError, OverflowError, ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid timestamp format.")

    try:
        query = {
            "event_type": event_type,
   
        }
        events_cursor = Event.find(query).sort("start_time", DESCENDING).limit(100)
        items = list(events_cursor)

        isWatchlist = filter_data.get("isWatchlist") if filter_data else None
        watchlist_dict = {}

        if event_type == "license_plate" and isWatchlist is not None:
            plates_cursor = Watchlist.find()
            for plate in plates_cursor:
                plate_number = plate.get("license_plate")
                plate_data = plate.get("data", {})
                plate_id = plate.get("_id")
                watchlist_dict[plate_number] = {**plate_data, "id": str(plate_id)}
        return {
            "totalCount": len(items),
            "items":json.loads(dumps(items)), 
            "watchlist": watchlist_dict if watchlist_dict else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")




@router.post("/events/viewed", tags=["events"])
async def mark_events_viewed(ids_event: str = Query(...)):
    try:
        ids = ids_event.split(",")
        result = Event.update_many(
            {"event_id": {"$in": ids}},
            {"$set": {"is_reviewed": True}}
        )

        return {
            "success": True,
            "message": f"Review update ok. Matched {result.matched_count} events."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.delete("/events/{event_id}", tags=["events"])
async def delete_event(event_id: str):
    try:
        uuid.UUID(event_id) 
        result = Event.delete_one({"event_id": event_id})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

        return {"success": True, "message": f"Event {event_id} deleted"}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
    
@router.websocket("/events")
async def websocket_endpoint(websocket: WebSocket):
    # await websocket.accept()
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(data)
    except Exception as e:
        logger.error(e)
    finally:
        manager.disconnect(websocket)
