#!/usr/bin/env python3
"""
Admin Setup Script for Churchill Application Portal

This script initializes the system with all necessary static data:
- RTO Profile (Churchill Education)
- Admin User Account
- Document Types
- Course Offerings

Run with: python scripts/admin_setup.py
"""

import asyncio
import json
import sys
from datetime import datetime
from uuid import UUID, uuid4
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models import (
    RTOProfile, UserAccount, StaffProfile, DocumentType, CourseOffering, UserRole
)
from app.core.security import get_password_hash


# Static IDs for consistency
RTO_ID = UUID("00000000-0000-0000-0000-000000000001")
ADMIN_USER_ID = UUID("00000000-0000-0000-0000-000000000099")
ADMIN_STAFF_ID = UUID("00000000-0000-0000-0000-000000000199")

DOCUMENT_TYPES = {
    'PASSPORT': {
        'id': UUID('10000000-0000-0000-0000-000000000001'),
        'code': 'PASSPORT',
        'name': 'Passport',
        'is_mandatory': True,
        'ocr_model_ref': 'passport_ocr',
        'display_order': 1,
    },
    'TRANSCRIPT_SLC': {
        'id': UUID('10000000-0000-0000-0000-000000000002'),
        'code': 'TRANSCRIPT_SLC',
        'name': 'SLC Transcript',
        'is_mandatory': True,
        'ocr_model_ref': 'transcript_ocr',
        'display_order': 2,
    },
    'TRANSCRIPT_HSC': {
        'id': UUID('10000000-0000-0000-0000-000000000003'),
        'code': 'TRANSCRIPT_HSC',
        'name': 'HSC Transcript',
        'is_mandatory': True,
        'ocr_model_ref': 'transcript_ocr',
        'display_order': 3,
    },
    'ENGLISH_TEST': {
        'id': UUID('10000000-0000-0000-0000-000000000004'),
        'code': 'ENGLISH_TEST',
        'name': 'English Test Results (IELTS/TOEFL/PTE)',
        'is_mandatory': True,
        'ocr_model_ref': 'english_test_ocr',
        'display_order': 4,
    },
    'ID_CARD': {
        'id': UUID('10000000-0000-0000-0000-000000000005'),
        'code': 'ID_CARD',
        'name': 'National ID Card / Driver License',
        'is_mandatory': False,
        'ocr_model_ref': 'id_card_ocr',
        'display_order': 5,
    },
    'BIRTH_CERTIFICATE': {
        'id': UUID('10000000-0000-0000-0000-000000000006'),
        'code': 'BIRTH_CERTIFICATE',
        'name': 'Birth Certificate',
        'is_mandatory': False,
        'ocr_model_ref': None,
        'display_order': 6,
    },
    'PREVIOUS_VISA': {
        'id': UUID('10000000-0000-0000-0000-000000000007'),
        'code': 'PREVIOUS_VISA',
        'name': 'Previous Visa / Travel Documents',
        'is_mandatory': False,
        'ocr_model_ref': None,
        'display_order': 7,
    },
    'HEALTH_COVER': {
        'id': UUID('10000000-0000-0000-0000-000000000008'),
        'code': 'HEALTH_COVER',
        'name': 'Health Insurance (OSHC) Proof',
        'is_mandatory': False,
        'ocr_model_ref': None,
        'display_order': 8,
    },
    'FINANCIAL_PROOF': {
        'id': UUID('10000000-0000-0000-0000-000000000009'),
        'code': 'FINANCIAL_PROOF',
        'name': 'Financial Proof (Bank Statements)',
        'is_mandatory': False,
        'ocr_model_ref': None,
        'display_order': 9,
    },
    'RELATION_PROOF': {
        'id': UUID('10000000-0000-0000-0000-000000000010'),
        'code': 'RELATION_PROOF',
        'name': 'Family Relationship Proof',
        'is_mandatory': False,
        'ocr_model_ref': None,
        'display_order': 10,
    },
    'TAX_INCOME': {
        'id': UUID('10000000-0000-0000-0000-000000000011'),
        'code': 'TAX_INCOME',
        'name': 'Tax Return / Income Statement',
        'is_mandatory': False,
        'ocr_model_ref': None,
        'display_order': 11,
    },
    'BUSINESS_INCOME': {
        'id': UUID('10000000-0000-0000-0000-000000000012'),
        'code': 'BUSINESS_INCOME',
        'name': 'Business Documents',
        'is_mandatory': False,
        'ocr_model_ref': None,
        'display_order': 12,
    },
    'OTHER': {
        'id': UUID('10000000-0000-0000-0000-000000000013'),
        'code': 'OTHER',
        'name': 'Other Supporting Documents',
        'is_mandatory': False,
        'ocr_model_ref': None,
        'display_order': 13,
    },
}

COURSE_OFFERINGS = [
    {
        'code': 'BSB50120',
        'name': 'Diploma of Business',
        'intake': '2025-01',
        'campus': 'North Lakes',
        'tuition_fee': 18000.00,
        'application_deadline': '2024-12-31',
    },
    {
        'code': 'ICT50220',
        'name': 'Diploma of Information Technology',
        'intake': '2025-02',
        'campus': 'North Lakes',
        'tuition_fee': 20000.00,
        'application_deadline': '2025-01-15',
    },
    {
        'code': 'CHC50113',
        'name': 'Diploma of Early Childhood Education and Care',
        'intake': '2025-01',
        'campus': 'North Lakes',
        'tuition_fee': 16000.00,
        'application_deadline': '2024-12-31',
    },
]


