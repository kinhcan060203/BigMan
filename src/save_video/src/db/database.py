from peewee import PostgresqlDatabase
from config import (
    DATABASE_NAME,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
)

# Initialize the database connection
db = PostgresqlDatabase(
    DATABASE_NAME,
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
)
# Bind models to the database
from src.modules.models import Camera, CameraService, Service, Event, Recordings

db.bind([Camera, CameraService, Service, Event, Recordings])
db.connect()
