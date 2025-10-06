from fastapi import status, HTTPException, Query
from decimal import Decimal
from typing import Union, Optional
from uuid import UUID
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm.exc import MultipleResultsFound
from database.config import db_dependency
from database.models import Services
from utils.manager import jwt_manager, token_dependency, check_if_admin
from schemas.services.services import CreateService, UpdateService
from shared import IsActiveEnum
from utils.logger import get_logger

logger = get_logger("service")


async def create_service(db: db_dependency, token: str, details: CreateService):
    logger.info("create service")
    #validate token
    await jwt_manager.validate_token(db= db,token= token)
    await check_if_admin(db, token)
    to_add = Services(**details.model_dump())
    try:
        db.add(to_add)
        await db.flush()
    except Exception as e:
        await db.rollback()
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    #get the service detail from db
    try:
        stmt = select(Services).where((Services.title == details.title) & (Services.description == details.description) & (Services.price == details.price))
        result_cls = await db.execute(stmt)
        result_obj = result_cls.scalar_one_or_none()
    except MultipleResultsFound as m:
        logger.error(f"Idempotency Error: {m.__class__.__name__}: {m}")
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="idempotency error")
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    logger.info("service created")
    return {
        "message": "service created",
        "id": result_obj.id,
        "title": result_obj.title,
        "description": result_obj.description,
        "price": result_obj.price,
        "duration_mins": result_obj.duration_mins,
        "is_active": result_obj.is_active,
        "created_at": result_obj.created_at
    }

async def get_service_by_id(db: db_dependency, token: token_dependency, id: Union[UUID, str]):
    logger.info("get service by id")
    #validate token
    await jwt_manager.validate_token(db=db, token= str(token))
    #search service db using id
    try:
        stmt= select(Services).where(Services.id == id)
        result_cls = await db.execute(stmt)
        result_obj = result_cls.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    if not result_obj:
        logger.error("service not found")
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail="service not found")
    logger.info("get service by id request successful")
    return {
        "id": result_obj.id,
        "title": result_obj.title,
        "description": result_obj.description,
        "price": result_obj.price,
        "duration_mins": result_obj.duration_mins,
        "is_active": result_obj.is_active,
        "created_at": result_obj.created_at
    }

async def get_services_by_query(db: db_dependency,
                                token: token_dependency,
                                q: Optional[str] = Query(None),
                                price_min: Optional[Decimal] = Query(None),
                                price_max: Optional[Decimal] = Query(None),
                                active: Optional[IsActiveEnum] = Query(None)):
    
    logger.info("get service by query")
    #validate_token
    await jwt_manager.validate_token(db,token)

    try:
        stmt = select(Services)
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    filters = []

    if q is not None:
        filters.append(Services.title.ilike(f"%{q}%"))
    if price_min is not None:
        filters.append(Services.price >= price_min)
    if price_max is not None:
        filters.append(Services.price <= price_max)
    if active is not None:
        filters.append(Services.is_active == active)
    
    if filters:
        stmt = stmt.where(and_(*filters))
    
    try:
        result_cls = await db.execute(stmt)
        result = result_cls.scalars().all()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    logger.info("get service by query request successful")
    
    return result


async def update_service(db: db_dependency, token: str, id: str, details: UpdateService):
    logger.info("update service")
    #validate token
    await jwt_manager.validate_token(db, token)
    await check_if_admin(db, token)
    values = {}

    if details.title is not None:
        values["title"] = details.title
    if details.description is not None:
        values["description"] = details.description
    if details.price is not None:
        values["price"] = details.price
    if details.duration_mins is not None:
        values["duration_mins"] = details.duration_mins
    
    if values:
        try:
            stmt = (update(Services).where(Services.id == id).values(**values).execution_options(synchronize_session="fetch"))
            await db.execute(stmt)
            await db.flush()
        except Exception as e:
            await db.rollback()
            logger.error(f"Db Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    try:
        select_stmt = select(Services).where(Services.id == id)
        result_cls = await db.execute(select_stmt)
        result_obj = result_cls.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    to_return = {
        "message": "update successful",
        "id": result_obj.id,
        "title": result_obj.title,
        "description": result_obj.description,
        "price": result_obj.price,
        "duration_mins": result_obj.duration_mins,
        "is_active": result_obj.is_active,
        "created_at": result_obj.created_at
    }
    logger.info("service updated")
    return to_return

async def delete_service(db: db_dependency, token: str, id: str):
    logger.info("delete service")
    #validate token
    await jwt_manager.validate_token(db, token)
    await check_if_admin(db, token)
    #delete service using id
    try:
        stmt= delete(Services).where(Services.id == id)
        await db.execute(stmt)
        await db.flush()
    except Exception as e:
        await db.rollback()
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    logger.info("service deleted")
    return{"message": "service deleted"}