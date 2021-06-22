from json.decoder import JSONDecodeError
from approxeng.input.selectbinder import ControllerResource
import array
import json
import random
import struct
import sys
import time
from collections import namedtuple

import click
from loguru import logger

from pySerialTransfer import pySerialTransfer as txfer
import navigation
from navigation import Pose
from enum import IntEnum

data_filter = lambda record: record["level"].name == "DATA"
non_data_filter = lambda record: record["level"].name != "DATA"

logger.remove()
logger.level("DATA", no=15)
fmt = "{time} - {name} - {level} - {message}"
logger.add("logs/debug_1.log", level="DEBUG", format=fmt, rotation="5 MB", filter=non_data_filter)
logger.add(sys.stdout, level="INFO", format=fmt, filter=non_data_filter)
logger.add("logs/info_1.log", level="INFO", format=fmt, rotation="5 MB", filter=non_data_filter)
logger.add("logs/data_{time}.log", level="DATA", format="{message}", filter=data_filter)
log_data = None

class Mode(IntEnum):
    travelling = 0,
    travelled = 1,
    rotating = 2,
    rotated = 3,
    firing = 4,
    fired = 5,
    reloading = 6,
    reloaded = 7

start_position = Pose(0, 0, 0)
midway = Pose(450, 0, 0)
start_heading = Pose(0, 0, 0)
firing_heading = Pose(0, 0, -1.47)
firing_position = Pose(450, -300, 0)

class RobotStopException(Exception):
    pass

def mixer(yaw, throttle, max_power=100):
    """
    Mix a pair of joystick axes, returning a pair of wheel speeds. This is where the mapping from
    joystick positions to wheel powers is defined, so any changes to how the robot drives should
    be made here, everything else is really just plumbing.

    :param yaw:
        Yaw axis value, ranges from -1.0 to 1.0
    :param throttle:
        Throttle axis value, ranges from -1.0 to 1.0
    :param max_power:
        Maximum speed that should be returned from the mixer, defaults to 100
    :return:
        A pair of power_left, power_right integer values to send to the motor driver
    """
    left = throttle + yaw
    right = throttle - yaw
    scale = float(max_power) / max(1, abs(left), abs(right))
    return int(left * -scale), int(right * -scale)

def send_motor_speed_message(link=None, left=0, right=0):
    payload = struct.pack('=bff', 1, right, left)
    for i, b in enumerate(list(payload)):
        link.txBuff[i] = b
    # print('sending: {}'.format(payload))
    link.send(len(payload))

def send_button_press_message(link=None, button=' '):
    payload = struct.pack('=bc', 2, button)
    for i, b in enumerate(list(payload)):
        link.txBuff[i] = b
        link.send(len(payload))
 
def send_waypoint_message(link=None, pose=None):
    if pose:
        payload = struct.pack('=bfff', 3, pose.x, pose.y, pose.heading)
        for i, b in enumerate(list(payload)):
            link.txBuff[i] = b
        # print('sending: {}'.format(payload))
        link.send(len(payload))

def send_straight_move_message(link=None, pose=None):
    if pose:
        payload = struct.pack('=bfff', 4, pose.x, pose.y, pose.heading)
        for i, b in enumerate(list(payload)):
            link.txBuff[i] = b
        # print('sending: {}'.format(payload))
        link.send(len(payload))

def send_rotate_message(link=None, pose=None):
    if pose:
        payload = struct.pack('=bfff', 5, pose.x, pose.y, pose.heading)
        for i, b in enumerate(list(payload)):
            link.txBuff[i] = b
        # print('sending: {}'.format(payload))
        link.send(len(payload))

def unpack_log_message(link=None):
#    fmt = 'f' * 8 + 'l' * 6 + 'f' * 3 + 'f' * 3
    fmt = 'f' * 3 + 'f' * 3 + 'b'

    response = array.array('B', link.rxBuff[:link.bytesRead]).tobytes()

    return struct.unpack(fmt, response)

def extract_current_pose(log_vars):
    """Extract the current pose from the tuple of values extracted from the log message"""
    *_, x, y, heading, current_mode = log_vars
    return navigation.Pose(x, y, heading)

