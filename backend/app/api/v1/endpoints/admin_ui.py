"""
Admin panel UI endpoints using Jinja2 templates.
Provides web interface for managing system configuration.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.api.dependencies import get_current_user, get_db
from app.models import UserRole, RtoProfile, DocumentType, UserAccount, CourseOffering
from app.api.v1.endpoints.admin import require_admin
from app.core.security import decode_token

router = APIRouter()

# Set up Jinja2 templates
templates = Jinja2Templates(directory="app/templates")


def get_token_from_storage(request: Request) -> Optional[str]:
    """Extract token from cookie or localStorage (via header)."""
    # Try to get from Authorization header (when localStorage is used)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return None


async def get_admin_user(request: Request):
    """Get current admin user or redirect to login."""
    token = get_token_from_storage(request)
    if not token:
        return None
    
    payload = decode_token(token)
    if not payload:
        return None
    
    # Check if admin role
    role = payload.get("role", "").upper()
    if role != "ADMIN":
        return None
    
    return payload


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page."""
    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard homepage."""
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})


@router.get("/rto-profiles", response_class=HTMLResponse)
async def rto_profiles_page(request: Request):
    """RTO profiles management page."""
    return templates.TemplateResponse("admin/rto_profiles.html", {"request": request})


@router.get("/document-types", response_class=HTMLResponse)
async def document_types_page(request: Request):
    """Document types management page."""
    return templates.TemplateResponse("admin/document_types.html", {"request": request})


@router.get("/staff", response_class=HTMLResponse)
async def staff_page(request: Request):
    """Staff management page."""
    return templates.TemplateResponse("admin/staff.html", {"request": request})


@router.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request):
    """Agent partners management page."""
    return templates.TemplateResponse("admin/agents.html", {"request": request})


@router.get("/courses", response_class=HTMLResponse)
async def courses_page(request: Request):
    """Courses management page."""
    return templates.TemplateResponse("admin/courses.html", {"request": request})


@router.get("/campuses", response_class=HTMLResponse)
async def campuses_page(request: Request):
    """Campuses management page."""
    return templates.TemplateResponse("admin/campuses.html", {"request": request})
