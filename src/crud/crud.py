from fastapi import HTTPException, status
from typing import Union
from passlib.context import CryptContext
from sqlalchemy import select, update, delete
from database.config import db_dependency, redis_dependency
from utils.manager import jwt_manager, token_dependency
from schemas.signup import SignUp
from schemas.crud import UpdateAccount
from database.models import Users

pwd_context = CryptContext(schemes=["bcrypt"], deprecated= "auto")

async def create_account(user_details: SignUp, db: db_dependency):
    full_name = user_details.full_name
    email = user_details.email
    password_hash = pwd_context.hash(user_details.password)
    role = user_details.role

    to_add = Users(full_name= full_name, email= email, password_hash= password_hash, role= role)

    try:
        await db.add(to_add)
        await db.flush()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    try:
        stmt = select(Users.id).where(Users.email == email)
        result_obj = await db.execute(stmt)
        user_id = result_obj.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    to_encode= {"sub": str(user_id), "role": role}
    access_token = await jwt_manager.create_access_token(to_encode)
    refresh_token = await jwt_manager.create_refresh_token(to_encode)

    to_return = {
        "message": "user account created",
        "access_token": access_token,
        "refresh_token": refresh_token
    }

    return to_return


async def get_account_details(db: db_dependency, token: token_dependency):
    data = await jwt_manager.decode_token(token)
    user_id = data.get("sub")
    try:
        stmt = select(Users).where(Users.id == user_id)
        result_obj = await db.execute(stmt)
        user_obj = result_obj.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")

    user = {
        "full_name": user_obj.full_name,
        "email": user_obj.email,
        "role": user_obj.role
    }

    return user

async def update_account(db: db_dependency, token: token_dependency, user_details: UpdateAccount):
    data = await jwt_manager.decode_token(token)
    user_id = data.get("sub")
    try:
        stmt = select(Users).where(Users.id == user_id)
        result_obj = await db.execute(stmt)
        user_obj = result_obj.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    existing_full_name = user_obj.full_name
    existing_email = user_obj.email
    existing_role = user_obj.role
    existing_password_hash = user_obj.password_hash

    new_full_name = user_details.full_name if user_details.full_name else existing_full_name
    new_email = user_details.email if user_details.email else existing_email
    new_role = user_details.role if user_details.role else existing_role
    new_password_hash = pwd_context.hash(user_details.password) if user_details.password else existing_password_hash

    try:
        stmt = update(Users).where(Users.id == user_id).values(full_name = new_full_name,
                                                               email= new_email,
                                                               password_hash= new_password_hash,
                                                               role= new_role
                                                                    )
        await db.execute(stmt)
        await db.flush()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    to_return = {
        "full_name": new_full_name,
        "email": new_email,
        "role": new_role
    }

    return to_return


async def delete_account(db: db_dependency, token: token_dependency):
    data = await jwt_manager.decode_token(token)
    user_id = data.get("sub")
    try:
        stmt = delete(Users).where(Users.id == user_id)
        await db.execute(stmt)
        await db.flush()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    #blacklist token in redis
    
    return {"message": "account deleted"}