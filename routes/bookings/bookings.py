from fastapi import APIRouter, status, Query
from datetime import datetime
from utils.manager import db_dependency, token_dependency
from src.bookings.bookings import create_booking, get_bookings, get_bookings_by_id, update_booking, delete_booking
from schemas.bookings.bookings import CreateBooking, CreateBookingResponseModel, GetBookingResponseModel, UpdateBooking
from shared import RoleEnum

bookings_router = APIRouter(prefix="/bookings", tags= ["bookings"])

@bookings_router.post("", status_code= status.HTTP_201_CREATED, response_model= CreateBookingResponseModel)
async def create_booking_router(db: db_dependency, token: token_dependency, details: CreateBooking):
    result = await create_booking(db= db, token= token, details= details)
    await db.commit()
    return result

@bookings_router.get("/{id}", status_code= status.HTTP_200_OK, response_model=GetBookingResponseModel)
async def get_bookings_by_id_router(db: db_dependency, token: token_dependency, id: str):
    return await get_bookings_by_id(db= db, token= token, id= id)

@bookings_router.get("", status_code= status.HTTP_200_OK, response_model=GetBookingResponseModel)
async def get_bookings_router(db: db_dependency,
                              token: token_dependency,
                              bookings_status: RoleEnum = Query(None),
                              bookings_from: datetime = Query(None),
                              bookings_to: datetime = Query(None)):
    return await get_bookings(db= db, token= token, bookings_status= bookings_status, bookings_from= bookings_from, bookings_to= bookings_to)

@bookings_router.patch("/{id}", status_code= status.HTTP_200_OK)
async def update_booking_router(db: db_dependency, token: token_dependency, id: str, preferences: UpdateBooking):
    result = await update_booking(db= db, token= token, id= id, preferences= preferences)
    await db.commit()
    return result

@bookings_router.delete("{id}")
async def delete_booking_router(db: db_dependency, token: token_dependency, id: str):
    result = await delete_booking(db = db, token= token, id= id)
    await db.commit()
    return result