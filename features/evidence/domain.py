from enum import Enum


class EvidenceType(str, Enum):
    TEXT = "TEXT"
    STRUCTURED_DATA = "STRUCTURED_DATA"
    LINK = "LINK"
    FILE_METADATA = "FILE_METADATA"
