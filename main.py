from approxeng.input.selectbinder import ControllerResource
import random
import struct
import time
from collections import namedtuple

from pySerialTransfer import pySerialTransfer as txfer

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
    return int(left * scale), int(right * scale)

def send_motor_speed_message(link=None, left=0, right=0):
    payload = struct.pack('ff', left, right)
    for i, b in enumerate(list(payload)):
        link.txBuff[i] = b
    print('sending: {}'.format(payload))
    link.send(len(payload))

def receive_sensor_data(link=None):
    fmt = 'f' * 8

    print('Response received:')

    response = ''
    for index in range(link.bytesRead):
        response += chr(link.rxBuff[index])

    distances = struct.unpack(fmt, response)

try:
    link = txfer.SerialTransfer('/dev/serial0', baud=1152000, restrict_ports=False)

    while True:
        # Inner try / except is used to wait for a controller to become available, at which point we
        # bind to it and enter a loop where we read axis values and send commands to the motors.
        try:
            # Bind to any available joystick, this will use whatever's connected as long as the library
            # supports it.
            with ControllerResource(dead_zone=0.1, hot_zone=0.2) as joystick:
                print('Controller found, press HOME button to exit, use left stick to drive.')
                print(joystick.controls)
                # Loop until the joystick disconnects, or we deliberately stop by raising a
                # RobotStopException
                while joystick.connected:
                    # Get virtual right axis joystick values from the right analogue stick
                    virt_x_axis, virt_y_axis = joystick['r']
                    power_left, power_right = mixer(yaw=virt_x_axis, throttle=virt_y_axis)
                    print('power left: {}, power right: {}'.format(power_left, power_right))

                    # Get a ButtonPresses object containing everything that was pressed since the last
                    # time around this loop.
                    joystick.check_presses()
                    # Print out any buttons that were pressed, if we had any
                    if joystick.has_presses:
                        print(joystick.presses)
                    # If home was pressed, raise a RobotStopException to bail out of the loop
                    # Home is generally the PS button for playstation controllers, XBox for XBox etc
                    if 'home' in joystick.presses:
                        raise RobotStopException()
                    send_motor_speed_message(link=link, left=power_left, right=power_right)
                    if link.available():
                        receive_sensor_data(link=link)
                    else:
                        print('no link available')
                    time.sleep(0.02)

        except IOError:
            # We get an IOError when using the ControllerResource if we don't have a controller yet,
            # so in this case we just wait a second and try again after printing a message.
            print('No controller found yet')
            send_motor_speed_message(link=link)
            time.sleep(1)
except (RobotStopException, KeyboardInterrupt):
    link.close()
    # This exception will be raised when the home button is pressed, at which point we should
    # stop the motors.
    print('Home button pressed - exiting')
    send_motor_speed_message(link=link)