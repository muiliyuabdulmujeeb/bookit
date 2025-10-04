from fastapi import HTTPException, status, Query
from sqlalchemy import select, update, delete, desc, and_
from typing import Annotated, Optional, Union, Any
from datetime import datetime, timezone
from schemas.bookings.bookings import CreateBooking, UpdateBooking, CreateBookingResponseModel
from database.config import db_dependency
from database.models import Bookings, Users, Services
from shared import StatusEnum, RoleEnum, UpdateBookingAction
from utils.manager import jwt_manager, token_dependency, if_admin_dependency, if_user_dependency

async def create_booking(db: db_dependency, token: if_user_dependency, details: CreateBooking) -> CreateBookingResponseModel:
    #validate the token
    await jwt_manager.validate_token(token)

    booking_user_id = details.user_id
    booking_service_id = details.service_id
    booking_start_time = details.start_time
    booking_end_time = details.end_time
    booking_status = details.status

    #check if user_id exists
    try:
        user_id_stmt = select(Users).where(Users.id == booking_user_id)
        user_id_result_obj = await db.execute(user_id_stmt)
        db_user_id = user_id_result_obj.scalar_one_or_none
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
    
    if db_user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "invalid user_id")
    
    #check if service_id exists
    try:
        service_id_stmt = select(Services).where(Services.id == booking_service_id)
        service_id_result_obj = await db.execute(service_id_stmt)
        db_service_id = service_id_result_obj.scalar_one_or_none
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
    
    if db_service_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "invalid service_id")

    #check if the service is still active
    try:
        check_stmt = select(Bookings).where(Bookings.service_id == booking_service_id).order_by(desc(Bookings.created_at)).limit(1)
        result_obj= await db.execute(check_stmt)
        last_service_booking = result_obj.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
    
    # check if expired
    if last_service_booking.end_time < datetime.now(tz=timezone.utc):
        new_status = None
        
        if last_service_booking.status == StatusEnum.PENDING.value:
            new_status = StatusEnum.CANCELLED.value
        elif last_service_booking.status not in (StatusEnum.CANCELLED.value, StatusEnum.COMPLETED.value):
            new_status = StatusEnum.COMPLETED.value
        
        if new_status:
            try:
                update_stmt = (update(Bookings).where(Bookings.service_id == booking_service_id).values(status=new_status))
                await db.execute(update_stmt)
                await db.commit()
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=f"Db Error: {e}")
    
    #check if it is confirmed i.e another user is still using the service
    if last_service_booking == StatusEnum.CONFIRMED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "Requested service not available")
    
    #since the service is active, it can be booked
    to_add = Bookings(user_id= booking_user_id, service_id= booking_service_id, start_time = booking_start_time, end_time= booking_end_time, status= booking_status)
    try:
        db.add(to_add)
        await db.flush()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail= f"Db Error: {e}")
    #get all booking details
    try:
        stmt = select(Bookings).where(Bookings.user_id == booking_user_id and
                                      Bookings.service_id == booking_service_id and
                                      Bookings.start_time == booking_start_time and
                                      Bookings.end_time == booking_end_time and
                                      Bookings.status == booking_status
                                      )
        details_result_cls = await db.execute(stmt)
        result_obj = details_result_cls.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail= f"Db Error: {e}")
    to_return = {
        "message": "booking created",
        "id": result_obj.id,
        "user_id": result_obj.user_id,
        "service_id": result_obj.service_id,
        "start_time": result_obj.start_time,
        "end_time": result_obj.end_time,
        "status": result_obj.status,
        "created_at": result_obj.created_at
        }
    return to_return

async def get_bookings(db: db_dependency,
                       token: str,
                       bookings_status: Optional[RoleEnum] = Query(None),
                       bookings_from: Optional[datetime] = Query(None),
                       bookings_to: Optional[datetime] = Query(None)):
    #validate token
    await jwt_manager.validate_token(token)
    #check user_role
    token_role = await jwt_manager.check_role(token)
    #if role = user path
    if token_role == RoleEnum.USER.value:
        #get user_id
        user_details: dict = await jwt_manager.decode_token(token)
        user_id = user_details.get("sub", None)
        if not user_id:
            raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="invalid user_id")
        #query all bookings with the user_id in db
        try:
            user_bookings_stmt = select(Bookings).where(Bookings.user_id == user_id).order_by(desc(Bookings.created_at))
            user_bookings_cls = await db.execute(user_bookings_stmt)
            user_bookings_obj = user_bookings_cls.scalars().all()
        except Exception as e:
            #logger
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
        #return the resulting booking objects
        return user_bookings_obj
    #if role = admin path
    if token_role == RoleEnum.ADMIN.value:
        try:
            all_booking_stmt = select(Bookings)
        except Exception as e:
            #logger
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
        
        filters = []
        if bookings_status is not None:
            filters.append(Bookings.status.ilike(f"%{bookings_status}%"))
        if bookings_from is not None:
            filters.append(Bookings.created_at > bookings_from)
        if bookings_to is not None:
            filters.append(Bookings.created_at < bookings_to)
        
        if filters:
            try:
                all_booking_stmt = all_booking_stmt.where(and_(*filters)).order_by(desc(Bookings.created_at))
                all_booking_cls = await db.execute(all_booking_cls)
                all_booking_obj = all_booking_cls.scalars().all()
            except Exception as e:
                #logger
                raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
            
            return all_booking_obj
        
        if not filters:
            try:
                all_booking_stmt = select(Bookings).order_by(desc(Bookings.created_at))
                all_booking_cls = await db.execute(all_booking_cls)
                all_booking_obj = all_booking_cls.scalars().all()
            except Exception as e:
                #logger
                raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
            
            return all_booking_obj
    