def extract_current_mode(log_vars):
    """Extract the current mode from the tuple of values extracted from the log message"""
    *_, current_mode = log_vars
    return Mode(current_mode)

def feed_the_fish(link, current_mode, process_step):
    new_process_step = process_step
    if process_step == 0 and current_mode != Mode.travelling:
        send_straight_move_message(link=link, pose=midway)
        print("moving to midway")
    if process_step == 0 and current_mode == Mode.travelling:
        print("moving to midway")
        new_process_step = 1
    elif process_step == 1 and current_mode == Mode.travelled:
        send_rotate_message(link=link, pose=firing_heading)
        print("sending rotating command")
    elif process_step == 1 and current_mode == Mode.rotating:
        print("rotating")
        new_process_step = 2
    elif process_step == 2 and current_mode == Mode.rotated:
        send_straight_move_message(link=link, pose=firing_position)
        print("sending move to firing")
    elif process_step == 2 and current_mode == Mode.travelling:
        new_process_step = 3
    elif process_step == 3 and current_mode == Mode.travelled:
        send_rotate_message(link=link, pose=firing_heading)
        print("sending aiming command")
    elif process_step == 3 and current_mode == Mode.rotating:
        print("rotating")
        new_process_step = 4
    elif process_step == 4 and current_mode == Mode.rotated:
        send_button_press_message(link,button=b't')
        print("moved to firing")
    elif process_step == 4 and current_mode == Mode.fired:
        send_straight_move_message(link=link, pose=midway)
        print("fired")
    elif process_step == 4 and current_mode == Mode.travelling:
        print("moving back to midway")
        new_process_step = 5
    elif process_step == 5 and current_mode == Mode.travelled:
        send_rotate_message(link=link, pose=start_heading)
        print("moved back to midway")
    elif process_step == 5 and current_mode == Mode.rotating:
        print("rotating back to start")
        new_process_step = 6
    elif process_step == 6 and current_mode == Mode.rotated:
        send_straight_move_message(link=link, pose=start_position)
        print("rotated back for start")
    elif process_step == 6 and current_mode == Mode.travelling:
        send_straight_move_message(link=link, pose=start_position)
        print("moving back to start")
        new_process_step = 7
    elif process_step == 7 and current_mode == Mode.travelled:
        print("moved back to start")
        new_process_step = 8
    return new_process_step
    
