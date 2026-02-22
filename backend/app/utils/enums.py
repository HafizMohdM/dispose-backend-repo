from enum import Enum

class DriverStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"

class DriverAvailabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE" 


class NotificationStatus(str,Enum):
    UNREAD ="UNREAD"
    READ = "READ"

class NotificationType(str,Enum):
    DRIVER_ASSIGNED = "DRIVER_ASSIGNED"
    PICKUP_CREATED= "PICKUP_CREATED"
    PICKUP_COMPLETED="PICKUP_COMPLETED"
    SYSTEM = "SYSTEM"




    
