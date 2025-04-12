FROM python:3.10.15-slim-bullseye

WORKDIR /app


RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 -y

COPY ./deployment/ai_services/requirements.txt .
RUN pip install -r requirements.txt --timeout=1000 --no-cache-dir
RUN pip uninstall -y opencv-python-headless opencv-python
RUN pip install opencv-python

COPY ./src/ai_services ./src/ai_services
COPY .env ./.env