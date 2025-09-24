import os
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from jose import jwt, JWTError, ExpiredSignatureError
from jose.exceptions import JWTClaimsError, JWTError
from typing import Annotated, Optional, Union
from database.config import db_dependency, redis_dependency

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer("/auth/login")
token_dependency = Annotated[str, Depends(oauth2_scheme)]

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
REFRESH_TOKEN_EXPIRE_MINUTES = os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES")

class jwt_manager():

    def __init__(self, db: db_dependency, redis: redis_dependency) -> None:
        self.db = db
        self.redis = redis

    
    async def create_access_token(user_details: dict) -> str: #sub and role as key value pairs in the dict
        
        iat= datetime.now(tz=timezone.utc)
        exp = iat + timedelta(minutes= ACCESS_TOKEN_EXPIRE_MINUTES)
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

    async def validate_token(token: str) -> str:


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
    
    async def check_role(token: str, required_role: str)-> Optional[None]:

        token = await jwt_manager.validate_token(token)
        
        data = jwt.decode(token, key= SECRET_KEY, algorithms= [ALGORITHM])

        user_role = data.get("role")

        match user_role:
            case "user": return "user"
            case "admin": return "admin"
            case _: return None