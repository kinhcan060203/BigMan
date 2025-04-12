import faulthandler
import threading
from src.save_video import VideoDecoder

faulthandler.enable()

threading.current_thread().name = "save_video"

if __name__ == "__main__":
    decode_vd_moduler = VideoDecoder()
    decode_vd_moduler.start()
