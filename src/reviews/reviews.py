from fastapi import HTTPException, status
from sqlalchemy import select, update, delete
from schemas.reviews.reviews import CreateReview, CreateReviewResponseModel, UpdateReview, UpdateReviewResponseModel
from database.config import db_dependency
from utils.manager import jwt_manager, if_user_dependency
from database.models import Bookings, Reviews
from shared import StatusEnum, RoleEnum
from utils.logger import get_logger

logger = get_logger("review")
async def create_review(db: db_dependency, token: if_user_dependency, details: CreateReview) -> CreateReviewResponseModel:
    validated_token = await jwt_manager.validate_token(db, token)
    token_details: dict = await jwt_manager.decode_token(validated_token)
    token_user_id = token_details.get("sub")
    if not token_user_id:
        logger.info("invalid user")
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "invalid user")
    
    user_booking_id = details.booking_id
    #check the booking table if there is a booking that exists for the user
    try:
        stmt1 = select(Bookings).where((Bookings.id == user_booking_id) & (Bookings.user_id== token_user_id))
        result1_obj = await db.execute(stmt1)
        result1 = result1_obj.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    #make sure the booking creator is the one giving the comment
    if str(result1.user_id) != token_user_id:
        logger.error("user not authenticated")
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail="you are not allowed to acccess this resource")
    #handle booking not found
    if not result1:
        logger.error("booking not found")
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail="Booking not found")
    
    if result1.status is not StatusEnum.COMPLETED:
        logger.error("booking status not completed")
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "booking must be completed before you can make a review")
    #check if the booking already has a review
    try:
        stmt2 = select(Reviews).where(Reviews.booking_id == user_booking_id)
        result2_obj = await db.execute(stmt2)
        result2 = result2_obj.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    if result2:
        logger.error("booking review already existed")
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="booking review already exist")
    
    #add review to database
    to_add = Reviews(booking_id = user_booking_id, rating= details.rating, comment= details.comment)
    try:
        db.add(to_add)
        await db.flush()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    #get review details from db to return to user
    try:
        stmt3 = select(Reviews).where(Reviews.booking_id == user_booking_id and Reviews.rating == details.rating and Reviews.comment == details.comment)
        result3_obj = await db.execute(stmt3)
        result3 = result3_obj.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    to_return = {
        "id": result3.id,
        "booking_id": result3.booking_id,
        "rating": result3.rating,
        "comment": result3.comment,
        "created_at": result3.created_at
    }
    logger.info("review created")
    return to_return

async def get_reviews_for_service(db: db_dependency, token: str, id: str):
    logger.info("get review for service")
    await jwt_manager.validate_token(db, token)

    try:
        stmt1 = select(Reviews).join(Bookings, Reviews.booking_id == Bookings.id).where(Bookings.service_id == id)
        stmt1_result_cls = await db.execute(stmt1)
        stmt1_result_obj = stmt1_result_cls.scalars().all()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    if not stmt1_result_obj:
        logger.error("review not found")
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail="review not found")
    logger.error("get review for service request completed")
    return stmt1_result_obj

async def update_review(db: db_dependency, token: str, id: str, details: UpdateReview) -> UpdateReviewResponseModel:
    logger.info("update review")
    validated_token = await jwt_manager.validate_token(db, token)
    token_details: dict = await jwt_manager.decode_token(validated_token)
    token_user_id = token_details.get("sub")
    if not token_user_id:
        logger.error("invalid user")
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "invalid user")
    try:
        stmt1 = select(Reviews, Bookings.user_id).join(Bookings, Reviews.booking_id == Bookings.id).where(Reviews.id == id)
        stmt1_result_cls = await db.execute(stmt1)
        stmt1_result_obj = stmt1_result_cls.one_or_none()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    if stmt1_result_obj:
        review = stmt1_result_obj[0]
        user_id = stmt1_result_obj[1]

    if str(user_id) != token_user_id:
        logger.error("user not authorized")
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail="you're not allowed to edit this review")
    
    new_rating = details.rating
    new_comment = details.comment if details.comment else review.comment

    try:
        stmt2= (update(Reviews).where(Reviews.id == id).values(rating= new_rating, comment= new_comment))
        await db.execute(stmt2)
        await db.flush()
    except Exception as e:
        await db.rollback()
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    try:
        stmt3 = select(Reviews).where(Reviews.id == id)
        stmt3_result_obj = await db.execute(stmt3)
        stmt3_result = stmt3_result_obj.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")

    to_return = {
        "id": stmt3_result.id,
        "booking_id": str(stmt3_result.booking_id),
        "rating": stmt3_result.rating,
        "comment": stmt3_result.comment,
        "created_at": stmt3_result.created_at
    }
    logger.error("review updated")
    return to_return

async def delete_review(db:db_dependency, token: str, id: str):
    logger.info("delete review")
    validated_token = await jwt_manager.validate_token(db, token)
    role = await jwt_manager.check_role(db, validated_token)

    if role not in (RoleEnum.ADMIN.value, RoleEnum.USER.value):
        logger.error("user not authenticated")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you're not allowed to perform this action")
    
    try:
        stmt = delete(Reviews).where(Reviews.id == id)
        await db.execute(stmt)
        await db.flush()
    except Exception as e:
        await db.rollback()
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    logger.info("review deleted")
    return {"message": "Review deleted"}