import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, INTEGER, UUID, VARCHAR, ForeignKey, Enum, DateTime, DECIMAL, CheckConstraint, Text
from database.config import Base
from shared import RoleEnum, IsActiveEnum, StatusEnum


class Users(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid= True), primary_key= True, default= lambda: uuid.uuid4())
    full_name = Column(VARCHAR(50), nullable= False)
    email = Column(VARCHAR(50), unique=True, nullable= False)
    password_hash = Column(Text(), nullable= False)
    role = Column(Enum(RoleEnum, name = "role_enum", create_type = True), nullable= False, default= RoleEnum.USER)
    created_at = Column(DateTime(timezone= True), nullable= False, default= lambda: datetime.now(tz= timezone.utc))


class Services(Base):
    __tablename__ = "services"

    id = Column(UUID(as_uuid= True), primary_key= True, default= lambda: uuid.uuid4())
    title = Column(VARCHAR(50), nullable= False)
    description = Column(VARCHAR(250))
    price = Column(DECIMAL(10, 2), nullable= False)
    duration_mins = Column(INTEGER(), nullable= False)
    is_active = Column(Enum(IsActiveEnum, name = "is_active_enum", create_type = True), nullable= False, default= IsActiveEnum.TRUE)
    created_at = Column(DateTime(timezone= True), nullable= False, default= lambda: datetime.now(tz= timezone.utc))

class Bookings(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid= True), primary_key= True, default= lambda: uuid.uuid4())
    user_id = Column(UUID(as_uuid= True), ForeignKey("users.id", onupdate= "CASCADE", ondelete= "CASCADE"), index= True)
    service_id = Column(UUID(as_uuid= True), ForeignKey("services.id", onupdate= "CASCADE", ondelete= "CASCADE"))
    start_time = Column(DateTime(timezone= True), nullable= False, default= lambda: datetime.now(tz= timezone.utc))
    end_time = Column(DateTime(timezone= True), nullable= False)
    role = Column(Enum(StatusEnum, name = "status_enum", create_type = True), nullable= False, default= StatusEnum.PENDING)
    created_at = Column(DateTime(timezone= True), nullable= False, default= lambda: datetime.now(tz= timezone.utc))

class Reviews(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid= True), primary_key= True, default= lambda: uuid.uuid4())
    booking_id = Column(UUID(as_uuid= True), ForeignKey("bookings.id", onupdate= "CASCADE", ondelete= "CASCADE"), index= True)
    rating = Column(INTEGER(), nullable= False)
    comment = Column(VARCHAR(250))
    created_at = Column(DateTime(timezone= True), nullable= False, default= lambda: datetime.now(tz= timezone.utc))


    __table_agrs__ = (
        CheckConstraint('rating > 1 AND rating < 6', name= "rating_between_1_to_5")
    )

class Blacklists(Base):
    __tablename__ = "blacklists"

    token = Column(UUID(as_uuid= True), primary_key= True, nullable= False)
