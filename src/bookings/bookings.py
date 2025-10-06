from fastapi import HTTPException, status, Query
from sqlalchemy import select, update, delete, desc, and_
from typing import Optional, List
from datetime import datetime, timezone
from schemas.bookings.bookings import CreateBooking, UpdateBooking, CreateBookingResponseModel
from database.config import db_dependency
from database.models import Bookings, Users, Services
from shared import StatusEnum, RoleEnum, UpdateBookingAction
from utils.manager import jwt_manager, token_dependency, check_if_user
from utils.logger import get_logger

logger = get_logger("booking")

async def create_booking(db: db_dependency, token: str, booking_details: CreateBooking) -> List[CreateBookingResponseModel]:
    logger.info("create booking")
    #validate the token
    await jwt_manager.validate_token(db, token)
    await check_if_user(db, token)
    booking_user_id = booking_details.user_id
    booking_service_id = booking_details.service_id
    booking_start_time = booking_details.start_time
    booking_end_time = booking_details.end_time
    booking_status = booking_details.status

    #check if booking_user_id is the same as the id in token(enforces same user creating the resource)
    decoded_token = await jwt_manager.decode_token(token)
    token_user_id = decoded_token.get("sub")
    if token_user_id != str(booking_user_id):
        logger.error("user not authorized")
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail="only authorized users are allowed to create this resource")
    
    #check if user_id exists
    try:
        user_stmt = select(Users).where(Users.id == booking_user_id)
        user_result_obj = await db.execute(user_stmt)
        db_user = user_result_obj.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    if db_user.id is None:
        logger.info("invalid user id")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "invalid user_id")
    
    #check if service_id exists
    try:
        service_id_stmt = select(Services).where(Services.id == booking_service_id)
        service_id_result_obj = await db.execute(service_id_stmt)
        db_service_id = service_id_result_obj.scalar_one_or_none
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    if db_service_id is None:
        logger.error("invalid service id")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail= "invalid service_id")

    #check if the service is still active
    try:
        check_stmt = select(Bookings).where(Bookings.service_id == booking_service_id).order_by(desc(Bookings.created_at)).limit(1)
        result_obj= await db.execute(check_stmt)
        last_service_booking = result_obj.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    # check if expired
    if last_service_booking is not None and last_service_booking.end_time < datetime.now(tz=timezone.utc):
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
                await db.rollback()
                logger.error(f"Db Error: {e.__class__.__name__}: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    #check if it is confirmed i.e another user is still using the service
    if last_service_booking is not None and last_service_booking == StatusEnum.CONFIRMED.value:
        logger.error("requested service is in use by another user")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail= "Requested service is in use, try again later")
    
    #since the service is active, it can be booked
    to_add = Bookings(user_id= booking_user_id, service_id= booking_service_id, start_time = booking_start_time, end_time= booking_end_time, status= booking_status)
    try:
        db.add(to_add)
        await db.flush()
    except Exception as e:
        await db.rollback()
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    #get all booking details
    try:
        stmt = select(Bookings).where((Bookings.user_id == booking_user_id) &
                                      (Bookings.service_id == booking_service_id) &
                                      (Bookings.start_time == booking_start_time) &
                                      (Bookings.end_time == booking_end_time) &
                                      (Bookings.status == booking_status)
                                      )
        details_result_cls = await db.execute(stmt)
        result_obj = details_result_cls.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
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
    logger.info("booking created")
    return to_return

