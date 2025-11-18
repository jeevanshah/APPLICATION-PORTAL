"""
API v1 router aggregator.
"""
from fastapi import APIRouter

# Import routers
from app.api.v1.endpoints import admin, admin_ui, application_steps, applications, auth, documents, staff, students

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(
    applications.router,
    prefix="/applications",
    tags=["Applications"])
api_router.include_router(
    application_steps.router,
    prefix="/applications",
    tags=["Application Steps"])
api_router.include_router(
    students.router,
    prefix="/students",
    tags=["Students"])
api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"])
api_router.include_router(
    staff.router,
    prefix="/staff",
    tags=["Staff Workflow"])
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"])
api_router.include_router(
    admin_ui.router,
    prefix="/admin-panel",
    tags=["Admin Panel UI"])

# TODO: Add more routers as they're implemented
# api_router.include_router(timeline.router, prefix="/timeline", tags=["Timeline"])
# api_router.include_router(users.router, prefix="/users", tags=["Users"])


@api_router.get("/")
async def api_root():
    """API v1 root."""
    return {"message": "Churchill Application Portal API v1"}
