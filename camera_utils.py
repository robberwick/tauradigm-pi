from PIL import Image
import numpy as np
import time
from datetime import datetime


FPS_MODE_OFF = 0
FPS_MODE_T0 = 1
FPS_MODE_FBF = 2
FPS_MODE = FPS_MODE_OFF

WRITE_IMAGES = True #False

def write_luminance_disk(data, frame, channel):
    date = datetime.now()
    timestamp = date.strftime('%H-%M-%S')
    filename = f'images/frame-{frame}-{timestamp}-{channel}.bmp'
    im = Image.fromarray(data, mode='L')  # if using luminance mode
    im.save(filename)

def processRow(receivedRow):
    minval = 255
    maxval = 0
    rowCopy = receivedRow.copy() 
    row = memoryview(rowCopy) #[y*w:(y+1)*w]

    x = 0
    weightedAverage = 0
    lineCount = 0
    threshold = 125
    for val in row:
        if val > threshold:
#            val = 255
            pass
        else:
#            val = 0
            weightedAverage += x
            lineCount += 1
#       row[x] = val
        x = x + 1
    maxLineWidth = 1000
    if lineCount < maxLineWidth and lineCount >0:
        linePosition = 2 * weightedAverage / len(row) / lineCount
        linePosition -= 1
    else:
        linePosition = -2

    return linePosition, lineCount

def processImage(imageHeight, data):
    sliceStep = 1
    linePosition = [0] * 50
    lineWidth = [0] * 50
    pGain = 0.25
    for i in range(0, imageHeight//2, sliceStep):
        newLinePosition, newLineWidth = processRow(data[i])
        if newLinePosition != -2:
            index = int(i/sliceStep)
            linePosition[index] = newLinePosition
            lineWidth[index] = newLineWidth
    maxTurnCorrection = 0.25
    turnCommand = min(pGain * linePosition[35], maxTurnCorrection)
    turnCommand = max(turnCommand, -maxTurnCorrection)
    return turnCommand

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
        self.turnCommand = 0


    def write(self, buf):
        global t_prev
        # write will be called once for each frame of output. buf is a bytes
        # object containing the frame data in YUV420 format; we can construct a
        # numpy array on top of the Y plane of this data quite easily:
        y_data = np.frombuffer(buf,
            dtype=np.uint8,
            count=self.fwidth * self.fheight
        ).reshape((self.fheight, self.fwidth))
        u_offset = self.fwidth * self.fheight
        u_data = np.frombuffer(buf,
            dtype=np.uint8,
            count=self.fwidth//2 * self.fheight//2,
            offset=u_offset
        ).reshape((self.fheight//2, self.fwidth//2))
        v_offset = self.fwidth * self.fheight + self.fwidth//2 * self.fheight//2
        v_data = np.frombuffer(buf,
            dtype=np.uint8,
            count=self.fwidth//2 * self.fheight//2,
            offset=int(v_offset)
        ).reshape((self.fheight//2, self.fwidth//2))
        # actual processing
        if WRITE_IMAGES and self.frame_cnt % 20 == 0:
            write_luminance_disk(y_data, self.frame_cnt, 'Y')
            write_luminance_disk(u_data, self.frame_cnt, 'U')
            write_luminance_disk(v_data, self.frame_cnt, 'V')
        self.frame_cnt += 1
        self.turnCommand = processImage(self.fheight, u_data)

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


