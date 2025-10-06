from fastapi import FastAPI
from routes.auth.auth import auth_router
from routes.services.services import service_router
from routes.bookings.bookings import bookings_router
from routes.reviews.reviews import reviews_router

app = FastAPI(title="BookIt", description= "A production-ready simple bookings API", version="0.0.1")


app.include_router(auth_router)
app.include_router(service_router)
app.include_router(bookings_router)
app.include_router(reviews_router)


@app.get("/", status_code= 200)
async def app_home():
    return {"message": "welcome to bookit"}

@app.get("/health", status_code= 200)
async def app_health():
    return {"message": "App is running"}