async def get_bookings_by_id(db: db_dependency, token: token_dependency, id: str):
    #validate token
    await jwt_manager.validate_token(token)
    #retrieve booking by id
    try:
        booking_stmt = select(Bookings).where(Bookings.id == id)
        stmt_obj = await db.execute(booking_stmt)
        result = stmt_obj.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
    
    to_return = {
        "id": result.id,
        "user_id": result.user_id,
        "service_id": result.service_id,
        "start_time": result.start_time,
        "end_time": result.end_time,
        "status": result.status,
        "created_at": result.created_at
    }
    
    return to_return


async def update_booking(db: db_dependency, token: str, id: str, preferences: UpdateBooking):
    #validate token
    await jwt_manager.validate_token(token)
    #check user role and user_id
    token_role = await jwt_manager.check_role(token)
    token_user_details = jwt_manager.decode_token(token)
    token_user_id = token_user_details.get("sub", None)
    #retrieve the booking details from db
    try:
        retrieve_stmt = select(Bookings).where(Bookings.id == id)
        retrieve_obj = await db.execute(retrieve_stmt)
        retrieve_data = retrieve_obj.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
    if retrieve_data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, details= "booking not found")
    if retrieve_data.user_id != token_user_id:
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, details= "you can only update a booking you created")
    #user path
    if token_role == RoleEnum.USER.value:
        #check if the booking is pending or confirmed
        if retrieve_data not in (StatusEnum.PENDING.value, StatusEnum.CONFIRMED.value):
            raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="booking status has to be pending or confirmed to perform action")
        #for cancel action
        if preferences.action == UpdateBookingAction.CANCEL.value:
            try:
                update_stmt1= (update(Bookings).where(Bookings.id == id).values(status= StatusEnum.CANCELLED.value))
                await db.execute(update_stmt1)
                await db.flush()
            except Exception as e:
                #logger
                raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
            return {"message": "booking cancelled"}
        #for reschedule action
        elif preferences.action == UpdateBookingAction.RESCHEDULE.value:
            if preferences.start_time is None or preferences.end_time is None:
                raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="to reschedule, specify new start_time and end_time")
            try:
                update_stmt2= (update(Bookings).where(Bookings.id == id).values(start_time= preferences.start_time, end_time = preferences.end_time))
                await db.execute(update_stmt2)
                await db.flush()
            except Exception as e:
                #logger
                raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
            return {"message": "booking rescheduled"}
    #admin path    
    if token_role == RoleEnum.ADMIN.value:
        #check if update_status_to is None
        if preferences.update_status_to is None:
            raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="update_status_to cannot be null")
        try:
            admin_update_stmt = (update(Bookings).where(Bookings.id == id).values(status= preferences.update_status_to))
            await db.execute(admin_update_stmt)
            await db.flush()
        except Exception as e:
            #logger
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
        return {"Message": "booking status updated"}        #write the correct response to sync with model
    
async def delete_booking(db: db_dependency, token: str, id: str):
    #validate token
    await jwt_manager.validate_token(token)
    #retrieve the boking details
    try:
        booking_stmt = select(Bookings).where(Bookings.id == id)
        stmt_obj = await db.execute(booking_stmt)
        result = stmt_obj.scalar_one_or_none()
    except Exception as e:
        #logger
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
    
    token_role = await jwt_manager.check_role(token)

    #user delete path
    token_user_details = jwt_manager.decode_token(token)
    token_user_id = token_user_details.get("sub", None)
    if not token_user_id:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, details= "invalid user_id")
    if result.user_id == token_user_id:     #this means the user created the booking so, they can delete it
        if token_role == RoleEnum.USER.value:
            if result.start_time < datetime.now(tz= timezone.utc):
                raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="you can only delete bookings that is yet to start")
            try:
                del_booking_stmt = delete(Bookings).where(Bookings.id == id)
                await db.execute(del_booking_stmt)
                db.flush()
            except Exception as e:
                #logger
                raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
            return {"message": f"booking with id {id} deleted"}
    else:
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail="you can only delete a booking you created")
    #admin delete path
    if token_role == RoleEnum.ADMIN.value:
        try:
            del_booking_stmt = delete(Bookings).where(Bookings.id == id)
            await db.execute(del_booking_stmt)
            db.flush()
        except Exception as e:
            #logger
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Db Error: {e}")
        
        return {"message": f"booking with id {id} deleted"}