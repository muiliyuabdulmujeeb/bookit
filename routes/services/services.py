from fastapi import APIRouter, status, Query
from typing import Optional, Union, List
from decimal import Decimal
from uuid import UUID
from utils.manager import db_dependency, token_dependency
from src.services.services import create_service, get_service_by_id, get_services_by_query, update_service, delete_service
from schemas.services.services import CreateService,UpdateService, CreateServiceResponseModel, UpdateServiceResponseModel, GetServiceResponseModel
from src.reviews.reviews import get_reviews_for_service
from shared import IsActiveEnum

service_router = APIRouter(prefix="/services", tags= ["services"])



@service_router.post("", status_code= status.HTTP_201_CREATED, response_model= CreateServiceResponseModel)
async def create_service_router(db: db_dependency, token: token_dependency, details: CreateService):
    result = await create_service(db= db, token= token, details= details)
    await db.commit()
    return result

@service_router.get("/{id}/reviews", status_code= status.HTTP_200_OK)
async def get_reviews_for_service_router(db: db_dependency, token: token_dependency, id: str):
    result = await get_reviews_for_service(db= db, token= token, id= id)
    await db.commit()
    return result

@service_router.get("/{id}", status_code= status.HTTP_200_OK, response_model= GetServiceResponseModel)
async def get_service_by_id_router(db: db_dependency, token: token_dependency, id: Union[UUID, str]):
    return await get_service_by_id(db= db, token= token, id = id)

@service_router.get("", status_code= status.HTTP_200_OK, response_model= List[GetServiceResponseModel])
async def get_services_by_query_router(
                                db: db_dependency, token: token_dependency,
                                q: Optional[str] = Query(None),
                                price_min: Optional[Decimal] = Query(None),
                                price_max: Optional[Decimal] = Query(None),
                                active: Optional[IsActiveEnum] = Query(None)):
    return await get_services_by_query(db = db, token = token, q = q, price_min= price_min, price_max= price_max, active= active)

@service_router.patch("/{id}", status_code= status.HTTP_200_OK, response_model= UpdateServiceResponseModel)
async def update_service_router(db: db_dependency, token: token_dependency, id: str, details: UpdateService):
    result = await update_service(db= db, token= token, id= id, details= details)
    await db.commit()
    return result

@service_router.delete("/{id}")
async def delete_service_router(db: db_dependency, token: token_dependency, id: str):
    result = await delete_service(db= db, token= token, id= id)
    await db.commit()
    return result