def setup_rto_profile(db: Session) -> RTOProfile:
    """Create or update RTO Profile."""
    print("Setting up RTO Profile...")
    
    existing = db.query(RTOProfile).filter(RTOProfile.id == RTO_ID).first()
    if existing:
        print(f"  ✓ RTO Profile already exists: {existing.name}")
        return existing
    
    rto = RTOProfile(
        id=RTO_ID,
        name="Churchill Education",
        abn="12345678901",
        cricos_code="03089G",
        contact_email="info@churchilleducation.edu.au",
        contact_phone="+61 7 1234 5678",
        address={
            "street": "1 Innovation Way",
            "city": "North Lakes",
            "state": "QLD",
            "postcode": "4509",
            "country": "Australia",
        },
        logo_url=None,
        brand_settings={
            "primary_color": "#0F4C81",
            "secondary_color": "#F8B400",
            "font_family": "Inter, 'Segoe UI', sans-serif",
        },
        business_settings={
            "default_commission_rate": 0.15,
            "features_enabled": ["document_ai", "gs_assessment", "timeline_feed"],
        },
        is_active=True,
    )
    db.add(rto)
    db.commit()
    print(f"  ✓ Created RTO Profile: {rto.name}")
    return rto


def setup_admin_user(db: Session, rto_id: UUID) -> tuple[UserAccount, StaffProfile]:
    """Create or update Admin User Account."""
    print("\nSetting up Admin User...")
    
    existing_user = db.query(UserAccount).filter(
        UserAccount.id == ADMIN_USER_ID
    ).first()
    if existing_user:
        existing_staff = db.query(StaffProfile).filter(
            StaffProfile.user_account_id == ADMIN_USER_ID
        ).first()
        print(f"  ✓ Admin user already exists: {existing_user.email}")
        return existing_user, existing_staff
    
    # Create admin user account
    admin_user = UserAccount(
        id=ADMIN_USER_ID,
        rto_profile_id=rto_id,
        email="admin@churchilleducation.edu.au",
        password_hash=get_password_hash("Admin@123"),  # Change this!
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
        mfa_enabled=False,
    )
    db.add(admin_user)
    db.flush()
    
    # Create staff profile
    admin_staff = StaffProfile(
        id=ADMIN_STAFF_ID,
        user_account_id=admin_user.id,
        department="Administration",
        title="System Administrator",
        phone="+61 7 1234 5678",
        can_verify_documents=True,
        can_assess_gs=True,
        can_approve_offers=True,
    )
    db.add(admin_staff)
    db.commit()
    print(f"  ✓ Created Admin User: {admin_user.email}")
    print(f"    Password: Admin@123 (CHANGE THIS IN PRODUCTION!)")
    return admin_user, admin_staff


def setup_document_types(db: Session, rto_id: UUID) -> None:
    """Create or update Document Types."""
    print("\nSetting up Document Types...")
    
    for key, doc_type_data in DOCUMENT_TYPES.items():
        existing = db.query(DocumentType).filter(
            DocumentType.id == doc_type_data['id']
        ).first()
        
        if existing:
            print(f"  ✓ {existing.name}")
            continue
        
        doc_type = DocumentType(
            id=doc_type_data['id'],
            rto_profile_id=rto_id,
            code=doc_type_data['code'],
            name=doc_type_data['name'],
            stage='DRAFT',
            is_mandatory=doc_type_data['is_mandatory'],
            ocr_model_ref=doc_type_data['ocr_model_ref'],
            display_order=doc_type_data['display_order'],
        )
        db.add(doc_type)
    
    db.commit()
    print(f"  ✓ Created {len(DOCUMENT_TYPES)} document types")


def setup_courses(db: Session, rto_id: UUID) -> None:
    """Create or update Course Offerings."""
    print("\nSetting up Course Offerings...")
    
    for course_data in COURSE_OFFERINGS:
        existing = db.query(CourseOffering).filter(
            CourseOffering.course_code == course_data['code'],
            CourseOffering.rto_profile_id == rto_id,
        ).first()
        
        if existing:
            print(f"  ✓ {existing.course_name} ({existing.course_code})")
            continue
        
        course = CourseOffering(
            id=uuid4(),
            rto_profile_id=rto_id,
            course_code=course_data['code'],
            course_name=course_data['name'],
            intake=course_data['intake'],
            campus=course_data['campus'],
            tuition_fee=course_data['tuition_fee'],
            application_deadline=course_data['application_deadline'],
            is_active=True,
        )
        db.add(course)
    
    db.commit()
    print(f"  ✓ Created {len(COURSE_OFFERINGS)} course offerings")


def main():
    """Run admin setup."""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("Churchill Application Portal - Admin Setup")
        print("=" * 60)
        
        # Setup RTO Profile
        rto = setup_rto_profile(db)
        
        # Setup Admin User
        admin_user, admin_staff = setup_admin_user(db, rto.id)
        
        # Setup Document Types
        setup_document_types(db, rto.id)
        
        # Setup Course Offerings
        setup_courses(db, rto.id)
        
        print("\n" + "=" * 60)
        print("✅ Admin Setup Complete!")
        print("=" * 60)
        print("\n📝 Next Steps:")
        print("  1. Login with Admin account:")
        print(f"     Email: {admin_user.email}")
        print("     Password: Admin@123")
        print("\n  2. Change the admin password immediately!")
        print("\n  3. Create agent and staff accounts via admin panel")
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
