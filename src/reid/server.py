from fastapi import FastAPI, File, HTTPException, Query, UploadFile
import os
import uvicorn
import pathlib
import cv2
import numpy as np
import uuid
import time
import argparse
import sys
import torch.nn.functional as F
import cv2
import numpy as np
import tqdm
from torch.backends import cudnn
sys.path.append('./')
from fastreid.config import get_cfg
from fastreid.utils.logger import setup_logger
import logging
from fastreid.utils.file_io import PathManager
from predictor import FeatureExtractionDemo
from pymilvus import MilvusClient

import supervision as sv
import peewee

from starlette.responses import RedirectResponse
from fastapi import Body
from fastapi.middleware.cors import CORSMiddleware
import base64



def get_parser():
    parser = argparse.ArgumentParser(description="Feature extraction with reid models")
    parser.add_argument(
        "--config-file",
        metavar="FILE",
        default='src/reid/reid_configs/VehicleID/bagtricks_R50-ibn.yml',
        help="path to config file",
    )
    parser.add_argument(
        "--parallel",
        action='store_true',
        help='If use multiprocess for feature extraction.'
    )
    parser.add_argument(
        "--input",
        nargs="+",
        help="A list of space separated input images; "
             "or a single glob pattern such as 'directory/*.jpg'",
    )
    parser.add_argument(
        "--output",
        default='demo_output',
        help='path to save features'
    )
    parser.add_argument(
        "--opts",
        help="Modify config options using the command-line 'KEY VALUE' pairs",
        default=[],
        nargs=argparse.REMAINDER,
    )
    return parser

def setup_cfg(args):
    cfg = get_cfg()
    # add_partialreid_config(cfg)
    cfg.merge_from_file(args.config_file)
    cfg.merge_from_list(args.opts)
    cfg.freeze()
    return cfg

cudnn.benchmark = True
setup_logger(name="reid")
logger = logging.getLogger("reid")


args = get_parser().parse_args()
cfg = setup_cfg(args)
PathManager.mkdirs(args.output)
reid_model = FeatureExtractionDemo(cfg, parallel=args.parallel)
milvus_cache = MilvusClient(uri="http://localhost:19532", token="root:anh123", db_name="reid")
app = FastAPI(
    title="nano",
    version="1.0.0",
    openapi_prefix="/api",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
async def index():
    """
    This endpoint redirects the root URL to the API documentation page.

    Returns:
        RedirectResponse: A redirection to the API documentation page.
    """
    return RedirectResponse(url="/docs")
@app.get(
    "/vehicle/search",
    tags=["reid"],
 
)
async def get_embedding(image_base64: str = Body(..., embed=True), top_k = 10):
    def postprocess(features):
        features = F.normalize(features)
        features = features.cpu().data.numpy()
        return features

    
    image_data = base64.b64decode(image_base64)
    np_arr = np.frombuffer(image_data, np.uint8)
    vehicle_box_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    feat = reid_model.run_on_image(vehicle_box_img)
    feat = postprocess(feat)[0]
    search_results = milvus_cache.search(
        collection_name='main_vehicle',
        anns_field="embedding",
        data=[feat],
        limit=top_k,
        search_params={"metric_type": "COSINE"},
        output_fields=["identity", "timestamp", "camera_name", "vehicle_path"],
    )
    formatted_results = []
    for result in search_results:
        for match in result:

            formatted_results.append({
                "identity": match["entity"].get("identity"),
                "timestamp": match["entity"].get("timestamp"),
                "camera_name": match["entity"].get("camera_name"),
                "vehicle_path": match["entity"].get("vehicle_path"),
                "distance": match["distance"],
            })
    
    return {"results": formatted_results}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5123)
