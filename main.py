from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.routes import(
    auth_router,
    profile_router,
    user_router
)
from src.common.db import (
    Base,
    engine,
)
from src.common.seed import seed_db
from src.complaints.routes import complaint_router
from src.hostels.routes import(
    hall_router,
    room_router,
    allocation_router
)
from src.chat.routes import chat_router

app = FastAPI()

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)  # create tables
    seed_db()  # seed data

origins = [
    "https://v0-residence-management-system-eight.vercel.app",
    
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(complaint_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(profile_router)
app.include_router(hall_router)
app.include_router(chat_router)
app.include_router(room_router),
app.include_router(allocation_router)

@app.get("/health")
def health():
    return {"ping":"pong"}
print(app)