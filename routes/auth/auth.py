from fastapi import APIRouter, status
from database.config import db_dependency
from schemas.auth.auth import SignUp, SignUpResponseModel, GetAccountResponse, UpdateAccount, UpdateAccountResponse, SignIn, SignInResponseModel, RefreshToken
from src.auth.auth import create_account, get_account_details, update_account, delete_account, sign_in, sign_out, refresh_access
from utils.manager import token_dependency, jwt_manager

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register", status_code= status.HTTP_201_CREATED, response_model= SignUpResponseModel)
async def sign_up(db: db_dependency, user_details: SignUp):
    result = await create_account(db= db, user_details= user_details)
    await db.commit()
    return result

@auth_router.get("/me",response_model= GetAccountResponse)
async def my_account(db: db_dependency, token: token_dependency):
    return await get_account_details(db= db, token= token)

@auth_router.patch("/me", response_model= UpdateAccountResponse)
async def update_account_route(db: db_dependency, token: token_dependency, user_details: UpdateAccount):
    result = await update_account(db=db, token=token, user_details=user_details)
    await db.commit()
    return result

@auth_router.post("/me/delete")
async def delete_account_route(db: db_dependency, token: token_dependency):
    result = await delete_account(db= db, token= token)
    await db.commit()
    return result

@auth_router.post("/login", response_model= SignInResponseModel)
async def sign_in_route(db: db_dependency, user_details: SignIn):
    return await sign_in(db=db, details= user_details)

@auth_router.post("/logout")
async def sign_out_route(db: db_dependency, token: token_dependency, refresh: RefreshToken):
    result = await sign_out(db= db, access_token= token, refresh_token=refresh)
    await db.commit()
    return result

@auth_router.post("/refresh")
async def refresh_access_route(db: db_dependency, token: RefreshToken):
    return await refresh_access(db= db, token= token)


