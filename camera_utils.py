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
    rowCopy = receivedRow.copy() 
    row = memoryview(rowCopy)

    lineCounts = []
    linePositions = []
    threshold = 125
    in = False
    start = 0
    for val in row:
        if val > threshold:
            #not line
            if in:
                lineCounts.append(row - start)
                linePositions.append((start + row)/2)
                in = False
        else:
            #line
            if !in:
                start = row
                in = True
    if in and row-start >= 2:
        lineCounts.append(row-start)
        linePositions.append((start + row)/2)

    maxLineWidth = 1000
    if lineCounts[0] < maxLineWidth and lineCounts[0] >0:
        linePositions[0] = 2 * weightedAverage / len(row) / lineCounts[0]
        linePositions[0] -= 1
    else:
        linePositions[0] = -2

    return linePositions, lineCounts


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
        self.pGain = 0.25
        self.linePosition = [0] * 50
        self.lineWidth = [0] * 50


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
        sliceStep = 1
        for i in range(0, self.fheight//2, sliceStep):
            newLinePosition, newLineWidth = processRow(u_data[i])
            if newLinePosition[0] != -2:
                index = int(i/sliceStep)
                self.linePosition[index] = newLinePosition[0]
                self.lineWidth[index] = newLineWidth[0]
        maxTurnCorrection = 0.25
        self.turnCommand = min(self.pGain * self.linePosition[35], maxTurnCorrection)
        self.turnCommand = max(self.turnCommand, -maxTurnCorrection)

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

    
