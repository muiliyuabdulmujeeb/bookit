from fastapi import FastAPI, status, HTTPException
from routes.auth.auth import auth_router

app = FastAPI(title="BookIt", description= "A production-ready simple bookings API", version="0.0.1")


app.include_router(auth_router)