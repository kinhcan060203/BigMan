from .crowd_detection import handle_crowd_detection
from .license_plate import handle_license_plate
from .vehicle_counting import handle_vehicle_counting
from .reid import handle_reid
from .speed_estimate import handle_speed_estimate
__all__ = [
    "handle_crowd_detection",
    "handle_vehicle_counting",
    "handle_license_plate",
    "handle_speed_estimate",
    "handle_reid"
]
