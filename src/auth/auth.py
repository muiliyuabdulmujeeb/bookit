from fastapi import HTTPException, status, Depends
from sqlalchemy import select, update, delete
from database.config import db_dependency
from schemas.auth.auth import SignIn, SignUp, UpdateAccount
from database.models import Users, Blacklists
from utils.manager import pwd_context, jwt_manager


async def create_account(user_details: SignUp, db: db_dependency)-> dict:
    full_name = user_details.full_name
    email = user_details.email
    password_hash = pwd_context.hash(user_details.password)
    role = user_details.role

    #check if user already exist
    try:
        stmt = select(Users).where(Users.email == email)
        result_obj = await db.execute(stmt)
        user = result_obj.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"0{e}")

    if user:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="user already exist, sign in")

    to_add = Users(full_name= full_name, email= email, password_hash= password_hash, role= role)

    try:
        db.add(to_add)
        await db.flush()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"1{e}")
    
    try:
        stmt = select(Users.id).where(Users.email == email)
        result_obj = await db.execute(stmt)
        user_id = result_obj.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"2{e}")
    to_encode= {"sub": str(user_id), "role": role.value}
    access_token = await jwt_manager.create_access_token(to_encode)
    refresh_token = await jwt_manager.create_refresh_token(to_encode)

    to_return = {
        "message": "user account created",
        "access_token": access_token,
        "refresh_token": refresh_token
    }

    return to_return


async def get_account_details(db: db_dependency, token: str = Depends(jwt_manager.validate_token))-> dict:
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

async def update_account(db: db_dependency, user_details: UpdateAccount, token: str = Depends(jwt_manager.validate_token))-> dict:
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


async def delete_account(db: db_dependency, token: str= Depends(jwt_manager.validate_token))-> dict:
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
    to_add = Blacklists(token= token)
    try:
        db.add(to_add)
        await db.flush()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB Error: {e}")
    
    return {"message": "account deleted"}


async def sign_in(db: db_dependency, details: SignIn) -> dict:
    #collect data
    user_email= details.email
    user_password= details.password
    
    #check if email exists
    try:
        stmt = select(Users).where(Users.email == user_email)
        result_obj = await db.execute(stmt)
        user = result_obj.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db error: {e}")

    if not user:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="email or password incorrect")
    
    #verify password
    pass_verify = pwd_context.verify(user_password, user.password_hash)

    if not pass_verify:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="email or password incorrect")
    
    #create token
    user_details = {"sub": str(user.id), "role": user.role}
    access_token = await jwt_manager.create_access_token(user_details)
    refresh_token = await jwt_manager.create_refresh_token(user_details)

    to_return = {
        "message": "login successful",
        "access_token": access_token,
        "refesh_token": refresh_token
    }

    return to_return

async def sign_out(db: db_dependency,refresh_token:str, access_token: str= Depends(jwt_manager.validate_token))-> bool:
    #blacklist token by adding it to the blacklisted tokens in postgres to simulate redis blacklisting
    access_to_add = Blacklists(token= access_token)
    refresh_to_add = Blacklists(token= refresh_token)
    try:
        db.add(access_to_add)
        db.add(refresh_to_add)
        await db.flush()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB Error: {e}")
    
    return True