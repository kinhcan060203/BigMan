from subprocess import Popen
import sys
import time
import json
import os

if __name__ == "__main__":

    processes: list[Popen] = []
    filepath = "src/ai-streaming/config/camera.json"
    with open(filepath, "r") as f:
        config = json.load(f)
    try:
        total_cam = 12
        num_cam_per_process = 4
        device = 1
        env = os.environ.copy()
        for i in range(0, min(total_cam, len(config)), num_cam_per_process):
            env["CUDA_VISIBLE_DEVICES"] = str(device)
            processes.append(
                Popen(
                    [
                        "python",
                        "src/ai-streaming/main.py",
                        "--start_index",
                        str(i),
                        "--num_cam",
                        str(num_cam_per_process),
                        "--meta_file",
                        filepath,
                    ],
                    start_new_session=True,
                    env=env,
                )
            )
            device = (device + 1) % 2
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("Ctrl C")
    finally:
        for p in processes:
            p.terminate()
            p.wait()
