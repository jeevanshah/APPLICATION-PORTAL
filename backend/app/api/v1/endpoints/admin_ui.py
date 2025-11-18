"""
Admin panel UI endpoints using Jinja2 templates.
Provides web interface for managing system configuration.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models import UserRole, RtoProfile, DocumentType, UserAccount, CourseOffering
from app.api.v1.endpoints.admin import require_admin

router = APIRouter()

# Set up Jinja2 templates
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin dashboard homepage."""
    admin_user = require_admin(current_user)
    
    rto_count = db.query(RtoProfile).count()
    doc_type_count = db.query(DocumentType).count()
    staff_count = db.query(UserAccount).filter(UserAccount.role == UserRole.STAFF).count()
    course_count = db.query(CourseOffering).count()
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user_email": current_user.get("sub"),
        "rto_count": rto_count,
        "doc_type_count": doc_type_count,
        "staff_count": staff_count,
        "course_count": course_count,
        "configured": rto_count > 0 and doc_type_count > 0 and staff_count > 0 and course_count > 0,
    })


@router.get("/rto-profiles", response_class=HTMLResponse)
async def rto_profiles_page(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """RTO profiles management page."""
    admin_user = require_admin(current_user)
    return templates.TemplateResponse("admin/rto_profiles.html", {
        "request": request,
        "user_email": current_user.get("sub"),
    })


@router.get("/document-types", response_class=HTMLResponse)
async def document_types_page(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Document types management page."""
    admin_user = require_admin(current_user)
    return templates.TemplateResponse("admin/document_types.html", {
        "request": request,
        "user_email": current_user.get("sub"),
    })


@router.get("/staff", response_class=HTMLResponse)
async def staff_page(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Staff management page."""
    admin_user = require_admin(current_user)
    return templates.TemplateResponse("admin/staff.html", {
        "request": request,
        "user_email": current_user.get("sub"),
    })


@router.get("/courses", response_class=HTMLResponse)
async def courses_page(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Courses management page."""
    admin_user = require_admin(current_user)
    return templates.TemplateResponse("admin/courses.html", {
        "request": request,
        "user_email": current_user.get("sub"),
    })
