from pydantic import BaseModel, Field, EmailStr
from typing import  Optional
from shared import RoleEnum



class SignUp(BaseModel):

    full_name: str = Field(min_length=5, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)
    role: RoleEnum

class SignUpResponseModel(BaseModel):
    message: str
    access_token: Optional[str]
    refresh_token: Optional[str]




class GetAccountResponse(BaseModel):
    full_name: str
    email: EmailStr
    role: RoleEnum

class UpdateAccount(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[RoleEnum] = None
    password: Optional[str] = None

class UpdateAccountResponse(GetAccountResponse):
    pass


class SignIn(BaseModel):

    email: EmailStr
    password: str = Field(min_length=8)

class SignInResponseModel(BaseModel):
    message: str
    access_token: Optional[str]
    refresh_token: Optional[str]

class RefreshToken(BaseModel):
    refresh_token: str