from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
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
from src.dashboard.routes import dashboard_router
from src.calendar.routes import router

templates = Jinja2Templates(directory="templates")

app = FastAPI()

@app.on_event("startup") #TODO: fix deprecations
def on_startup():
    Base.metadata.create_all(bind=engine)  # create tables
    seed_db()  # seed data



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Redirect-URL"]
)

app.include_router(complaint_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(profile_router)
app.include_router(hall_router)
app.include_router(chat_router)
app.include_router(room_router),
app.include_router(allocation_router)
app.include_router(dashboard_router)
app.include_router(router)

@app.get("/")
def root(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

@app.get("/health")
def health():
    return {"ping":"pong"}
print(app)