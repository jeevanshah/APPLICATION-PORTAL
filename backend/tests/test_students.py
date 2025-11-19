"""
Test student profile management and application tracking endpoints.

Test workflow:
1. Agent creates student profile with credentials
2. Agent creates application for student
3. Student logs in with provided credentials
4. Student views dashboard (sees applications and stats)
5. Student tracks specific application (sees detailed progress)
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    UserAccount, UserRole, UserStatus, AgentProfile, StudentProfile,
    CourseOffering, Application, ApplicationStage
)


class TestAgentCreatesStudent:
    """Test agent creating student profiles."""
    
    def test_agent_creates_student_profile(self, client: TestClient, agent_token: str, db_session):
        """Agent successfully creates a student profile with login credentials."""
        student_data = {
            "email": "test.student@example.com",
            "password": "StudentPass123!",
            "given_name": "Test",
            "family_name": "Student",
            "date_of_birth": "1998-05-15",
            "passport_number": "TS1234567",
            "nationality": "Nepalese",
            "visa_type": "Student Visa (Subclass 500)",
            "phone": "+61 400 111 222",
            "address": "123 Test St, Sydney NSW 2000"
        }
        
        response = client.post(
            "/api/v1/students",
            json=student_data,
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert data["email"] == "test.student@example.com"
        assert data["given_name"] == "Test"
        assert data["family_name"] == "Student"
        assert data["passport_number"] == "TS1234567"
        assert data["status"] == "active"
        assert "id" in data
        assert "user_account_id" in data
        
        # Verify user account was created in database
        user = db_session.query(UserAccount).filter(
            UserAccount.email == "test.student@example.com"
        ).first()
        
        assert user is not None
        assert user.role == UserRole.STUDENT
        assert user.status == UserStatus.ACTIVE
        
        # Verify student profile was created
        student_profile = db_session.query(StudentProfile).filter(
            StudentProfile.user_account_id == user.id
        ).first()
        
        assert student_profile is not None
        assert student_profile.given_name == "Test"
        assert student_profile.family_name == "Student"
    
    def test_student_cannot_create_student_profile(self, client: TestClient, student_token: str):
        """Students cannot create other student profiles."""
        student_data = {
            "email": "another.student@example.com",
            "password": "AnotherPass123!",
            "given_name": "Another",
            "family_name": "Student",
            "date_of_birth": "1999-06-20"
        }
        
        response = client.post(
            "/api/v1/students",
            json=student_data,
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        assert response.status_code == 403
        assert "Only agents and staff" in response.json()["detail"]
    
    def test_duplicate_email_rejected(self, client: TestClient, agent_token: str, db_session):
        """Creating student with existing email is rejected."""
        # Create first student
        student_data = {
            "email": "duplicate@example.com",
            "password": "Pass123!",
            "given_name": "First",
            "family_name": "Student",
            "date_of_birth": "1998-01-01"
        }
        
        response1 = client.post(
            "/api/v1/students",
            json=student_data,
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert response1.status_code == 201
        
        # Try to create second student with same email
        student_data["given_name"] = "Second"
        response2 = client.post(
            "/api/v1/students",
            json=student_data,
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]


class TestStudentLogin:
    """Test student login with agent-created credentials."""
    
    def test_student_logs_in_with_credentials(self, client: TestClient, agent_token: str, db_session):
        """Student can log in using credentials created by agent."""
        # Agent creates student
        student_data = {
            "email": "login.test@example.com",
            "password": "LoginTest123!",
            "given_name": "Login",
            "family_name": "Test",
            "date_of_birth": "1997-07-07"
        }
        
        create_response = client.post(
            "/api/v1/students",
            json=student_data,
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert create_response.status_code == 201
        
        # Student logs in
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "login.test@example.com",
                "password": "LoginTest123!"
            }
        )
        
        assert login_response.status_code == 200
        data = login_response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["role"] == "student"
        assert data["email"] == "login.test@example.com"


class TestStudentDashboard:
    """Test student dashboard endpoint."""
    
    def test_student_views_dashboard(
        self, 
        client: TestClient, 
        student_token: str, 
        student_id: str,
        db_session
    ):
        """Student can view their dashboard with applications and statistics."""
        response = client.get(
            "/api/v1/students/me/dashboard",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "student" in data
        assert "applications" in data
        assert "recent_activity" in data
        assert "statistics" in data
        
        # Verify student information
        assert data["student"]["email"] == "john.doe@example.com"
        
        # Verify statistics structure
        stats = data["statistics"]
        assert "total_applications" in stats
        assert "draft_count" in stats
        assert "submitted_count" in stats
        assert "in_review_count" in stats
        assert "offers_count" in stats
        assert "enrolled_count" in stats
    
    def test_agent_cannot_view_student_dashboard(self, client: TestClient, agent_token: str):
        """Agents cannot access student dashboard endpoint."""
        response = client.get(
            "/api/v1/students/me/dashboard",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        
        assert response.status_code == 403
        assert "Only students" in response.json()["detail"]
    
    def test_dashboard_shows_applications(
        self,
        client: TestClient,
        agent_token: str,
        db_session,
        churchill_rto_id: str
    ):
        """Dashboard shows all applications for the student."""
        # Agent creates student
        student_resp = client.post(
            "/api/v1/students",
            json={
                "email": "multi.app@example.com",
                "password": "MultiApp123!",
                "given_name": "Multi",
                "family_name": "App",
                "date_of_birth": "1996-03-03"
            },
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert student_resp.status_code == 201
        student_data = student_resp.json()
        
        # Student logs in
        login_resp = client.post(
            "/api/v1/auth/login",
            data={"username": "multi.app@example.com", "password": "MultiApp123!"}
        )
        assert login_resp.status_code == 200
        student_token = login_resp.json()["access_token"]
        
        # Create course offerings
        from uuid import UUID, uuid4
        course1 = CourseOffering(
            id=uuid4(),
            course_code="TEST001",
            course_name="Test Course 1",
            intake="2025 Semester 1",
            campus="Sydney",
            tuition_fee=20000.00,
            is_active=True
        )
        course2 = CourseOffering(
            id=uuid4(),
            course_code="TEST002",
            course_name="Test Course 2",
            intake="2025 Semester 2",
            campus="Melbourne",
            tuition_fee=25000.00,
            is_active=True
        )
        db_session.add_all([course1, course2])
        db_session.flush()
        
        # Agent creates 2 applications for student
        student_profile_id = student_data["id"]
        
        app1_resp = client.post(
            "/api/v1/applications",
            json={
                "student_profile_id": student_profile_id,
                "course_offering_id": str(course1.id)
            },
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert app1_resp.status_code == 201
        
        app2_resp = client.post(
            "/api/v1/applications",
            json={
                "student_profile_id": student_profile_id,
                "course_offering_id": str(course2.id)
            },
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert app2_resp.status_code == 201
        
        # Student views dashboard
        dashboard_resp = client.get(
            "/api/v1/students/me/dashboard",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        assert dashboard_resp.status_code == 200
        dashboard = dashboard_resp.json()
        
        # Should see both applications
        assert len(dashboard["applications"]) == 2
        assert dashboard["statistics"]["total_applications"] == 2
        assert dashboard["statistics"]["draft_count"] == 2  # Both are drafts initially
        
        # Verify application details
        app_courses = [app["course_code"] for app in dashboard["applications"]]
        assert "TEST001" in app_courses
        assert "TEST002" in app_courses


class TestApplicationTracking:
    """Test student application tracking endpoint."""
    
    def test_student_tracks_own_application(
        self,
        client: TestClient,
        student_token: str,
        test_application_id: str
    ):
        """Student can view detailed tracking for their application."""
        response = client.get(
            f"/api/v1/students/me/applications/{test_application_id}/track",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify tracking details
        assert data["id"] == test_application_id
        assert "course_code" in data
        assert "course_name" in data
        assert "current_stage" in data
        assert "completion_percentage" in data
        
        # Verify progress tracking
        assert "stage_progress" in data
        assert isinstance(data["stage_progress"], list)
        assert len(data["stage_progress"]) > 0
        
        # Verify required documents
        assert "required_documents" in data
        assert isinstance(data["required_documents"], list)
        
        # Verify timeline
        assert "timeline" in data
        assert isinstance(data["timeline"], list)
        
        # Verify next steps
        assert "next_steps" in data
        assert isinstance(data["next_steps"], list)
        assert len(data["next_steps"]) > 0
    
    def test_student_cannot_track_others_application(
        self,
        client: TestClient,
        agent_token: str,
        db_session,
        churchill_rto_id: str
    ):
        """Student cannot track applications belonging to other students."""
        # Create two students
        student1_resp = client.post(
            "/api/v1/students",
            json={
                "email": "student1@example.com",
                "password": "Student1Pass!",
                "given_name": "Student",
                "family_name": "One",
                "date_of_birth": "1997-01-01"
            },
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        student1_data = student1_resp.json()
        
        student2_resp = client.post(
            "/api/v1/students",
            json={
                "email": "student2@example.com",
                "password": "Student2Pass!",
                "given_name": "Student",
                "family_name": "Two",
                "date_of_birth": "1997-02-02"
            },
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        student2_data = student2_resp.json()
        
        # Create course
        from uuid import uuid4
        course = CourseOffering(
            id=uuid4(),
            course_code="TRACK001",
            course_name="Track Test Course",
            intake="2025 Semester 1",
            campus="Sydney",
            tuition_fee=20000.00,
            is_active=True
        )
        db_session.add(course)
        db_session.flush()
        
        # Create application for student1
        app_resp = client.post(
            "/api/v1/applications",
            json={
                "student_profile_id": student1_data["id"],
                "course_offering_id": str(course.id)
            },
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        app_data = app_resp.json()
        app_id = app_data["application"]["id"]
        
        # Student2 logs in
        login_resp = client.post(
            "/api/v1/auth/login",
            data={"username": "student2@example.com", "password": "Student2Pass!"}
        )
        student2_token = login_resp.json()["access_token"]
        
        # Student2 tries to track student1's application
        track_resp = client.get(
            f"/api/v1/students/me/applications/{app_id}/track",
            headers={"Authorization": f"Bearer {student2_token}"}
        )
        
        assert track_resp.status_code == 404
        assert "not found" in track_resp.json()["detail"].lower()
    
    def test_tracking_shows_next_steps(
        self,
        client: TestClient,
        agent_token: str,
        db_session,
        churchill_rto_id: str
    ):
        """Application tracking shows relevant next steps based on stage."""
        # Create student and log them in
        student_resp = client.post(
            "/api/v1/students",
            json={
                "email": "nextsteps@example.com",
                "password": "NextSteps123!",
                "given_name": "Next",
                "family_name": "Steps",
                "date_of_birth": "1996-06-06"
            },
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        student_data = student_resp.json()
        
        login_resp = client.post(
            "/api/v1/auth/login",
            data={"username": "nextsteps@example.com", "password": "NextSteps123!"}
        )
        student_token = login_resp.json()["access_token"]
        
        # Create course and application
        from uuid import uuid4
        course = CourseOffering(
            id=uuid4(),
            course_code="NEXT001",
            course_name="Next Steps Course",
            intake="2025 Semester 1",
            campus="Sydney",
            tuition_fee=20000.00,
            is_active=True
        )
        db_session.add(course)
        db_session.flush()
        
        app_resp = client.post(
            "/api/v1/applications",
            json={
                "student_profile_id": student_data["id"],
                "course_offering_id": str(course.id)
            },
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        app_id = app_resp.json()["application"]["id"]
        
        # Track application (should be in DRAFT stage)
        track_resp = client.get(
            f"/api/v1/students/me/applications/{app_id}/track",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        assert track_resp.status_code == 200
        data = track_resp.json()
        
        # Verify next steps for DRAFT stage
        assert data["current_stage"] == "draft"
        assert len(data["next_steps"]) > 0
        
        # Should include message about completing and submitting application
        next_steps_text = " ".join(data["next_steps"]).lower()
        assert "complete" in next_steps_text or "submit" in next_steps_text


class TestStudentProfileUpdate:
    """Test student updating their own profile."""
    
    def test_student_updates_own_profile(self, client: TestClient, student_token: str):
        """Student can update their own profile information."""
        update_data = {
            "phone": "+61 400 999 888",
            "address": "456 New Address, Melbourne VIC 3000",
            "visa_type": "Student Visa (Subclass 500) - Extended"
        }
        
        response = client.patch(
            "/api/v1/students/me",
            json=update_data,
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["phone"] == "+61 400 999 888"
        assert data["address"] == "456 New Address, Melbourne VIC 3000"
        assert data["visa_type"] == "Student Visa (Subclass 500) - Extended"
        
        # Other fields should remain unchanged
        assert data["given_name"] == "John"
        assert data["family_name"] == "Doe"
    
    def test_agent_cannot_update_via_student_endpoint(self, client: TestClient, agent_token: str):
        """Agents cannot use the student profile update endpoint."""
        response = client.patch(
            "/api/v1/students/me",
            json={"phone": "+61 400 000 000"},
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        
        assert response.status_code == 403


class TestStudentList:
    """Test listing students (for agents/staff)."""
    
    def test_agent_lists_students(self, client: TestClient, agent_token: str, db_session):
        """Agent can list students they have created applications for."""
        response = client.get(
            "/api/v1/students",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "students" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["students"], list)
    
    def test_student_cannot_list_students(self, client: TestClient, student_token: str):
        """Students cannot list other students."""
        response = client.get(
            "/api/v1/students",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        
        assert response.status_code == 403
    
    def test_student_list_pagination(self, client: TestClient, agent_token: str):
        """Student list supports pagination."""
        response = client.get(
            "/api/v1/students?page=1&page_size=10",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["page_size"] == 10
