FROM python:3.10.15-slim-bullseye

WORKDIR /app

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 -y


RUN pip install uv
ENV UV_HTTP_TIMEOUT=1000
ENV UV_LINK_MODE=copy

COPY ./deployment/ai_services/requirements.txt .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install -r requirements.txt --system 

RUN pip uninstall -y opencv-python-headless opencv-python
RUN uv pip install opencv-python