async def get_bookings(db: db_dependency,
                       token: str,
                       bookings_status: Optional[StatusEnum] = Query(None),
                       bookings_from: Optional[datetime] = Query(None),
                       bookings_to: Optional[datetime] = Query(None)):
    logger.info("getting bookings")
    #validate token
    await jwt_manager.validate_token(db, token)
    #check user_role
    token_role = await jwt_manager.check_role(db, token)
    #if role = user path
    if token_role == RoleEnum.USER.value:
        #get user_id
        user_details: dict = await jwt_manager.decode_token(token)
        user_id = user_details.get("sub", None)
        if not user_id:
            logger.error("invalid user id")
            raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="invalid user_id")
        #query all bookings with the user_id in db
        try:
            user_bookings_stmt = select(Bookings).where(Bookings.user_id == user_id).order_by(desc(Bookings.created_at))
            user_bookings_cls = await db.execute(user_bookings_stmt)
            user_bookings_obj = user_bookings_cls.scalars().all()
        except Exception as e:
            logger.error(f"Db Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
        #return the resulting booking objects
        logger.info("get bookings request successful")
        return user_bookings_obj
    #if role = admin path
    if token_role == RoleEnum.ADMIN.value:
        try:
            all_booking_stmt = select(Bookings)
        except Exception as e:
            logger.error(f"Db Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
        
        filters = []
        if bookings_status is not None:
            filters.append(Bookings.status == bookings_status)
        if bookings_from is not None:
            filters.append(Bookings.start_time > bookings_from)
        if bookings_to is not None:
            filters.append(Bookings.end_time < bookings_to)
        
        if filters:
            try:
                all_booking_stmt = all_booking_stmt.where(and_(*filters)).order_by(desc(Bookings.created_at))
                all_booking_cls = await db.execute(all_booking_stmt)
                all_booking_obj = all_booking_cls.scalars().all()
            except Exception as e:
                logger.error(f"Db Error: {e.__class__.__name__}: {e}")
                raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
            logger.info("get bookings request successful")
            return all_booking_obj
        
        if not filters:
            try:
                all_booking_stmt = select(Bookings).order_by(desc(Bookings.created_at))
                all_booking_cls = await db.execute(all_booking_stmt)
                all_booking_obj = all_booking_cls.scalars().all()
            except Exception as e:
                logger.error(f"Db Error: {e.__class__.__name__}: {e}")
                raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
            logger.info("get bookings request successful")
            
            return all_booking_obj
    
async def get_bookings_by_id(db: db_dependency, token: token_dependency, id: str):
    logger.info("getting bookings by id")
    #validate token
    await jwt_manager.validate_token(db, token)
    token_role = await jwt_manager.check_role(db, token)
    if token_role == RoleEnum.ADMIN.value:
        #retrieve booking by id
        try:
            booking_stmt = select(Bookings).where(Bookings.id == id)
            stmt_obj = await db.execute(booking_stmt)
            result = stmt_obj.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Db Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
        
        to_return = {
            "id": result.id,
            "user_id": result.user_id,
            "service_id": result.service_id,
            "start_time": result.start_time,
            "end_time": result.end_time,
            "status": result.status,
            "created_at": result.created_at
        }
        logger.info("get booking by id request successful")
        return to_return
    elif token_role == RoleEnum.USER.value:
        #get user_id
        user_details: dict = await jwt_manager.decode_token(token)
        user_id = user_details.get("sub", None)
        if not user_id:
            logger.error("invalid user id")
            raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="invalid user_id")
        #retrieve booking by id
        try:
            booking_stmt = select(Bookings).where(Bookings.id == id)
            stmt_obj = await db.execute(booking_stmt)
            result = stmt_obj.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Db Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")

        if user_id != str(result.user_id):
            logger.error("unauthorized user")
            raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail="you are not allowed to access this resource")
        
        to_return = {
            "id": result.id,
            "user_id": result.user_id,
            "service_id": result.service_id,
            "start_time": result.start_time,
            "end_time": result.end_time,
            "status": result.status,
            "created_at": result.created_at
        }
        logger.info("get bookings by id request successful")
        return to_return
    else:
        logger.error("unauthorized user")
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail="you do not have the permission to access this resource")

