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

def process_row(received_row):
    """Returns a tuple of (line position (center) and line width for the given row data"""
    minval = 255
    maxval = 0
    rowCopy = received_row.copy()
    row = memoryview(rowCopy) #[y*w:(y+1)*w]

    x = 0
    weighted_average = 0
    line_count = 0
    threshold = 125
    for val in row:
        if val > threshold:
#            val = 255
            pass
        else:
#            val = 0
            weighted_average += x
            line_count += 1
#       row[x] = val
        x = x + 1
    max_line_width = 1000
    if line_count < max_line_width and line_count >0:
        line_position = 2 * weighted_average / len(row) / line_count
        line_position -= 1
    else:
        line_position = -2

    return line_position, line_count

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

        self.p_gain = 0.25
        self.yuv_data = dict(y=None, u=None, v=None)
        # TODO this 50 should probably be a constructor param
        self.line_position_at_row = [0] * 50
        self.line_width_at_row = [0] * 50

    def write(self, buf):
        global t_prev
        # write will be called once for each frame of output. buf is a bytes
        # object containing the frame data in YUV420 format; we can construct a
        # numpy array on top of the Y plane of this data quite easily:
        self.yuv_data['y'] = np.frombuffer(buf,
            dtype=np.uint8,
            count=self.fwidth * self.fheight
        ).reshape((self.fheight, self.fwidth))
        u_offset = self.fwidth * self.fheight
        self.yuv_data['u']  = np.frombuffer(buf,
            dtype=np.uint8,
            count=self.fwidth//2 * self.fheight//2,
            offset=u_offset
        ).reshape((self.fheight//2, self.fwidth//2))
        v_offset = self.fwidth * self.fheight + self.fwidth//2 * self.fheight//2
        self.yuv_data['v'] = np.frombuffer(buf,
            dtype=np.uint8,
            count=self.fwidth//2 * self.fheight//2,
            offset=int(v_offset)
        ).reshape((self.fheight//2, self.fwidth//2))
        # actual processing
        if WRITE_IMAGES and self.frame_cnt % 20 == 0:
            write_luminance_disk(self.yuv_data['y'], self.frame_cnt, 'Y')
            write_luminance_disk(self.yuv_data['u'], self.frame_cnt, 'U')
            write_luminance_disk(self.yuv_data['v'], self.frame_cnt, 'V')
        self.frame_cnt += 1

        # Extract line data
        self.extract_line_positions()

        if FPS_MODE is not FPS_MODE_OFF:
            if FPS_MODE == FPS_MODE_FBF:
                # frame by frame difference
                # HOW DOES THIS WORK?
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

    def extract_line_positions(self, channel='u'):
        """Extract the line positions from the current image data using the specified channel"""
        slice_step = 1

        # select data from channel
        data = self.yuv_data[channel]

        # TODO Only extract specified rows?
        for i in range(0, self.fheight // 2, slice_step):
            new_line_position, new_line_width = process_row(data[i])
            # is -2 just a magic number to indicate 'something went wrong' or 'nothing was found'?
            if new_line_position != -2:
                index = int(i/slice_step)
                self.line_position_at_row[index] = new_line_position
                self.line_width_at_row[index] = new_line_width


    def get_turn_command(self, channel='u'):
        """Calculate the turn command from the currently calculated line positions"""
        max_turn_correction = 0.25
        # why are we calculating the line positions of all the rows, if we're only looking at the value for row 35?
        turn_command = min(self.p_gain * self.line_position_at_row[35], max_turn_correction)
        turn_command = max(turn_command, -max_turn_correction)
        return turn_command