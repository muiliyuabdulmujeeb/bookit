from pydantic import BaseModel, EmailStr
from typing import Union, Annotated, Optional
from database.models import RoleEnum




class GetAccountResponse(BaseModel):
    full_name: str
    email: EmailStr
    role: RoleEnum

class UpdateAccount(BaseModel):
    full_name: Union[str, None]
    email: Union[EmailStr, None]
    role: Union[RoleEnum, None]
    password: Union[str, None]

class UpdateAccountResponse(GetAccountResponse):
    pass