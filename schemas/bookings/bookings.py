from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from shared import StatusEnum, UpdateBookingAction


class CreateBooking(BaseModel):
    user_id: UUID = Field(...)
    service_id: UUID = Field(...)
    start_time: Optional[datetime] = Field(default_factory= lambda: datetime.now(tz= timezone.utc))
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
        return self
    
class CreateBookingResponseModel(BaseModel):
    user_id: UUID = Field(...)
    service_id: UUID = Field(...)
    start_time: datetime
    end_time: datetime = Field(...)
    status: StatusEnum = Field(...)
    message: Optional[str] = None
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class GetBookingResponseModel(BaseModel):
    message: Optional[str] = None
    id: UUID
    user_id : UUID
    service_id : UUID
    start_time: datetime
    end_time: datetime
    status: StatusEnum
    created_at: datetime

class UpdateBooking(BaseModel):
    action: Optional[UpdateBookingAction] = Field(None, description="(user only) You can only reschedule or cancel if your booking is pending or confirmed")
    start_time: Optional[datetime] = Field(None, description="(user only) If you intend to reschedule, set the new start_time otherwise leave blank")
    end_time: Optional[datetime] = Field(None, description="(user only) If you intend to reschedule, set the new end_time otherwise leave blank")
    status: Optional[StatusEnum] = Field(None, description="(admin only) Input the new status")

    @field_validator("start_time")
    @classmethod
    def check_update_start_time(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return v
        now = datetime.now(tz=timezone.utc)
        if v < now:
            raise ValueError("start_time must not be in the past")
        return v

    @field_validator("end_time")
    @classmethod
    def check_end_time(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return v
        now = datetime.now(tz=timezone.utc)
        if v < now:
            raise ValueError("end_time must not be in the past")
        return v

    @model_validator(mode="after")
    def check_times(self):
        if self.start_time is None or self.end_time is None:
            return self
        if self.start_time > self.end_time:
            raise ValueError("end_time must be after start_time")
        return self