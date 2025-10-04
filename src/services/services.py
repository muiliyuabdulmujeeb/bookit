from fastapi import status, HTTPException, Query
from decimal import Decimal
from typing import Union, Optional
from uuid import UUID
from sqlalchemy import select, update, delete, and_
from database.config import db_dependency
from database.models import Services
from utils.manager import jwt_manager, token_dependency, if_admin_dependency
from schemas.services.services import CreateService, UpdateService


async def create_service(db: db_dependency, token: if_admin_dependency, details: CreateService):
    #validate token
    await jwt_manager.validate_token(token)
    to_add = Services(**details.model_dump())
    try:
        db.add(to_add)
        await db.flush()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB Error: {e}")
    
    #get the service detail from db
    try:
        stmt = select(Services).where(Services.title == details.title and Services.description == details.description and Services.price == details.price)
        result_cls = await db.execute(stmt)
        result_obj = result_cls.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB Error: {e}")
    
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
    #validate token
    await jwt_manager.validate_token(token= str(token))
    #search service db using id
    try:
        stmt= select(Services).where(Services.id == id)
        result_cls = await db.execute(stmt)
        result_obj = result_cls.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB Error: {e}")
    
    if not result_obj:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail="service not found")

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
                                active: Optional[bool] = Query(None)):
    
    #validate_token
    await jwt_manager.validate_token(token)

    try:
        stmt = select(Services)
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB Error: {e}")
    
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
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB Error: {e}")
    
    return result


async def update_service(db: db_dependency, token: if_admin_dependency, id: str, details: UpdateService):
    #validate token
    await jwt_manager.validate_token(token)

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
            #logger
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    try:
        select_stmt = select(Services).where(Services.id == id)
        result_cls = await db.execute(select_stmt)
        result_obj = result_cls.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB Error: {e}")
    
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

    return to_return

async def delete_service(db: db_dependency, token: if_admin_dependency, id: str):
    #validate token
    await jwt_manager.validate_token(token)
    #delete service using id
    try:
        stmt= delete(Services).where(Services.id == id)
        await db.execute(stmt)
        await db.flush()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB Error: {e}")
    
    return{"message": "service deleted"}