"""
Admin panel endpoints for managing system configuration.
Allows admins to manage RTO profiles, document types, staff, courses, etc.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models import UserRole, RtoProfile, DocumentType, UserAccount, StaffProfile, CourseOffering
from app.schemas.admin import (
    RTOProfileCreate,
    RTOProfileResponse,
    DocumentTypeCreate,
    DocumentTypeResponse,
    StaffCreateRequest,
    StaffResponse,
    CourseOfferingCreate,
    CourseOfferingResponse,
)
from app.core.security import get_password_hash

router = APIRouter()


def require_admin(current_user: dict = Depends(get_current_user)):
    """Dependency to ensure user is admin."""
    if current_user.get("role") != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ==================== RTO PROFILE MANAGEMENT ====================

@router.get("/rto-profiles", response_model=List[RTOProfileResponse])
async def list_rto_profiles(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """List all RTO profiles."""
    profiles = db.query(RtoProfile).all()
    return profiles


@router.post("/rto-profiles", response_model=RTOProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_rto_profile(
    data: RTOProfileCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Create a new RTO profile."""
    # Check if profile already exists
    existing = db.query(RtoProfile).filter(RtoProfile.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"RTO profile '{data.name}' already exists"
        )

    profile = RtoProfile(
        name=data.name,
        cricos_code=data.cricos_code,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        address=data.address,  # JSONB field
        abn=data.abn,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/rto-profiles/{rto_id}", response_model=RTOProfileResponse)
async def get_rto_profile(
    rto_id: UUID,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Get RTO profile details."""
    profile = db.query(RtoProfile).filter(RtoProfile.id == rto_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RTO profile not found"
        )
    return profile


@router.patch("/rto-profiles/{rto_id}", response_model=RTOProfileResponse)
async def update_rto_profile(
    rto_id: UUID,
    data: RTOProfileCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Update RTO profile."""
    profile = db.query(RtoProfile).filter(RtoProfile.id == rto_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RTO profile not found"
        )

    for key, value in data.dict(exclude_unset=True).items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/rto-profiles/{rto_id}")
async def delete_rto_profile(
    rto_id: UUID,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Delete RTO profile."""
    profile = db.query(RtoProfile).filter(RtoProfile.id == rto_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RTO profile not found"
        )

    db.delete(profile)
    db.commit()
    
    return {"message": "RTO profile deleted successfully"}


# ==================== DOCUMENT TYPE MANAGEMENT ====================

@router.get("/document-types", response_model=List[DocumentTypeResponse])
async def list_document_types(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """List all document types."""
    types = db.query(DocumentType).order_by(DocumentType.display_order).all()
    return types


@router.post("/document-types", response_model=DocumentTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_document_type(
    data: DocumentTypeCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Create a new document type."""
    # Check if code already exists
    existing = db.query(DocumentType).filter(DocumentType.code == data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document type code '{data.code}' already exists"
        )

    doc_type = DocumentType(
        code=data.code,
        name=data.name,
        stage=data.stage,
        is_mandatory=data.is_mandatory,
        ocr_model_ref=data.ocr_model_ref,
        display_order=data.display_order,
    )

    db.add(doc_type)
    db.commit()
    db.refresh(doc_type)
    return doc_type


@router.get("/document-types/{doc_type_id}", response_model=DocumentTypeResponse)
async def get_document_type(
    doc_type_id: UUID,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Get document type details."""
    doc_type = db.query(DocumentType).filter(DocumentType.id == doc_type_id).first()
    if not doc_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document type not found"
        )
    return doc_type


@router.patch("/document-types/{doc_type_id}", response_model=DocumentTypeResponse)
async def update_document_type(
    doc_type_id: UUID,
    data: DocumentTypeCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Update document type."""
    doc_type = db.query(DocumentType).filter(DocumentType.id == doc_type_id).first()
    if not doc_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document type not found"
        )

    for key, value in data.dict(exclude_unset=True).items():
        setattr(doc_type, key, value)

    db.commit()
    db.refresh(doc_type)
    return doc_type


@router.delete("/document-types/{doc_type_id}")
async def delete_document_type(
    doc_type_id: UUID,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Delete document type."""
    doc_type = db.query(DocumentType).filter(DocumentType.id == doc_type_id).first()
    if not doc_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document type not found"
        )

    db.delete(doc_type)
    db.commit()
    
    return {"message": "Document type deleted successfully"}


# ==================== STAFF MANAGEMENT ====================

@router.get("/staff", response_model=List[StaffResponse])
async def list_staff(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """List all staff members."""
    staff_members = db.query(UserAccount).filter(
        UserAccount.role == UserRole.STAFF
    ).all()
    return staff_members


@router.post("/staff", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    data: StaffCreateRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Create a new staff member."""
    # Check if email already exists
    existing = db.query(UserAccount).filter(UserAccount.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{data.email}' already registered"
        )

    # Get default RTO (admin RTO) - in real scenario, this would be configurable
    default_rto = db.query(RtoProfile).filter(RtoProfile.is_active == True).first()
    if not default_rto:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active RTO profile found. Create an RTO first."
        )

    # Create user account
    user = UserAccount(
        email=data.email,
        password_hash=get_password_hash(data.password),
        role=UserRole.STAFF,
        rto_profile_id=default_rto.id,
    )

    db.add(user)
    db.flush()

    # Create staff profile
    staff_profile = StaffProfile(
        user_account_id=user.id,
        department=data.department,
        job_title=data.job_title,
        permissions=data.permissions,
    )

    db.add(staff_profile)
    db.commit()
    db.refresh(user)

    return user


@router.get("/staff/{staff_id}", response_model=StaffResponse)
async def get_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Get staff member details."""
    user = db.query(UserAccount).filter(
        UserAccount.id == staff_id,
        UserAccount.role == UserRole.STAFF
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    return user


@router.patch("/staff/{staff_id}/deactivate")
async def deactivate_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Deactivate a staff member."""
    user = db.query(UserAccount).filter(
        UserAccount.id == staff_id,
        UserAccount.role == UserRole.STAFF
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )

    user.status = "inactive"
    db.commit()

    return {"message": f"Staff member {user.email} deactivated"}


# ==================== COURSE MANAGEMENT ====================

@router.get("/courses", response_model=List[CourseOfferingResponse])
async def list_courses(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """List all courses."""
    courses = db.query(CourseOffering).all()
    return courses


@router.post("/courses", response_model=CourseOfferingResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    data: CourseOfferingCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Create a new course."""
    # Check if course code already exists
    existing = db.query(CourseOffering).filter(CourseOffering.course_code == data.course_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course code '{data.course_code}' already exists"
        )

    course = CourseOffering(
        course_code=data.course_code,
        course_name=data.course_name,
        intake=data.intake,
        campus=data.campus,
        tuition_fee=data.tuition_fee,
        application_deadline=data.application_deadline,
        is_active=True,
    )

    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/courses/{course_id}", response_model=CourseOfferingResponse)
async def get_course(
    course_id: UUID,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Get course details."""
    course = db.query(CourseOffering).filter(CourseOffering.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    return course


@router.patch("/courses/{course_id}", response_model=CourseOfferingResponse)
async def update_course(
    course_id: UUID,
    data: CourseOfferingCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Update course details."""
    course = db.query(CourseOffering).filter(CourseOffering.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    for key, value in data.dict(exclude_unset=True).items():
        setattr(course, key, value)

    db.commit()
    db.refresh(course)
    return course


@router.delete("/courses/{course_id}")
async def delete_course(
    course_id: UUID,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Delete course."""
    course = db.query(CourseOffering).filter(CourseOffering.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    db.delete(course)
    db.commit()
    
    return {"message": "Course deleted successfully"}


# ==================== SYSTEM STATUS ====================

@router.get("/status")
async def get_system_status(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """Get system configuration status."""
    rto_count = db.query(RtoProfile).count()
    doc_type_count = db.query(DocumentType).count()
    staff_count = db.query(UserAccount).filter(UserAccount.role == UserRole.STAFF).count()
    course_count = db.query(CourseOffering).count()

    return {
        "rto_profiles": rto_count,
        "document_types": doc_type_count,
        "staff_members": staff_count,
        "courses": course_count,
        "configured": rto_count > 0 and doc_type_count > 0 and staff_count > 0 and course_count > 0
    }
