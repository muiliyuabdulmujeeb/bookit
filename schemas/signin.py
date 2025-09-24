from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class SignIn(BaseModel):

    email: EmailStr
    password: str = Field(min_length=8)

class SignInResponseModel(BaseModel):
    message: str
    Authentication: Optional[None]