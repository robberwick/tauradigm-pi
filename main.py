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

def unpack_log_message(link=None):
    fmt = 'f' * 8 + 'l' * 6 + 'f' * 3 + 'f' * 3

    response = array.array('B', link.rxBuff[:link.bytesRead]).tobytes()

    return struct.unpack(fmt, response)

def extract_current_pose(log_vars):
    """Extract the current pose from the tuple of values extracted from the log message"""
    *_, x, y, heading = log_vars
    return navigation.Pose(x, y, heading)

@click.command()
@click.option('--waypoints', default=None, help='waypoint file')
def run(waypoints=None):
    waypoint_list = None
    try:
        with open(waypoints) as fp:
            waypoint_list = json.load(fp)
    except (FileNotFoundError, JSONDecodeError):
        logger.error(f"Could not open waypoints file: {waypoints}")
        return
    navigator = navigation.Navigator(waypoints=waypoint_list)
    try:
        link = txfer.SerialTransfer('/dev/serial0', baud=1000000, restrict_ports=False)
        battery_checked = False


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
                            if joystick.presses.circle:
                                send_button_press_message(link,button=b'c')
                                logger.info('circle button pressed')
                            if joystick.presses.triangle:
                                send_button_press_message(link,button=b't')
                                logger.info('triangle button pressed')
                            if joystick.presses.square:
                                send_button_press_message(link,button=b's')
                                logger.info('square button pressed')
                            if joystick.presses.cross:
                                send_button_press_message(link,button=b'x')
                                logger.info('cross button pressed')
                            if joystick.presses.dleft:
                                send_button_press_message(link,button=b'l')
                                logger.info('D pad left pressed')
                            if joystick.presses.dright:
                                send_button_press_message(link,button=b'r')
                                logger.info('D pad right pressed')
                            if joystick.presses.dup:
                                send_button_press_message(link,button=b'u')
                                logger.info('D pad up pressed')
                            if joystick.presses.ddown:
                                send_button_press_message(link,button=b'd')
                                logger.info('D pad down pressed')
                            time.sleep(0.06)
                        # If home was pressed, raise a RobotStopException to bail out of the loop
                        # Home is generally the PS button for playstation controllers, XBox for XBox etc
                        if 'home' in joystick.presses:
                            logger.info('Home button pressed - exiting')
                            raise RobotStopException()
                        send_motor_speed_message(link=link, left=power_left, right=power_right)
                        if link.available():
                            # unpack the incoming log message into a tuple
                            message_values = unpack_log_message(link=link)

                            # log the values
                            log_data = (time.time(),) + message_values
                            logger.log('DATA', ','.join(map(str,log_data)))
                            # Get the current pose from the message values
                            current_pose = extract_current_pose(message_values)
                            # Is the current position close enough to the target waypoint to select the next one?
                            if current_pose is not None:
                                if navigator.should_increment_waypoint(current_pose):
                                    navigator.increment_waypoint_index()

                            # send the waypoint message to the teensy
                            send_waypoint_message(link=link, pose=navigator.target_waypoint)
                            print(navigator.target_waypoint)
                        else:
                            link_msg = 'no data - link status: {}'.format(link.status)
                            logger.info(link_msg)
                        time.sleep(0.02)

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
