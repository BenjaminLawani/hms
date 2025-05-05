from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.routes import(
    auth_router,
    profile_router,
    user_router
)
from src.complaints.routes import complaint_router
from src.hostels.routes import(
    hall_router,
    room_router,
    allocation_router
)
from src.chat.routes import chat_router

app = FastAPI()

app.include_router(complaint_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(profile_router)
app.include_router(hall_router)
app.include_router(chat_router)
app.include_router(room_router),
app.include_router(allocation_router)
print(app)