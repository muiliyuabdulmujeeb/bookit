from fastapi import HTTPException, status
from sqlalchemy import select, update, delete
from schemas.reviews.reviews import CreateReview, CreateReviewResponseModel, GetReviewResponseModel, UpdateReview, UpdateReviewResponseModel
from database.config import db_dependency
from utils.manager import jwt_manager, if_user_dependency
from database.models import Bookings, Reviews
from shared import StatusEnum, RoleEnum


async def create_review(db: db_dependency, token: if_user_dependency, details: CreateReview) -> CreateReviewResponseModel:
    validated_token = await jwt_manager.validate_token(token)
    token_details: dict = await jwt_manager.decode_token(validated_token)
    token_user_id = token_details.get("sub")
    if not token_user_id:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "invalid user")
    
    user_booking_id = details.booking_id
    #check the booking table if there is a booking that exists for the user
    try:
        stmt1 = select(Bookings).where(Bookings.id == user_booking_id and Bookings.user_id== token_user_id)
        result1_obj = await db.execute(stmt1)
        result1 = result1_obj.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail= f"Db Error: {e}")
    
    #handle booking not found
    if not result1:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail="Booking not found")
    
    if result1.status is not StatusEnum.COMPLETED.value:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "booking must be completed before you can make a review")
    #check if the booking already has a review
    try:
        stmt2 = select(Reviews).where(Reviews.booking_id == user_booking_id)
        result2_obj = await db.execute(stmt2)
        result2 = result2_obj.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail= f"Db Error: {e}")
    if result2:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="booking review already exist")
    
    #add review to database
    to_add = Reviews(booking_id = user_booking_id, rating= details.rating, comment= details.comment)
    try:
        db.add(to_add)
        await db.flush()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail= f"Db Error: {e}")
    
    #get review details from db to return to user
    try:
        stmt3 = select(Reviews).where(Reviews.booking_id == user_booking_id and Reviews.rating == details.rating and Reviews.comment == details.comment)
        result3_obj = await db.execute(stmt3)
        result3 = result3_obj.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail= f"Db Error: {e}")
    
    to_return = {
        "id": result3.id,
        "booking_id": result3.booking_id,
        "rating": result3.rating,
        "comment": result3.comment,
        "created_at": result3.created_at
    }
    return to_return

async def get_reviews_for_service(db: db_dependency, token: str, id: str) -> list[GetReviewResponseModel]:
    await jwt_manager.validate_token(token)

    try:
        stmt1 = select(Reviews).join(Bookings, Reviews.booking_id == Bookings.id).where(Bookings.service_id == id)
        stmt1_result_cls = await db.execute(stmt1)
        stmt1_result_obj = stmt1_result_cls.scalars().all()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail= f"Db Error: {e}")
    
    if not stmt1_result_obj:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail="review not found")
    return stmt1_result_obj

async def update_review(db: db_dependency, token: str, id: str, details: UpdateReview) -> UpdateReviewResponseModel:
    validated_token = await jwt_manager.validate_token(token)
    token_details: dict = await jwt_manager.decode_token(validated_token)
    token_user_id = token_details.get("sub")
    if not token_user_id:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "invalid user")
    try:
        stmt1 = select(Reviews, Bookings.user_id).join(Bookings, Reviews.booking_id == Bookings.id).where(Reviews.id == id)
        stmt1_result_cls = await db.execute(stmt1)
        stmt1_result_obj = stmt1_result_cls.one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail= f"Db Error: {e}")
    
    if stmt1_result_obj:
        review = stmt1_result_obj[0]
        user_id = stmt1_result_obj[1]

    if user_id != token_user_id:
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail="you're not allowed to edit this review")
    
    new_rating = details.rating
    new_comment = details.comment if details.comment else review.comment

    try:
        stmt2= (update(Reviews).where(Reviews.id == id).values(rating= new_rating, comment= new_comment))
        await db.execute(stmt2)
        await db.flush()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail= f"Db Error: {e}")
    
    try:
        stmt3 = select(Reviews).where(Reviews.id == id)
        stmt3_result_obj = await db.execute(stmt3)
        stmt3_result = stmt3_result_obj.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail= f"Db Error: {e}")

    to_return = {
        "id": stmt3_result.id,
        "booking_id": stmt3_result.booking_id,
        "rating": stmt3_result.rating,
        "comment": stmt3_result.comment,
        "created_at": stmt3_result.created_at
    }
    return to_return

async def delete_review(db:db_dependency, token: str, id: str):
    validated_token = await jwt_manager.validate_token(token)
    role = await jwt_manager.check_role(validated_token)

    if role not in (RoleEnum.ADMIN.value, RoleEnum.USER.value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you're not allowed to perform this action")
    
    try:
        stmt = delete(Reviews).where(Reviews.id == id)
        await db.execute(stmt)
        await db.flush()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
    
    return {"message": "Review deleted"}