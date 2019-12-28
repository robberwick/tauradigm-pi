import struct
from collections import namedtuple

from pySerialTransfer import pySerialTransfer as txfer

if __name__ == '__main__':
    try:
        link = txfer.SerialTransfer('/dev/serial0', baud=57600)
        while True:
            payload = struct.pack('fff', 101.1, 202.2, 303.3)
            for i, b in enumerate(list(payload)):
                link.txBuff[i] = b
            link.send(len(payload))

            while not link.available():
                if link.status < 0:
                    print('ERROR: {}'.format(link.status))

            payload = struct.unpack('bb', bytearray(link.rxBuff[0:link.bytesRead]))
            print('left: {}, right: {}'.format(*payload))

    except KeyboardInterrupt:
        link.close()