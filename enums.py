from enum import IntEnum, unique

@unique
class MessageType(IntEnum):
    COMMAND_MOTOR_SPEED = 0
    RECEIVE_SENSOR_DATA = 1