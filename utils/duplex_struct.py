import random
import struct
import time
from collections import namedtuple

from pySerialTransfer import pySerialTransfer as txfer

if __name__ == '__main__':
    try:
        link = txfer.SerialTransfer('/dev/serial0', baud=1152000, restrict_ports=False)
        while True:
            # x = random.uniform(-500, 500)
            # y = random.uniform(-500, 500)
            # z = random.uniform(-500, 500)
            # payload = struct.pack('fff', x, y, z)
            # for i, b in enumerate(list(payload)):
            #     link.txBuff[i] = b
            # link.send(len(payload))

            if not link.available():
                if link.status < 0:
                    print('ERROR: {}'.format(link.status))
            else:
                payload = struct.unpack('ffffffff', bytearray(link.rxBuff[0:link.bytesRead]))
                print(payload)
            time.sleep(0.02)

    except KeyboardInterrupt:
        link.close()