from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import datetime, timezone
from shared import StatusEnum, UpdateBookingAction


class CreateBooking(BaseModel):
    user_id: str = Field(...)
    service_id: str = Field(...)
    start_time: Optional[datetime] = datetime.now(tz= timezone.utc)
    end_time: datetime = Field(...)
    status: StatusEnum = Field(...)

    @field_validator("start_time")
    @classmethod
    def check_start_time(cls, v: Optional[datetime])-> Optional[datetime]:
        if v is None:
            return v
        now = datetime.now(tz= timezone.utc)
        if v < now:
            raise ValueError("start_time must not be in the past")
        return v
    
    @field_validator("end_time")
    @classmethod
    def check_end_time(cls, v: datetime)-> datetime:
        now = datetime.now(tz= timezone.utc)
        if v < now:
            raise ValueError("end_time must not be in the past")
        return v
    @model_validator(mode="after")
    def check_times(self):
        if self.start_time > self.end_time:
            raise ValueError("end_time must be after start_time")
    
class CreateBookingResponseModel(CreateBooking):
    message: Optional[str]
    id: str
    created_at: datetime

class GetBookingResponseModel(BaseModel):
    message: Optional[str]
    id: str
    user_id = str
    service_id = str
    start_time: datetime
    end_time: datetime
    role: StatusEnum
    created_at: datetime

class UpdateBooking(CreateBooking):
    action: Optional[UpdateBookingAction] = None, Field(description="(user only) you can only reschedule or cancel if your booking is pending or confirmed")
    start_time: Optional[datetime] = None, Field(description="(user only) if you intend to reschedule, please set the new start_time otherwise leave it blank")
    end_time: Optional[datetime] = None, Field(description="(user only) if you intend to reschedule, please set the new end_time otherwise leave it blank")
    update_status_to: Optional[StatusEnum] = None, Field(description="(admin only) input the new status")


    @field_validator("start_time")
    @classmethod
    def check_update_start_time(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return v
        now = datetime.now(tz= timezone.utc)
        if v < now:
            raise ValueError("start_time must not be in the past")
        return v
    
    @model_validator(mode="after")
    def check_times(self):
       if self.start_time > self.end_time:
            raise ValueError("end_time must be after start_time")