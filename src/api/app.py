from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pathlib
import json
dir = pathlib.Path(__file__).parent.resolve()
from config import (
    HLS_SERVER,
    API_PORT,
)
from utils.logger import logger
from modules.camera import HLSStreamManager

from router import (
    event,
    camera,
    reid_analysis,
    counting_analysis
)

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

app.include_router(camera.router)
app.include_router(event.router)
app.include_router(reid_analysis.router)
app.include_router(counting_analysis.router)

# hls_manager = HLSStreamManager(HLS_SERVER)

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title="docs",
        swagger_css_url="https://cdn.jsdelivr.net/gh/Itz-fork/Fastapi-Swagger-UI-Dark/assets/swagger_ui_dark.css",
    )

@app.get("/", include_in_schema=False)
async def index():
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    uvicorn.run(
        "app:app",  
        host="0.0.0.0",
        port=int(API_PORT),
        reload=True
    )
