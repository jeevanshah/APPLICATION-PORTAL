"""
Test Application CRUD endpoints with draft/resume workflow.
"""
import pytest
from fastapi import status
from uuid import UUID


class TestApplicationDraftWorkflow:
    """Test draft creation, auto-save, and submit workflow."""
    
    def test_create_draft_as_student(self, client, churchill_rto_id, db_session):
        """Student can create draft application."""
        from app.models import StudentProfile, CourseOffering, UserAccount, UserRole
        from datetime import date
        
        # Create student user and profile
        student_user = UserAccount(
            email="student@test.com",
            password_hash="hash",
            role=UserRole.STUDENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(student_user)
        db_session.commit()
        
        student_profile = StudentProfile(
            user_account_id=student_user.id,
            given_name="John",
            family_name="Doe",
            date_of_birth=date(2000, 1, 1),
            nationality="Australia"
        )
        db_session.add(student_profile)
        
        # Create course
        course = CourseOffering(
            course_code="CERT4-IT",
            course_name="Certificate IV in Information Technology",
            intake="2025 Semester 1",
            campus="Brisbane",
            tuition_fee=10000.00
        )
        db_session.add(course)
        db_session.commit()
        
        # Create token for student (skip login since we don't have valid password hash)
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(student_user.id), "email": student_user.email, "role": "student"})
        
        # Create draft application
        response = client.post(
            "/api/v1/applications",
            json={"course_offering_id": str(course.id)},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "application" in data
        assert data["application"]["current_stage"] == "draft"
        assert "form_metadata" in data["application"]
        assert data["application"]["form_metadata"]["completed_sections"] == []
        
        app_id = data["application"]["id"]
        
        # Auto-save: Update emergency contacts
        update_response = client.patch(
            f"/api/v1/applications/{app_id}",
            json={
                "emergency_contacts": [
                    {
                        "name": "Jane Doe",
                        "relationship": "Mother",
                        "phone": "+61400000000",
                        "is_primary": True
                    }
                ]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert update_response.status_code == status.HTTP_200_OK
        update_data = update_response.json()
        assert len(update_data["application"]["emergency_contacts"]) == 1
        assert update_data["application"]["form_metadata"]["auto_save_count"] == 1
    
    def test_cannot_update_submitted_application(self, client, churchill_rto_id, db_session):
        """Cannot update application after it's submitted."""
        from app.models import Application, ApplicationStage, StudentProfile, CourseOffering, UserAccount, UserRole
        from datetime import date
        
        # Create test data
        student_user = UserAccount(
            email="student2@test.com",
            password_hash="hash",
            role=UserRole.STUDENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(student_user)
        db_session.commit()
        
        student_profile = StudentProfile(
            user_account_id=student_user.id,
            given_name="Alice",
            family_name="Smith",
            date_of_birth=date(1999, 5, 10),
            nationality="Australia"
        )
        db_session.add(student_profile)
        
        course = CourseOffering(
            course_code="DIP-BUS",
            course_name="Diploma of Business",
            intake="2025 Semester 2",
            campus="Sydney",
            tuition_fee=12000.00
        )
        db_session.add(course)
        db_session.commit()
        
        # Create submitted application
        app = Application(
            student_profile_id=student_profile.id,
            course_offering_id=course.id,
            current_stage=ApplicationStage.SUBMITTED
        )
        db_session.add(app)
        db_session.commit()
        
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(student_user.id)})
        
        # Try to update
        response = client.patch(
            f"/api/v1/applications/{app.id}",
            json={"usi": "ABC123XYZ"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot update application" in response.json()["detail"]
    
    def test_list_applications_as_student(self, client, churchill_rto_id, db_session):
        """Student sees only their own applications."""
        from app.models import Application, ApplicationStage, StudentProfile, CourseOffering, UserAccount, UserRole
        from datetime import date
        
        # Create two students
        student1_user = UserAccount(
            email="student1@list.com",
            password_hash="hash",
            role=UserRole.STUDENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(student1_user)
        db_session.commit()
        
        student1_profile = StudentProfile(
            user_account_id=student1_user.id,
            given_name="Bob",
            family_name="Brown",
            date_of_birth=date(2001, 3, 15),
            nationality="Australia"
        )
        db_session.add(student1_profile)
        
        student2_user = UserAccount(
            email="student2@list.com",
            password_hash="hash",
            role=UserRole.STUDENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(student2_user)
        db_session.commit()
        
        student2_profile = StudentProfile(
            user_account_id=student2_user.id,
            given_name="Charlie",
            family_name="Chen",
            date_of_birth=date(2002, 7, 20),
            nationality="China"
        )
        db_session.add(student2_profile)
        
        course = CourseOffering(
            course_code="CERT3-ACC",
            course_name="Certificate III in Accounting",
            intake="2025 Semester 1",
            campus="Melbourne",
            tuition_fee=8000.00
        )
        db_session.add(course)
        db_session.commit()
        
        # Create applications for both students
        app1 = Application(
            student_profile_id=student1_profile.id,
            course_offering_id=course.id,
            current_stage=ApplicationStage.DRAFT
        )
        app2 = Application(
            student_profile_id=student2_profile.id,
            course_offering_id=course.id,
            current_stage=ApplicationStage.DRAFT
        )
        db_session.add_all([app1, app2])
        db_session.commit()
        
        # Student1 logs in and lists applications
        from app.core.security import create_access_token
        token1 = create_access_token({"sub": str(student1_user.id)})
        
        response = client.get(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {token1}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1  # Only sees their own application
        assert data[0]["id"] == str(app1.id)


class TestApplicationSubmit:
    """Test application submission and validation."""
    
    def test_submit_incomplete_application_fails(self, client, churchill_rto_id, db_session):
        """Cannot submit application without required fields."""
        from app.models import Application, ApplicationStage, StudentProfile, CourseOffering, UserAccount, UserRole
        from datetime import date
        
        student_user = UserAccount(
            email="incomplete@test.com",
            password_hash="hash",
            role=UserRole.STUDENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(student_user)
        db_session.commit()
        
        student_profile = StudentProfile(
            user_account_id=student_user.id,
            given_name="Test",
            family_name="User",
            date_of_birth=date(2000, 1, 1),
            nationality="Australia"
        )
        db_session.add(student_profile)
        
        course = CourseOffering(
            course_code="TEST-101",
            course_name="Test Course",
            intake="2025",
            campus="Test",
            tuition_fee=1000.00
        )
        db_session.add(course)
        db_session.commit()
        
        # Create draft without required fields
        app = Application(
            student_profile_id=student_profile.id,
            course_offering_id=course.id,
            current_stage=ApplicationStage.DRAFT
        )
        db_session.add(app)
        db_session.commit()
        
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(student_user.id)})
        
        # Try to submit
        response = client.post(
            f"/api/v1/applications/{app.id}/submit",
            json={"confirm_accuracy": True},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Validation failed" in response.json()["detail"]
        assert "Emergency contacts required" in response.json()["detail"]