@click.command()
@click.option('--waypoints', default=None, help='waypoint file')
def run(waypoints=None):
    waypoint_list = None
    navigating = False
    driving = True
    fish_feeding = False
    current_mode = None
    process_step = 0
    shot_number = 1
    shots_allowed = 3

    try:
        link = txfer.SerialTransfer('/dev/serial0', baud=500000, restrict_ports=False)
        battery_checked = False
        send_button_press_message(link,button=b'l')
        send_button_press_message(link,button=b'r')

        while True:
            # Inner try / except is used to wait for a controller to become available, at which point we
            # bind to it and enter a loop where we read axis values and send commands to the motors.
            try:
                # Bind to any available joystick, this will use whatever's connected as long as the library
                # supports it.
                with ControllerResource(dead_zone=0.1, hot_zone=0.2) as joystick:
                    logger.info('Controller found, press HOME button to exit, use left stick to drive.')
                    logger.info(joystick.controls)

                    # Loop until the joystick disconnects, or we deliberately stop by raising a
                    # RobotStopException
                    while joystick.connected:
                        if not battery_checked:
                            battery_level = joystick.battery_level
                            if battery_level:
                                if battery_level<=0.25:
                                    logger.info('battery flat, only at: {:.2f}'.format(joystick.battery_level))
                                    logger.info('exiting')
                                    raise RobotStopException()
                                else:
                                    logger.info('battery level: {:.2f}'.format(joystick.battery_level))
                                    battery_checked = True

                        # Get virtual right axis joystick values from the right analogue stick
                        virt_x_axis, virt_y_axis = joystick['r']
                        power_left, power_right = mixer(yaw=virt_x_axis, throttle=virt_y_axis)
                        # Get a ButtonPresses object containing everything that was pressed since the last
                        # time around this loop.
                        joystick.check_presses()
                        # Print out any buttons that were pressed, if we had any
                        if joystick.has_presses:
                            logger.debug(joystick.presses)
                        if joystick.has_presses:
                            time.sleep(0.06)
                            logger.debug(joystick.presses)
                            if joystick.presses.start:
                                print("started")
                                fish_feeding = True
                            if joystick.presses.circle:
                                #send_button_press_message(link,button=b'c')
                                logger.info('circle button pressed')
                                test_B = Pose(450, 0, 0)
                                send_straight_move_message(link=link, pose=test_B)
                            if joystick.presses.triangle:
                                send_button_press_message(link,button=b't')
                                logger.info('triangle button pressed')
                                driving = True
                            if joystick.presses.square:
                                #send_button_press_message(link,button=b's')
                                test_A = Pose(0, 0, 0)
                                send_straight_move_message(link=link, pose=test_A)
                                logger.info('square button pressed')
                            if joystick.presses.cross:
                                send_button_press_message(link,button=b'x')
                                logger.info('cross button pressed')
                                driving = False
                                fish_feeding = False
                            if joystick.presses.dleft:
                                send_button_press_message(link,button=b'l')
                                logger.info('D pad left pressed')
                            if joystick.presses.dright:
                                send_button_press_message(link,button=b'r')
                                logger.info('D pad right pressed')
                            if joystick.presses.dup:
                                send_button_press_message(link,button=b'u')
                                logger.info('D pad up pressed')
                                navigating = True
                            if joystick.presses.ddown:
                                send_button_press_message(link,button=b'd')
                                logger.info('D pad down pressed')
                                navigating = False
                            if joystick.presses.l1:
                                logger.info('left 1 trigger pressed')
                                firing_position = Pose(450, -300, 0)
                                send_straight_move_message(link=link, pose=firing_position)
                            if joystick.presses.l2:
                                logger.info('left 2 trigger pressed')
                                west = Pose(0, 0, -1.47)
                                send_rotate_message(link=link, pose=west)
                            if joystick.presses.r2:
                                logger.info('right 2 trigger pressed')
                                north = Pose(0, 0, 0)
                                send_rotate_message(link=link, pose=north)
                            time.sleep(0.05)
                        # If home was pressed, raise a RobotStopException to bail out of the loop
                        # Home is generally the PS button for playstation controllers, XBox for XBox etc
                        if 'home' in joystick.presses:
                            logger.info('Home button pressed - exiting')
                            raise RobotStopException()
                        if not driving:
                            power_left, power_right = 0, 0
                        send_motor_speed_message(link=link, left=power_left, right=power_right)
                        time.sleep(0.03)
                        if link.available():
                            # unpack the incoming log message into a tuple
                            message_values = unpack_log_message(link=link)

                            # log the values
                            log_data = (time.time(),) + message_values
                            logger.log('DATA', ','.join(map(str,log_data)))
                            # Get the current pose from the message values
                            current_mode = extract_current_mode(message_values)
                            # Is the current position close enough to the target waypoint to select the next one?

                            if fish_feeding:
                                if process_step == 8:
                                    #we've travelled back to the square, so set mode back to start
                                    # and get ready to go again
                                    process_step = 0
                                    if shot_number < shots_allowed:
                                        shot_number += 1
                                        process_step = feed_the_fish(link, current_mode, process_step)
                                    else:
                                        fish_feeding = False
                                else:
                                    process_step = feed_the_fish(link, current_mode, process_step)
                        else:
                            link_msg = 'no data - link status: {}'.format(link.status)
                            logger.info(link_msg)
                        time.sleep(0.03)

            except IOError:
                # We get an IOError when using the ControllerResource if we don't have a controller yet,
                # so in this case we just wait a second and try again after printing a message.
                logger.info('No controller found yet')
                batteryChecked = False
                send_motor_speed_message(link=link)
                time.sleep(1)
    except (RobotStopException, KeyboardInterrupt):
        link.close()
        # This exception will be raised when the home button is pressed, or the controller
        # battery is flat, at which point we should stop the motors.
        send_motor_speed_message(link=link)

if __name__ == "__main__":
    run()
