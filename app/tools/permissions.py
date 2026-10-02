from enum import Enum


class PermissionLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    WRITE = "WRITE"
    EXTERNAL_ACTION = "EXTERNAL_ACTION"
    HIGH_RISK = "HIGH_RISK"
