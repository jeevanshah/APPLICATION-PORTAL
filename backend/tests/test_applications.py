"""
Test Application CRUD endpoints with agent-centric workflow.

CRITICAL WORKFLOW:
- Agents create applications on behalf of students
- Agents fill the entire application form
- Agents submit applications
- Students have READ-ONLY access (except for signing offers later)
"""
import pytest
from fastapi import status
from uuid import UUID


class TestApplicationAgentWorkflow:
    """Test agent creating, editing, and submitting applications."""
    
    def test_agent_creates_application(self, client, churchill_rto_id, db_session):
        """Agent can create draft application for student."""
        from app.models import StudentProfile, CourseOffering, UserAccount, UserRole, AgentProfile
        from datetime import date
        
        # Create agent user and profile
        agent_user = UserAccount(
            email="agent@test.com",
            password_hash="hash",
            role=UserRole.AGENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(agent_user)
        db_session.commit()
        
        agent_profile = AgentProfile(
            user_account_id=agent_user.id,
            agency_name="Test Agency",
            phone="+61400000001"
        )
        db_session.add(agent_profile)
        db_session.commit()
        
        # Create student profile
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
        
        # Agent creates application
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(agent_user.id), "email": agent_user.email, "role": "agent"})
        
        response = client.post(
            "/api/v1/applications",
            json={
                "course_offering_id": str(course.id),
                "student_profile_id": str(student_profile.id),
                "agent_profile_id": str(agent_profile.id)
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "application" in data
        assert data["application"]["current_stage"] == "draft"
        assert data["application"]["student_profile_id"] == str(student_profile.id)
        assert data["application"]["agent_profile_id"] == str(agent_profile.id)
    
    def test_agent_updates_application(self, client, churchill_rto_id, db_session):
        """Agent can update application they created."""
        from app.models import Application, ApplicationStage, StudentProfile, CourseOffering, UserAccount, UserRole, AgentProfile
        from datetime import date
        
        # Create agent
        agent_user = UserAccount(
            email="agent2@test.com",
            password_hash="hash",
            role=UserRole.AGENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(agent_user)
        db_session.commit()
        
        agent_profile = AgentProfile(
            user_account_id=agent_user.id,
            agency_name="Test Agency 2",
            phone="+61400000002"
        )
        db_session.add(agent_profile)
        db_session.commit()
        
        # Create student
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
        
        # Create draft application
        app = Application(
            student_profile_id=student_profile.id,
            agent_profile_id=agent_profile.id,
            course_offering_id=course.id,
            current_stage=ApplicationStage.DRAFT
        )
        db_session.add(app)
        db_session.commit()
        
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(agent_user.id), "email": agent_user.email, "role": "agent"})
        
        # Agent updates application
        response = client.patch(
            f"/api/v1/applications/{app.id}",
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
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["application"]["emergency_contacts"]) == 1
        assert data["application"]["form_metadata"]["auto_save_count"] == 1
    
    def test_agent_submits_application(self, client, churchill_rto_id, db_session):
        """Agent can submit completed application."""
        from app.models import Application, ApplicationStage, StudentProfile, CourseOffering, UserAccount, UserRole, AgentProfile
        from datetime import date
        
        # Create agent
        agent_user = UserAccount(
            email="agent3@test.com",
            password_hash="hash",
            role=UserRole.AGENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(agent_user)
        db_session.commit()
        
        agent_profile = AgentProfile(
            user_account_id=agent_user.id,
            agency_name="Test Agency 3",
            phone="+61400000003"
        )
        db_session.add(agent_profile)
        db_session.commit()
        
        # Create student
        student_user = UserAccount(
            email="student3@test.com",
            password_hash="hash",
            role=UserRole.STUDENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(student_user)
        db_session.commit()
        
        student_profile = StudentProfile(
            user_account_id=student_user.id,
            given_name="Bob",
            family_name="Brown",
            date_of_birth=date(2001, 3, 15),
            nationality="Australia"
        )
        db_session.add(student_profile)
        
        course = CourseOffering(
            course_code="CERT3-ACC",
            course_name="Certificate III in Accounting",
            intake="2025 Semester 1",
            campus="Melbourne",
            tuition_fee=8000.00
        )
        db_session.add(course)
        db_session.commit()
        
        # Create complete draft application
        app = Application(
            student_profile_id=student_profile.id,
            agent_profile_id=agent_profile.id,
            course_offering_id=course.id,
            current_stage=ApplicationStage.DRAFT,
            emergency_contacts=[{"name": "Test", "relationship": "Parent", "phone": "+61400000000", "is_primary": True}],
            health_cover_policy={
                "provider": "OSHC",
                "policy_number": "12345",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "coverage_type": "OSHC"
            },
            language_cultural_data={
                "english_proficiency": "native",
                "first_language": "English",
                "country_of_birth": "Australia",
                "citizenship_status": "Citizen"
            }
        )
        db_session.add(app)
        db_session.commit()
        
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(agent_user.id), "email": agent_user.email, "role": "agent"})
        
        # Agent submits application
        response = client.post(
            f"/api/v1/applications/{app.id}/submit",
            json={"confirm_accuracy": True},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["application"]["current_stage"] == "submitted"


class TestStudentReadOnlyAccess:
    """Test that students CANNOT create, edit, or submit applications."""
    
    def test_student_cannot_create_application(self, client, churchill_rto_id, db_session):
        """Students cannot create applications - 403 Forbidden."""
        from app.models import StudentProfile, CourseOffering, UserAccount, UserRole
        from datetime import date
        
        # Create student
        student_user = UserAccount(
            email="blocked@test.com",
            password_hash="hash",
            role=UserRole.STUDENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(student_user)
        db_session.commit()
        
        student_profile = StudentProfile(
            user_account_id=student_user.id,
            given_name="Blocked",
            family_name="Student",
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
        
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(student_user.id), "email": student_user.email, "role": "student"})
        
        # Try to create application
        response = client.post(
            "/api/v1/applications",
            json={
                "course_offering_id": str(course.id),
                "student_profile_id": str(student_profile.id)
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Students cannot create applications" in response.json()["detail"]
    
    def test_student_cannot_edit_application(self, client, churchill_rto_id, db_session):
        """Students cannot edit applications - 403 Forbidden."""
        from app.models import Application, ApplicationStage, StudentProfile, CourseOffering, UserAccount, UserRole, AgentProfile
        from datetime import date
        
        # Create agent
        agent_user = UserAccount(
            email="agent_edit@test.com",
            password_hash="hash",
            role=UserRole.AGENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(agent_user)
        db_session.commit()
        
        agent_profile = AgentProfile(
            user_account_id=agent_user.id,
            agency_name="Edit Agency",
            phone="+61400000010"
        )
        db_session.add(agent_profile)
        db_session.commit()
        
        # Create student
        student_user = UserAccount(
            email="blocked_edit@test.com",
            password_hash="hash",
            role=UserRole.STUDENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(student_user)
        db_session.commit()
        
        student_profile = StudentProfile(
            user_account_id=student_user.id,
            given_name="Edit",
            family_name="Blocked",
            date_of_birth=date(2000, 1, 1),
            nationality="Australia"
        )
        db_session.add(student_profile)
        
        course = CourseOffering(
            course_code="EDIT-101",
            course_name="Edit Test",
            intake="2025",
            campus="Test",
            tuition_fee=1000.00
        )
        db_session.add(course)
        db_session.commit()
        
        # Create application by agent
        app = Application(
            student_profile_id=student_profile.id,
            agent_profile_id=agent_profile.id,
            course_offering_id=course.id,
            current_stage=ApplicationStage.DRAFT
        )
        db_session.add(app)
        db_session.commit()
        
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(student_user.id), "email": student_user.email, "role": "student"})
        
        # Try to edit
        response = client.patch(
            f"/api/v1/applications/{app.id}",
            json={"usi": "ABC123XYZ"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Students cannot edit applications" in response.json()["detail"]
    
    def test_student_cannot_submit_application(self, client, churchill_rto_id, db_session):
        """Students cannot submit applications - 403 Forbidden."""
        from app.models import Application, ApplicationStage, StudentProfile, CourseOffering, UserAccount, UserRole, AgentProfile
        from datetime import date
        
        # Create agent
        agent_user = UserAccount(
            email="agent_submit@test.com",
            password_hash="hash",
            role=UserRole.AGENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(agent_user)
        db_session.commit()
        
        agent_profile = AgentProfile(
            user_account_id=agent_user.id,
            agency_name="Submit Agency",
            phone="+61400000020"
        )
        db_session.add(agent_profile)
        db_session.commit()
        
        # Create student
        student_user = UserAccount(
            email="blocked_submit@test.com",
            password_hash="hash",
            role=UserRole.STUDENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(student_user)
        db_session.commit()
        
        student_profile = StudentProfile(
            user_account_id=student_user.id,
            given_name="Submit",
            family_name="Blocked",
            date_of_birth=date(2000, 1, 1),
            nationality="Australia"
        )
        db_session.add(student_profile)
        
        course = CourseOffering(
            course_code="SUBMIT-101",
            course_name="Submit Test",
            intake="2025",
            campus="Test",
            tuition_fee=1000.00
        )
        db_session.add(course)
        db_session.commit()
        
        # Create complete draft by agent
        app = Application(
            student_profile_id=student_profile.id,
            agent_profile_id=agent_profile.id,
            course_offering_id=course.id,
            current_stage=ApplicationStage.DRAFT,
            emergency_contacts=[{"name": "Test", "relationship": "Parent", "phone": "+61400000000", "is_primary": True}],
            health_cover_policy={
                "provider": "OSHC",
                "policy_number": "12345",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "coverage_type": "OSHC"
            },
            language_cultural_data={
                "english_proficiency": "native",
                "first_language": "English",
                "country_of_birth": "Australia",
                "citizenship_status": "Citizen"
            }
        )
        db_session.add(app)
        db_session.commit()
        
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(student_user.id), "email": student_user.email, "role": "student"})
        
        # Try to submit
        response = client.post(
            f"/api/v1/applications/{app.id}/submit",
            json={"confirm_accuracy": True},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Students cannot submit applications" in response.json()["detail"]


class TestApplicationPermissions:
    """Test permission boundaries for different roles."""
    
    def test_agent_cannot_edit_other_agents_application(self, client, churchill_rto_id, db_session):
        """Agent can only edit their own applications."""
        from app.models import Application, ApplicationStage, StudentProfile, CourseOffering, UserAccount, UserRole, AgentProfile
        from datetime import date
        
        # Create two agents
        agent1_user = UserAccount(
            email="agent1_perm@test.com",
            password_hash="hash",
            role=UserRole.AGENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(agent1_user)
        db_session.commit()
        
        agent1_profile = AgentProfile(
            user_account_id=agent1_user.id,
            agency_name="Agency 1",
            phone="+61400000001"
        )
        db_session.add(agent1_profile)
        
        agent2_user = UserAccount(
            email="agent2_perm@test.com",
            password_hash="hash",
            role=UserRole.AGENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(agent2_user)
        db_session.commit()
        
        agent2_profile = AgentProfile(
            user_account_id=agent2_user.id,
            agency_name="Agency 2",
            phone="+61400000002"
        )
        db_session.add(agent2_profile)
        db_session.commit()
        
        # Create student
        student_user = UserAccount(
            email="student_perm@test.com",
            password_hash="hash",
            role=UserRole.STUDENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(student_user)
        db_session.commit()
        
        student_profile = StudentProfile(
            user_account_id=student_user.id,
            given_name="Perm",
            family_name="Test",
            date_of_birth=date(2000, 1, 1),
            nationality="Australia"
        )
        db_session.add(student_profile)
        
        course = CourseOffering(
            course_code="PERM-101",
            course_name="Permission Test",
            intake="2025",
            campus="Test",
            tuition_fee=1000.00
        )
        db_session.add(course)
        db_session.commit()
        
        # Agent 1 creates application
        app = Application(
            student_profile_id=student_profile.id,
            agent_profile_id=agent1_profile.id,
            course_offering_id=course.id,
            current_stage=ApplicationStage.DRAFT
        )
        db_session.add(app)
        db_session.commit()
        
        from app.core.security import create_access_token
        token2 = create_access_token({"sub": str(agent2_user.id), "email": agent2_user.email, "role": "agent"})
        
        # Agent 2 tries to edit Agent 1's application
        response = client.patch(
            f"/api/v1/applications/{app.id}",
            json={"usi": "ABC123XYZ"},
            headers={"Authorization": f"Bearer {token2}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Agents can only edit their own applications" in response.json()["detail"]
    
    def test_cannot_update_submitted_application(self, client, churchill_rto_id, db_session):
        """Cannot update application after it's submitted."""
        from app.models import Application, ApplicationStage, StudentProfile, CourseOffering, UserAccount, UserRole, AgentProfile
        from datetime import date
        
        # Create agent
        agent_user = UserAccount(
            email="agent_submitted@test.com",
            password_hash="hash",
            role=UserRole.AGENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(agent_user)
        db_session.commit()
        
        agent_profile = AgentProfile(
            user_account_id=agent_user.id,
            agency_name="Submitted Agency",
            phone="+61400000030"
        )
        db_session.add(agent_profile)
        db_session.commit()
        
        # Create student
        student_user = UserAccount(
            email="student_submitted@test.com",
            password_hash="hash",
            role=UserRole.STUDENT,
            rto_profile_id=UUID(churchill_rto_id),
            status="active"
        )
        db_session.add(student_user)
        db_session.commit()
        
        student_profile = StudentProfile(
            user_account_id=student_user.id,
            given_name="Submitted",
            family_name="Test",
            date_of_birth=date(1999, 5, 10),
            nationality="Australia"
        )
        db_session.add(student_profile)
        
        course = CourseOffering(
            course_code="SUBMITTED-101",
            course_name="Submitted Test",
            intake="2025",
            campus="Test",
            tuition_fee=1000.00
        )
        db_session.add(course)
        db_session.commit()
        
        # Create submitted application
        app = Application(
            student_profile_id=student_profile.id,
            agent_profile_id=agent_profile.id,
            course_offering_id=course.id,
            current_stage=ApplicationStage.SUBMITTED
        )
        db_session.add(app)
        db_session.commit()
        
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(agent_user.id), "email": agent_user.email, "role": "agent"})
        
        # Try to update
        response = client.patch(
            f"/api/v1/applications/{app.id}",
            json={"usi": "ABC123XYZ"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot update application" in response.json()["detail"]
