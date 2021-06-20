from PIL import Image, ImageDraw
import numpy as np
import time
from datetime import datetime


FPS_MODE_OFF = 0
FPS_MODE_T0 = 1
FPS_MODE_FBF = 2
FPS_MODE = FPS_MODE_OFF

WRITE_IMAGES = True #False

def write_luminance_disk(data, frame, channel, line_positions=None, line_widths=None, read_row=None):
    date = datetime.now()
    timestamp = date.strftime('%H-%M-%S')
    filename = f'images/frame-{frame}-{timestamp}-{channel}.bmp'
    im = Image.fromarray(data, mode='L')  # if using luminance mode

    scaling_factor = 1 if channel.lower() != 'y' else 2

    # if we have line positions, plot them
    if line_positions:
        draw = ImageDraw.Draw(im)
        # iterate through all rows in line_positions
        for row_num, lines_at_row in enumerate(line_positions):
            # row will contain an array of midpoints for detected lines

            for found_line_number, line_pos in enumerate(lines_at_row):
                # if we have line width, draw that first
                if line_widths:
                    # we should have a corresponding width for every found line
                    try:
                        row_line_widths = line_widths[found_line_number]
                        if row_line_widths:
                            for row_line_width in row_line_widths:
                                line_width_start = line_pos - (row_line_width // 2)
                                # draw the line width in white (black if it's the read_row)
                                line_width_colour = 0 if row_num == read_row else 255
                                line_y = row_num * scaling_factor
                                line_start_x = line_width_start * scaling_factor
                                line_end_x = (line_width_start + row_line_width) * scaling_factor
                                draw.line([(line_start_x, line_y), (line_end_x, line_y)], fill=line_width_colour)
                    except KeyError:
                        pass

                # draw the center point of the line in black (white if it's the read_row)
                center_dot_colour = 255 if row_num == read_row else 0
                im.putpixel((line_pos * scaling_factor, row_num * scaling_factor), center_dot_colour)

    im.save(filename)

def process_row(received_row):
    """Returns a tuple of (line position (distance from center of row -1 to 1), line widths, and center position in pixels of each line found for the given row data"""
    rowCopy = received_row.copy()
    row = memoryview(rowCopy) #[y*w:(y+1)*w]
    image_width = len(row)
    line_widths = []
    line_positions = []
    line_centers = []
    threshold = 125
    min_width = 2
    inside_line = False
    start = 0
    x = 0
    for val in row:
        if val > threshold:
            #not line
            if inside_line:
                line_width = x - start
                if line_width > min_width:
                    # it's a legit line - save it
                    line_widths.append(line_width)
                    line_position = (x + start)/image_width - 1
                    line_positions.append(line_position)
                    line_centers.append((x + start) // 2)
                inside_line = False
        else:
            #line
            if not inside_line:
                start = x
                inside_line = True
        x = x + 1

    line_width_px = x - start
    if inside_line and (line_width_px >= 2):
        line_widths.append(line_width_px)
        line_positions.append((x + start)/image_width - 1)
        line_centers.append((x + start) // 2)

    return line_positions, line_widths, line_centers


class RecordingOutput(object):
    """
    Object mimicking file-like object so start_recording will write each frame to it.
    See: https://picamera.readthedocs.io/en/release-1.12/api_camera.html#picamera.PiCamera.start_recording
    """
    def __init__(self, height=50, width=50, read_row_pos_percent=80):
        self.fheight = height
        self.fwidth = width
        self.frame_cnt = 0
        self.t0 = 0
        self.p_gain = 0.25
        self.yuv_data = dict(y=None, u=None, v=None)
        self.line_position_at_row = [[]] * self.fheight
        self.line_width_at_row = [[]] * self.fheight
        self.line_centers_at_row = [[]] * self.fheight
        self.read_row_pos_percent = read_row_pos_percent
        self.last_fork_time = 0
        self.fork_timeout = 0.5

    def get_channel_height(self, channel='u'):
        return self.fheight if channel.lower() == 'y' else self.fheight // 2

    def get_channel_width(self, channel='u'):
        return self.fwidth if channel.lower() == 'y' else self.fwidth // 2

    def get_read_row(self, channel='u'):
        return int((self.get_channel_height(channel=channel) / 100) * self.read_row_pos_percent)

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

        # Extract line data
        self.extract_line_positions()

        # actual processing
        if WRITE_IMAGES and self.frame_cnt % 5 == 0:
            for channel in ['y', 'u']:
                write_luminance_disk(
                    self.yuv_data[channel],
                    self.frame_cnt,
                    channel.upper(),
                    line_positions=self.line_centers_at_row,
                    line_widths=self.line_width_at_row,
                    read_row=self.get_read_row(channel)
                    )
            # write_luminance_disk(self.yuv_data['y'], self.frame_cnt, 'Y')
            # write_luminance_disk(self.yuv_data['u'], self.frame_cnt, 'U')
         #   write_luminance_disk(self.yuv_data['v'], self.frame_cnt, 'V')
        self.frame_cnt += 1

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
            line_positions, line_widths, line_centers = process_row(data[i])
            # perhaps we shouldn't be skipping empty lists here
            # but get_turn_command should do the right thing when it fails to pick up a line at the expected position?
            if line_positions:
                index = int(i/slice_step)
                self.line_position_at_row[index] = line_positions
                self.line_width_at_row[index] = line_widths
                self.line_centers_at_row[index] = line_centers


    def get_turn_command(self, channel='u', left_fork=True):
        """Calculate the turn command from the currently calculated line positions and a L or R fork option"""
        max_turn_correction = 0.5
        turn_at_fork = 1
        # why are we calculating the line positions of all the rows, if we're only looking at the value for row 35?
        read_row = self.get_read_row(channel=channel)
        lines = len(self.line_position_at_row[read_row])
        if lines > 1 and (self.last_fork_time + self.fork_timeout < time.time()):
            #new junction detected
            self.last_fork_time = time.time()
            if left_fork:
                return -turn_at_fork
            else:
                return turn_at_fork
        if left_fork:
            line_position = self.line_position_at_row[read_row][0]
        else:
            line_position = self.line_position_at_row[read_row][lines-1]
        turn_command = min(self.p_gain * line_position, max_turn_correction)
        turn_command = max(turn_command, -max_turn_correction)
        return turn_command
