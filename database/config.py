import os
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
from redis import Redis

load_dotenv()
DB_URL = os.getenv("DEV_DB_URL")
DEV_REDIS_HOST = os.getenv("DEV_REDIS_HOST")
DEV_REDIS_PORT = os.getenv("DEV_REDIS_PORT")
DEV_REDIS_DB = os.getenv("DEV_REDIS_DB")

Base = declarative_base()

engine = create_async_engine(url=DB_URL)

Session = async_sessionmaker(engine, expire_on_commit= False)

async def get_db():
    async with Session() as session:
        try:
            yield session
        finally:
            await session.close()

db_dependency = Annotated[AsyncSession, Depends(get_db)]

redis_client = Redis(host= DEV_REDIS_HOST, port= DEV_REDIS_PORT, db= DEV_REDIS_DB)

async def get_redis():
    yield redis_client

redis_dependency = Annotated[Redis, Depends(get_redis)]