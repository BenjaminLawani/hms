from enum import Enum

class ComplainCategory(str, Enum):
    GENERAL = "general"
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    FURNITURE = "furniture"

class Status(str, Enum):
    CLOSED = "closed"
    OPENED = "opened"
    
class AllocationStatus(Enum):
    ALLOCATED = "allocated"
    VACATED = "vacated"
    PENDING = "pending"
    REJECTED = "rejected"