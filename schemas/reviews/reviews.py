from pydantic import BaseModel, field_validator, Field
from typing import Optional
from uuid import UUID
from datetime import datetime



class CreateReview(BaseModel):
    booking_id: str = Field(...)
    rating: int = Field(...)
    comment: Optional[str]

    @field_validator("rating")
    @classmethod
    def check_rating(cls, v: int)-> int:
        if v < 1:
            raise ValueError("rating cannot be less than 1")
        if v > 5:
            raise ValueError("rating cannot be greater than 5")
        return v
    
class CreateReviewResponseModel(CreateReview):
    id: UUID
    created_at: datetime

class UpdateReview(BaseModel):
    rating: int = Field(...)
    comment: Optional[str]

    @field_validator("rating")
    @classmethod
    def check_rating(cls, v: int)-> int:
        if v < 1:
            raise ValueError("rating cannot be less than 1")
        if v > 5:
            raise ValueError("rating cannot be greater than 5")
        return v
    
class UpdateReviewResponseModel(CreateReviewResponseModel):
    pass

class GetReviewResponseModel(CreateReviewResponseModel):
    class Config:
        from_attributes = True