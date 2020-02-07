import random
import struct
import time
from collections import namedtuple

from pySerialTransfer import pySerialTransfer as txfer

def send_motor_speed_message(link=None, left=0, right=0):
    payload = struct.pack('ff', left, right)
    for i, b in enumerate(list(payload)):
        link.txBuff[i] = b

    print('left: {}, right: {}, sending: {}'.format(left, right, payload))
    link.send(len(payload))

if __name__ == '__main__':
    try:
        link = txfer.SerialTransfer('/dev/serial0', baud=1152000, restrict_ports=False)
        while True:
            for x in range(0, 100):
                send_motor_speed_message(link=link, left=x, right=x )
                time.sleep(0.02)
            for x in range(100, 0, -1):
                send_motor_speed_message(link=link, left=x, right=x )
                time.sleep(0.02)
            for x in range(0, -100, -1):
                send_motor_speed_message(link=link, left=x, right=x )
                time.sleep(0.02)
            for x in range(-100, 0):
                send_motor_speed_message(link=link, left=x, right=x )
                time.sleep(0.02)


    except KeyboardInterrupt:
        send_motor_speed_message(link=link, left=0, right=0)
        link.close()