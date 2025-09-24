from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from database.models import RoleEnum


class SignUp(BaseModel):

    full_name: str = Field(min_length=5, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)
    role: RoleEnum

class SignUpResponseModel(BaseModel):
    message: str
    access_token: Optional[None]
    refresh_token: Optional[None]