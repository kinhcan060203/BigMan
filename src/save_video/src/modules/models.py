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

# Each model is a table in the database


# Camera model
class Camera(Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    camera_id = CharField()
    name = CharField()
    url = CharField()
    resolution = JSONField()
    data = JSONField()

    class Meta:
        db_table = "camera"


# Service model
class Service(Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField()

    class Meta:
        db_table = "service"


# This table uses the id of the camera and the id of the service to create a unique key
class CameraService(Model):
    camera_id = ForeignKeyField(Camera, backref="services", on_delete="CASCADE")
    service_id = ForeignKeyField(Service, backref="cameras", on_delete="CASCADE")
    data = JSONField()

    class Meta:
        db_table = "camera_service"
        primary_key = CompositeKey("camera_id", "service_id")


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



class Timeline(Model):  # type: ignore[misc]
    timestamp = DateTimeField()
    source = CharField(index=True, max_length=20)  # ex: tracked object, audio, external
    event_id = ForeignKeyField(
        Event, backref="timeline", on_delete="CASCADE", field="event_id"
    )
    class_type = CharField(max_length=50)  # ex: entered_zone, audio_heard
    data = JSONField()  # ex: tracked object id, region, box, etc.

    class Meta:
        db_table = "timeline"


class Regions(Model):  # type: ignore[misc]
    camera = CharField(null=False, primary_key=True, max_length=20)
    grid = JSONField()  # json blob of grid
    last_update = DateTimeField()


class Recordings(Model):  # type: ignore[misc]
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    event_id = ForeignKeyField(
        Event, backref="recordings", on_delete="CASCADE", field="event_id"
    )
    path = CharField(unique=True)
    start_time = DateTimeField()
    end_time = DateTimeField()
    duration = FloatField()
    dBFS = IntegerField(null=True)
    segment_size = FloatField(default=0)  # this should be stored as MB

    class Meta:
        db_table = "recordings"


class Export(Model):  # type: ignore[misc]
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    event_id = ForeignKeyField(
        Event, backref="exports", on_delete="CASCADE", field="event_id"
    )
    name = CharField(index=True, max_length=100)
    date = DateTimeField()
    video_path = CharField(unique=True)
    thumb_path = CharField(unique=True)
    in_progress = BooleanField()

    class Meta:
        db_table = "export"


# class ReviewSegment(Model):  # type: ignore[misc]
#     id = CharField(null=False, primary_key=True, max_length=30)
#     camera = ForeignKeyField(
#         Camera, backref="review_segments", on_delete="CASCADE", field="camera_id"
#     )
#     start_time = DateTimeField()
#     end_time = DateTimeField()
#     has_been_reviewed = BooleanField(default=False)
#     severity = CharField(max_length=30)  # alert, detection, significant_motion
#     thumb_path = CharField(unique=True)
#     data = (
#         JSONField()
#     )  # additional data about detection like list of labels, zone, areas of significant motion

#     class Meta:
#         db_table = "review_segment"


class Previews(Model):  # type: ignore[misc]
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    event_id = ForeignKeyField(
        Event, backref="previews", on_delete="CASCADE", field="event_id"
    )
    name = CharField(index=True, max_length=100)
    path = CharField(unique=True)
    start_time = DateTimeField()
    end_time = DateTimeField()
    duration = FloatField()

    class Meta:
        db_table = "previews"


# Used for temporary table in record/cleanup.py
class RecordingsToDelete(Model):  # type: ignore[misc]
    id = CharField(null=False, primary_key=False, max_length=30)

    class Meta:
        temporary = True


class User(Model):  # type: ignore[misc]
    username = CharField(null=False, primary_key=True, max_length=30)
    password_hash = CharField(null=False, max_length=120)


class WatchListLicensePlate(Model):  # type: ignore[misc]
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    license_plate = CharField(null=False, max_length=20)
    data = JSONField()

    class Meta:
        db_table = "watch_list_license_plate"


