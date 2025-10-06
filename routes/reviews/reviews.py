from fastapi import APIRouter, status
from utils.manager import db_dependency, token_dependency
from src.reviews.reviews import create_review, get_reviews_for_service, update_review, delete_review
from schemas.reviews.reviews import CreateReview, CreateReviewResponseModel, UpdateReview, UpdateReviewResponseModel

reviews_router = APIRouter(prefix="/reviews", tags= ["reviews"])


@reviews_router.post("", status_code= status.HTTP_201_CREATED, response_model= CreateReviewResponseModel)
async def create_review_router(db: db_dependency, token: token_dependency, details: CreateReview):
    result = await create_review(db= db, token= token, details= details)
    await db.commit()
    return result

@reviews_router.patch("/{id}", status_code= status.HTTP_200_OK, response_model= UpdateReviewResponseModel)
async def update_review_router(db: db_dependency, token: token_dependency, id: str, details: UpdateReview):
    result = await update_review(db= db, token= token, id= id, details= details)
    await db.commit()
    return result

@reviews_router.delete("/{id}", status_code= status.HTTP_200_OK)
async def delete_review_router(db: db_dependency, token: token_dependency, id: str):
    result = await delete_review(db= db, token= token, id= id)
    await db.commit()
    return result