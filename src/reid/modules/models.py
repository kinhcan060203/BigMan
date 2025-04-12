import uuid
from peewee import (
    BooleanField,
    CharField,
    DateTimeField,
    FloatField,
    IntegerField,
    Model,
    TextField,
    UUIDField,
    ForeignKeyField,
    CompositeKey,
)
from playhouse.postgres_ext import JSONField


# Camera model
class Camera(Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    area_id = CharField()
    area_name = CharField()
    camera_id = CharField(unique=True)
    resolution = JSONField()
    camera_name = CharField()
    url = CharField()
    data = JSONField()

    class Meta:
        db_table = "camera"



class Event(Model):  # type: ignore[misc]
    event_id = UUIDField(primary_key=True, default=uuid.uuid4)
    event_type = CharField(index=True, max_length=20)
    camera_id = ForeignKeyField(
        Camera, backref="events", on_delete="CASCADE", field="camera_id"
    )
    start_time = DateTimeField()
    end_time = DateTimeField()
    full_thumbnail_path = TextField()
    target_thumbnail_path = TextField()
    is_reviewed = BooleanField(default=False)
    data = JSONField()  
    class Meta:
        db_table = "event"


class Vehicle(Model):  # type: ignore[misc]
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    license_plate = CharField(null=False, max_length=20)
    data = JSONField()
    thumbnail = CharField(null=False, max_length=255)
    snapshot_at = DateTimeField()
    camera_id = ForeignKeyField(
        Camera, backref="vehicles", on_delete="CASCADE", field="camera_id"
    )
    embedding_id = CharField(null=False, max_length=50)
    created_at = DateTimeField()

    class Meta:
        db_table = "vehicle"
        
class WatchListLicensePlate(Model):  # type: ignore[misc]
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    license_plate = CharField(null=False, max_length=20)
    data = JSONField()

    class Meta:
        db_table = "watch_list_license_plate"

