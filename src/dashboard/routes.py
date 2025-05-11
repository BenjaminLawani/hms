from fastapi import (
    APIRouter,
    Request,
    Depends
)
from fastapi.templating import Jinja2Templates
from src.common.security import(
    get_current_user,
    is_admin
)
from src.auth.models import User
from fastapi.responses import RedirectResponse
dashboard_router = APIRouter(
    prefix="/dashboard",
    tags=["DASHBOARD"]
)

templates = Jinja2Templates(directory="templates")

@dashboard_router.get("/admin-dashboard")
def admin_dashboard(request: Request):
    return templates.TemplateResponse("admin-dashboard.html", {"request": request})

@dashboard_router.get("/student-dashboard")
def student_dashboard(request: Request):
    return templates.TemplateResponse("student-dashboard.html", {"request": request})

@dashboard_router.post("/redirect")
def dashboard_redirect(current_user: User = Depends(get_current_user)):
    if current_user.is_admin:
        return RedirectResponse(url="/dashboard/admin-dashboard")
    else:
        return RedirectResponse(url="/dashboard/student-dashboard")