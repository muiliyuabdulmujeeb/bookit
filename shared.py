import enum

class RoleEnum(enum.Enum):
    USER = "user"
    ADMIN = "admin"

class IsActiveEnum(enum.Enum):
    TRUE = "true"
    FALSE = "false"

class StatusEnum(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class UpdateBookingAction(enum.Enum):
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"