from PIL import Image
import numpy as np
import time
from datetime import datetime


FPS_MODE_OFF = 0
FPS_MODE_T0 = 1
FPS_MODE_FBF = 2
FPS_MODE = FPS_MODE_OFF

WRITE_IMAGES = False

def write_luminance_disk(data, frame, channel):
    date = datetime.now()
    timestamp = date.strftime('%H-%M-%S')
    filename = f'images/frame-{frame}-{timestamp}-{channel}.bmp'
    im = Image.fromarray(data, mode='L')  # if using luminance mode
    im.save(filename)

def process_row(received_row):
    """Returns a tuple of (line position (center) and line width for the given row data"""
    rowCopy = received_row.copy()
    row = memoryview(rowCopy) #[y*w:(y+1)*w]
    image_width = len(row)
    line_counts = []
    line_positions = []
    threshold = 110
    min_width = 2
    inside_line = False
    start = 0
    x = 0
    line_min = threshold
    for val in row:
        if val > threshold:
            #not line
            if inside_line:
                line_width = x - start
                if line_width > min_width:
                    line_counts.append(line_width)
                    line_position = (x + start)/image_width - 1
                    line_positions.append(line_position)
                inside_line = False
        else:
            #line
            if not inside_line:
                start = x
                inside_line = True
        x = x + 1
    if inside_line and (x - start) >= 2:
        line_counts.append(x - start)
        line_positions.append((x + start)/image_width - 1)

    return line_positions, line_counts

def process_col(received_col):
    """returns fraction of col below threshold"""
    colCopy = received_col.copy()
    col = memoryview(colCopy) #[y*w:(y+1)*w]
    image_height = len(col)
    line_count = 0
    threshold = 100
    x = 0
    for val in col:
        if val > threshold:
            pass
        else:
            line_count = line_count + 1
    
    wall_fraction = line_count / image_height

    return wall_fraction

class RecordingOutput(object):
    """
    Object mimicking file-like object so start_recording will write each frame to it.
    See: https://picamera.readthedocs.io/en/release-1.12/api_camera.html#picamera.PiCamera.start_recording
    """
    def __init__(self, height=50, width=50, read_row_pos_percent=88):
        self.fheight = height
        self.fwidth = width
        self.frame_cnt = 0
        self.t0 = 0
        self.p_gain = 0.25
        self.d_gain = 0.1
        self.yuv_data = dict(y=None, u=None, v=None)
        self.line_position_at_row = [0] * self.fheight
        self.line_width_at_row = [0] * self.fheight
        self.read_row_pos_percent = read_row_pos_percent
        self.last_fork_time = 0
        self.tentative_fork_time =0
        self.fork_time_threshold = 0.025
        self.fork_timeout = 0.5
        self.fork_number = 0
        self.wall_closeness = 0
        self.last_line_position = 0

    def get_channel_height(self, channel='u'):
        return self.fheight if channel.lower() == 'y' else self.fheight // 2

    def get_channel_width(self, channel='u'):
        return self.fwidth if channel.lower() == 'y' else self.fwidth // 2

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
         #   write_luminance_disk(self.yuv_data['v'], self.frame_cnt, 'V')
        self.frame_cnt += 1

        # Extract line data
        self.extract_line_positions()
        self.extract_wall_distance()

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
        read_row = int((self.get_channel_height(channel=channel) / 100) * self.read_row_pos_percent)
        new_line_position, new_line_width = process_row(data[read_row])
        self.line_position_at_row[read_row] = new_line_position
        self.line_width_at_row[read_row] = new_line_width

    def extract_wall_distance(self, channel='y'):
        """Extract the wall position from the current image data using the specified channel"""
        slice_step = 1

        # select data from channel
        data = self.yuv_data[channel]
        self.wall_closeness = process_col(data[:,48])

            

    def get_turn_command(self, channel='u', fork='left'):
        """Calculate the turn command from the currently calculated line positions and a L or R fork option"""
        max_turn_correction = 0.18
        turn_at_fork = 0.5
        # why are we calculating the line positions of all the rows, if we're only looking at the value for row 35?
        read_row = int((self.get_channel_height(channel=channel) / 100) * self.read_row_pos_percent)
        #print(self.line_position_at_row[read_row])
        if type(self.line_position_at_row[read_row]) is list:
            lines = len(self.line_position_at_row[read_row])
        else:
            lines = 1
        if lines > 1 and (self.last_fork_time + self.fork_timeout < time.time()):
            #we appear to be on a fork, record the time if we've not already
            if self.tentative_fork_time is None:
                self.tentative_fork_time = time.time()
        else:
            #we're not on a fork, wipe time check
            self.tentative_fork_time = None

        if (lines > 1
                and (self.last_fork_time + self.fork_timeout < time.time())
                and (time.time() > self.tentative_fork_time + self.fork_time_threshold)):
            #new junction detected
            self.fork_number += 1
            print(self.fork_number)
            self.last_fork_time = time.time()
            if fork == 'left':
                return -turn_at_fork
            else:
                return turn_at_fork

        if type(self.line_position_at_row[read_row]) is list and len(self.line_position_at_row[read_row])>0:
            if fork == 'left':
                line_position = self.line_position_at_row[read_row][0]
            else:
                line_position = self.line_position_at_row[read_row][lines-1]
        else:
            # make line position all the way to one side of the image, on the side we last saw it
            line_position = self.last_line_position/abs(self.last_line_position) 
        turn_command = self.p_gain * line_position
        turn_command -= self.d_gain * (line_position - self.last_line_position)
        turn_command = max(min(turn_command, max_turn_correction), -max_turn_correction)
        self.last_line_position = line_position
        return turn_command