async def update_booking(db: db_dependency, token: str, id: str, preferences: UpdateBooking):
    logger.info("update booking")
    #validate token
    await jwt_manager.validate_token(db, token)
    #check user role and user_id
    token_role = await jwt_manager.check_role(db, token)
    token_user_details = await jwt_manager.decode_token(token)
    token_user_id = token_user_details.get("sub", None)
    #retrieve the booking details from db
    try:
        retrieve_stmt = select(Bookings).where(Bookings.id == id)
        retrieve_obj = await db.execute(retrieve_stmt)
        retrieve_data = retrieve_obj.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    if retrieve_data is None:
        logger.error("booking not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail= "booking not found")
    #user path
    if token_role == RoleEnum.USER.value:
        if str(retrieve_data.user_id) != token_user_id:
            logger.error("user not authorized")
            raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail= "you can only update a booking you created")
        #check if the booking is pending or confirmed
        if retrieve_data.status not in (StatusEnum.PENDING, StatusEnum.CONFIRMED):
            logger.error("invalid request parameter")
            raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="booking status has to be pending or confirmed to perform action")
        #for cancel action
        if preferences.action not in (UpdateBookingAction.CANCEL.value, UpdateBookingAction.RESCHEDULE.value):
            logger.error("invalid request parameter")
            raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="specify the right action you want to carry out on the resource")
        if preferences.action.value == UpdateBookingAction.CANCEL.value:
            try:
                update_stmt1= (update(Bookings).where(Bookings.id == id).values(status= StatusEnum.CANCELLED))
                await db.execute(update_stmt1)
                await db.flush()
            except Exception as e:
                await db.rollback()
                logger.error(f"Db Error: {e.__class__.__name__}: {e}")
                raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
            logger.info("booking cancelled, update successful")
            return {"message": "booking cancelled"}
        #for reschedule action
        elif preferences.action.value == UpdateBookingAction.RESCHEDULE.value:
            if preferences.start_time is None or preferences.end_time is None:
                logger.error("invalid request parameter")
                raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="to reschedule, specify new start_time and end_time")
            try:
                update_stmt2= (update(Bookings).where(Bookings.id == id).values(start_time= preferences.start_time, end_time = preferences.end_time))
                await db.execute(update_stmt2)
                await db.flush()
            except Exception as e:
                logger.error(f"Db Error: {e.__class__.__name__}: {e}")
                raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
            logger.info("booking rescheduled, update successful")
            
            return {"message": "booking rescheduled"}
    #admin path    
    if token_role == RoleEnum.ADMIN.value:
        #check if update_status_to is None
        if preferences.status is None:
            logger.error("invalid request parameter")
            raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="status cannot be null")
        try:
            admin_update_stmt = (update(Bookings).where(Bookings.id == id).values(status= preferences.status))
            await db.execute(admin_update_stmt)
            await db.flush()
        except Exception as e:
            logger.error(f"Db Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
        logger.info("booking status updated")
        return {"Message": "booking status updated"}        
    
async def delete_booking(db: db_dependency, token: str, id: str):
    logger.info("delete booking")
    #validate token
    await jwt_manager.validate_token(db, token)
    #retrieve the boking details
    try:
        booking_stmt = select(Bookings).where(Bookings.id == id)
        stmt_obj = await db.execute(booking_stmt)
        result = stmt_obj.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Db Error: {e.__class__.__name__}: {e}")
        raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
    
    token_role = await jwt_manager.check_role(db, token)

    #user delete path
    token_user_details = await jwt_manager.decode_token(token)
    token_user_id = token_user_details.get("sub", None)
    if not token_user_id:
        logger.error("invalid user id")
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, details= "invalid user_id")
    if token_role == RoleEnum.USER.value:
        if str(result.user_id) == token_user_id:     #this means the user created the booking so, they can delete it
            if result.start_time < datetime.now(tz= timezone.utc):
                logger.error("invalid request")
                raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail="you can only delete bookings that is yet to start")
            try:
                del_booking_stmt = delete(Bookings).where(Bookings.id == id)
                await db.execute(del_booking_stmt)
                await db.flush()
            except Exception as e:
                await db.rollback()
                logger.error(f"Db Error: {e.__class__.__name__}: {e}")
                raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
            logger.info("booking deleted")
            return {"message": f"booking with id {id} deleted"}
        else:
            logger.error("user not authorized")
            raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail="you can only delete a booking you created")
    #admin delete path
    if token_role == RoleEnum.ADMIN.value:
        try:
            del_booking_stmt = delete(Bookings).where(Bookings.id == id)
            await db.execute(del_booking_stmt)
            await db.flush()
        except Exception as e:
            await db.rollback()
            logger.error(f"Db Error: {e.__class__.__name__}: {e}")
            raise HTTPException(status_code= status.HTTP_500_INTERNAL_SERVER_ERROR, detail="500 internal server error")
        logger.info("booking deleted")
        
        return {"message": f"booking with id {id} deleted"}