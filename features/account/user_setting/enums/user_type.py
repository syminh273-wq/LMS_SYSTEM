from enum import Enum


class UserTypes(str, Enum):
    CONSUMER = 'consumer'
    SPACE = 'space'
