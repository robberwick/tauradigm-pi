from PIL import Image
import numpy as np
import time
from datetime import datetime


FPS_MODE_OFF = 0
FPS_MODE_T0 = 1
FPS_MODE_FBF = 2
FPS_MODE = FPS_MODE_OFF

WRITE_IMAGES = True  # False

def write_luminance_disk(y_data, frame):
    date = datetime.now()
    timestamp = date.strftime('%H-%M-%S')
    filename = f'frame-{frame}-{timestamp}.bmp'
    im = Image.fromarray(y_data, mode='L')  # using luminance mode
    im.save(filename)


class RecordingOutput(object):
    """
    Object mimicking file-like object so start_recording will write each frame to it.
    See: https://picamera.readthedocs.io/en/release-1.12/api_camera.html#picamera.PiCamera.start_recording
    """
    def __init__(self):
        self.fwidth = 0
        self.fheight = 0
        self.frame_cnt = 0
        self.t0 = 0

    def write(self, buf):
        global t_prev
        # write will be called once for each frame of output. buf is a bytes
        # object containing the frame data in YUV420 format; we can construct a
        # numpy array on top of the Y plane of this data quite easily:
        y_data = np.frombuffer(buf,
            dtype=np.uint8,
            count=self.fwidth * self.fheight
        ).reshape((self.fheight, self.fwidth))

        # actual processing
        if WRITE_IMAGES and self.frame_cnt % 20 == 0:
            write_luminance_disk(y_data, self.frame_cnt)

        self.frame_cnt += 1

        if FPS_MODE is not FPS_MODE_OFF:
            if FPS_MODE == FPS_MODE_FBF:
                # frame by frame difference
                dt = time.time() - t_prev  # dt
                t_prev = time.time()
                fps = 1.0 / dt
            else:
                # calculation based on time elapsed since capture start
                dt = time.time() - self.t0  # dt
                fps = self.frame_cnt / dt

            if self.frame_cnt % 10 == 0:
                print(f'fps: {round(fps, 2)}')

    def flush(self):
        pass  # called at end of recording