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
from database.config import db_dependency
from database.models import Blacklists
from shared import RoleEnum
from utils.logger import get_logger

load_dotenv()

logger = get_logger("security")

pwd_context = CryptContext(schemes=["argon2"], deprecated= "auto")
oauth2_scheme = OAuth2PasswordBearer("/auth/login")
token_dependency = Annotated[str, Depends(oauth2_scheme)]

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES"))

class JwtManager():

    def __init__(self) -> None:
        pass

    
    async def create_access_token(self, user_details: dict) -> str: #sub and role as key value pairs in the dict
        logger.info("create access token")
        iat= datetime.now(tz=timezone.utc)
        exp = iat + timedelta(minutes= ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = user_details.copy()
        to_encode.update({"iat": int(iat.timestamp()), "exp": int(exp.timestamp()), "type": "access"})

        try:
            token = jwt.encode(to_encode, key= SECRET_KEY, algorithm= ALGORITHM)
        except JWTError as e:
            logger.error(f"jwt Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
        except Exception as e:
            logger.error(f"jwt Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
        logger.info("access token created")
        return token
    
    async def decode_token(self, token: str)-> Union[str, dict]:
        logger.info("decode token")
        try:
             data = jwt.decode(token, key= SECRET_KEY, algorithms= [ALGORITHM])
        except JWTClaimsError as e:
            logger.error("invalid claims in token")
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="invalid claims in token")
        
        except ExpiredSignatureError as e:
            logger.error("token expired")
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="token expired")
        
        except JWTError as e:
            logger.error(f"jwt Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="invalid token")
        logger.info("token decoded")
        return data
    
    async def create_refresh_token(self, user_details: dict) -> str: #sub and role as key value pairs in the dict
        logger.info("create refresh token")
        iat= datetime.now(tz=timezone.utc)
        exp = iat + timedelta(minutes= REFRESH_TOKEN_EXPIRE_MINUTES)
        to_encode = user_details.copy()
        to_encode.update({"iat": iat, "exp": exp,"type": "refresh"})

        try:
            token = jwt.encode(to_encode, key= SECRET_KEY, algorithm= ALGORITHM)
        except JWTError as e:
            logger.error(f"jwt Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
        except Exception as e:
            logger.error(f"jwt Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
        logger.info("refresh token created")
        return token

    async def validate_token(self, db: db_dependency, token: str) -> str:
        logger.info("validate token")
        #check if user token is already blacklisted, hence logged out
        try:
            stmt = select(Blacklists.token).where(Blacklists.token == token)
            result_obj = await db.execute(stmt)
            user = result_obj.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Db Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")

        if user:
            logger.error("session expired, user previously logged out")
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="session expired, sign in again")

        try:
            decoded = jwt.decode(token, key= SECRET_KEY, algorithms= [ALGORITHM])
        except JWTClaimsError as e:
            logger.error("invalid claims in token")
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="invalid claims in token")
        
        except ExpiredSignatureError as e:
            logger.error("token expired")
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="token expired")
        
        except JWTError as e:
            logger.error(f"jwt Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="invalid token")
        token_type = decoded.get("type")
        if token_type != "access":
            logger.error("invalid token type")
            raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="invalid token type")
        logger.info("token validated")
        return token
    
    async def validate_refresh_token(self, db: db_dependency, token: str) -> str:
        logger.info("validate refresh token")
        #check if user token is already blacklisted, hence logged out
        try:
            stmt = select(Blacklists.token).where(Blacklists.token == token)
            result_obj = await db.execute(stmt)
            user = result_obj.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Db Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")

        if user:
            logger.error("session expired, user previously logged out")
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="session expired, sign in again")

        try:
            decoded = jwt.decode(token, key= SECRET_KEY, algorithms= [ALGORITHM])
        except JWTClaimsError as e:
            logger.error("invalid claims in token")
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="invalid claims in token")
        
        except ExpiredSignatureError as e:
            logger.error("token expired")
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="token expired")
        
        except JWTError as e:
            logger.error(f"jwt Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="invalid token")
        token_type = decoded.get("type")
        if token_type != "refresh":
            logger.error("invalid token type")
            raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="invalid token type")
        logger.info("refresh token validated")
        return token
    
    async def generate_new_access_token(self, db: db_dependency, refresh_token: str)-> str:
        logger.info("generate new access token")
        #validate token
        validated_token = await self.validate_refresh_token(db= db,token= refresh_token)
        #decode token to get user data
        data = await self.decode_token(validated_token)
        #encode user data
        token = await self.create_access_token(data)
        logger.info("new access token generated")
        return token
    
    async def check_role(self, db: db_dependency, token: str)-> Optional[str]:
        logger.info("check user role")

        token = await self.validate_token(db, token)
        
        data = jwt.decode(token, key= SECRET_KEY, algorithms= [ALGORITHM])
        user_role = data.get("role")

        match user_role:
            case RoleEnum.USER.value:
                logger.info("user role returned")
                return RoleEnum.USER.value
            case RoleEnum.ADMIN.value:
                logger.info("user role returned")
                return RoleEnum.ADMIN.value

jwt_manager = JwtManager()

async def check_if_user(db: db_dependency, token: token_dependency)-> bool:
    logger.info("check if user")
    assigned_role = await jwt_manager.check_role(db, token)
    if assigned_role != RoleEnum.USER.value:
        logger.error("user not authorized")
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail="you are not allowed to access this service")
    logger.info("user authorized")
    return True

async def check_if_admin(db: db_dependency, token: token_dependency)-> bool:
    logger.info("check if admin")
    assigned_role = await jwt_manager.check_role(db, token)
    if assigned_role != RoleEnum.ADMIN.value:
        logger.error("user not authorized")
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail="you are not allowed to access this service")
    logger.info("user authorized")
    return True

if_user_dependency = Annotated[bool, Depends(check_if_user)]
if_admin_dependency = Annotated[bool, Depends(check_if_admin)]