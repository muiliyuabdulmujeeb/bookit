import os
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from passlib.context import CryptContext
from dotenv import load_dotenv
from jose import jwt, JWTError, ExpiredSignatureError
from jose.exceptions import JWTClaimsError, JWTError
from typing import Annotated, Optional, Union
from database.config import db_dependency, redis_dependency
from database.models import Blacklists
from shared import RoleEnum

load_dotenv()

pwd_context = CryptContext(schemes=["argon2"], deprecated= "auto")
oauth2_scheme = OAuth2PasswordBearer("/auth/login")
token_dependency = Annotated[str, Depends(oauth2_scheme)]

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES"))

class jwt_manager():

    def __init__(self, db: db_dependency, redis: redis_dependency) -> None:
        self.db = db
        self.redis = redis

    
    async def create_access_token(user_details: dict) -> str: #sub and role as key value pairs in the dict
        
        iat= datetime.now(tz=timezone.utc)
        exp = iat + timedelta(minutes= ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = user_details.copy()
        to_encode.update({"iat": int(iat.timestamp()), "exp": int(exp.timestamp())})

        print(to_encode)

        try:
            token = jwt.encode(to_encode, key= SECRET_KEY, algorithm= ALGORITHM)
        except JWTError as e:
            #logger
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e)
        except Exception as e:
            #logger
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e)
        
        return token
    
    async def decode_token(token: str)-> Union[str, dict]:
        try:
             data = jwt.decode(token, key= SECRET_KEY, algorithms= [ALGORITHM])
        except JWTClaimsError as e:
            #logger
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="invalid claims in token")
        
        except JWTError as e:
            #logger
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="invalid token")

        return data
    
    async def create_refresh_token(user_details: dict) -> str: #sub and role as key value pairs in the dict
        
        iat= datetime.now(tz=timezone.utc)
        exp = iat + timedelta(minutes= REFRESH_TOKEN_EXPIRE_MINUTES)
        to_encode = user_details.copy()
        to_encode.update({"iat": iat, "exp": exp})

        try:
            token = jwt.encode(to_encode, key= SECRET_KEY, algorithm= ALGORITHM)
        except JWTError as e:
            #logger
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
        except Exception as e:
            #logger
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
        
        return token

    async def validate_token(self, token: str) -> str:
        #check if user token is already blacklisted, hence logged out
        try:
            stmt = select(Blacklists.token).where(Blacklists.token == token)
            result_obj = await self.db.execute(stmt)
            user = result_obj.scalar_one_or_none()
        except Exception as e:
            #logger
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")

        if user:
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="session expired, sign in again")

        try:
            jwt.decode(token, key= SECRET_KEY, algorithms= [ALGORITHM])
        except JWTClaimsError as e:
            #logger
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="invalid claims in token")
        
        except ExpiredSignatureError as e:
            #logger
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="token expired")
        
        except JWTError as e:
            #logger
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="invalid token")
        
        return token
    
    async def generate_new_access_token(self, refresh_token: str)-> str:
        #validate token
        validated_token = await self.validate_token(token= refresh_token)
        #decode token to get user data
        data = await jwt_manager.decode_token(validated_token)
        #encode user data
        token = await jwt_manager.create_access_token(data)
        return token
    
    async def check_role(self, token: str)-> Optional[str]:

        token = await self.validate_token(token)
        
        data = jwt.decode(token, key= SECRET_KEY, algorithms= [ALGORITHM])

        user_role = data.get("role")

        match user_role:
            case RoleEnum.USER: return RoleEnum.USER.value
            case RoleEnum.ADMIN: return RoleEnum.ADMIN.value
            case _: return None



async def check_if_user(token: token_dependency)-> bool:
    assigned_role = await jwt_manager.check_role(token)
    if assigned_role != RoleEnum.USER:
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail="you are not allowed to access this service")
    return True

async def check_if_admin(token: token_dependency)-> bool:
    assigned_role = await jwt_manager.check_role(token)
    if assigned_role != RoleEnum.ADMIN:
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail="you are not allowed to access this service")
    return True

if_user_dependency = Annotated[bool, Depends(check_if_user)]
if_admin_dependency = Annotated[bool, Depends(check_if_admin)]