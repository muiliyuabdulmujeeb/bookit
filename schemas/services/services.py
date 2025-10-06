from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from uuid import UUID
from shared import IsActiveEnum
from datetime import datetime


class CreateService(BaseModel):
    title: str = Field(..., min_length=2, max_length=50)
    description: str = Field(..., min_length=2, max_length=250)
    price : Decimal = Field(..., max_digits=10, decimal_places=2)
    duration_mins: int

class CreateServiceResponseModel(CreateService):
    message: Optional[str] = None
    id: UUID
    is_active: IsActiveEnum
    created_at: datetime

class UpdateService(BaseModel):
    title: Optional[str] = Field(..., min_length=2, max_length=50)
    description: Optional[str] = Field(..., min_length=2, max_length=250)
    price : Optional[Decimal] = Field(..., max_digits=10, decimal_places=2)
    duration_mins: Optional[int] = None

class UpdateServiceResponseModel(CreateServiceResponseModel):
    class Config:
        from_attributes = True

class GetServiceResponseModel(CreateServiceResponseModel):
    class Config:
        from_attributes = True