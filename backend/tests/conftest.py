"""
Pytest fixtures for Churchill Application Portal tests.
Provides test database, client, and common test data.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.models import RtoProfile
from uuid import UUID
from datetime import datetime


# Use separate test database in Docker Postgres
# This ensures UUID and JSONB types work correctly
TEST_DB_NAME = "churchill_test"
POSTGRES_USER = os.getenv("POSTGRES_USER", "churchill_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "churchill_dev_password_123")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

SQLALCHEMY_TEST_DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{TEST_DB_NAME}"
)

engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create test database once for entire test session."""
    # Create test database if it doesn't exist
    default_engine = create_engine(
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/postgres"
    )
    with default_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        # Drop and recreate for clean slate
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Seed Churchill RTO
    db = TestingSessionLocal()
    churchill = RtoProfile(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Churchill Education",
        abn="12345678901",
        cricos_code="03089G",
        contact_email="info@churchilleducation.edu.au",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(churchill)
    db.commit()
    db.close()
    
    yield
    
    # Cleanup after all tests (skip if sessions still open)
    try:
        engine.dispose()  # Close all connections first
        Base.metadata.drop_all(bind=engine)
        with default_engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
    except Exception:
        # Ignore cleanup errors (database may still be in use)
        pass


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    db = TestingSessionLocal()
    yield db
    db.rollback()  # Rollback any uncommitted changes
    db.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with test database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def churchill_rto_id():
    """Churchill Education RTO ID for tests."""
    return "00000000-0000-0000-0000-000000000001"


@pytest.fixture(scope="session")
def agent_token_session():
    """Session-scoped agent authentication (create once, reuse)."""
    from app.main import app
    from fastapi.testclient import TestClient
    
    with TestClient(app) as client:
        # Check if agent already exists from another test
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test.agent@agency.com", "password": "AgentPass123!"}
        )
        
        if login_resp.status_code == 200:
            return login_resp.json()["access_token"]
        
        # If login failed, agent doesn't exist - but fixtures will create it
        # This shouldn't happen in session scope
        return None


@pytest.fixture
def agent_token(client, db_session, churchill_rto_id):
    """Create and authenticate an agent user."""
    from app.models import UserAccount, UserRole, UserStatus, AgentProfile
    from app.core.security import get_password_hash
    from uuid import uuid4
    
    # Check if agent already exists
    existing_agent = db_session.query(UserAccount).filter(
        UserAccount.email == "test.agent@agency.com"
    ).first()
    
    if not existing_agent:
        # Create agent user
        agent_user = UserAccount(
            id=uuid4(),
            email="test.agent@agency.com",
            password_hash=get_password_hash("AgentPass123!"),
            role=UserRole.AGENT,
            rto_profile_id=UUID(churchill_rto_id),
            status=UserStatus.ACTIVE
        )
        db_session.add(agent_user)
        db_session.flush()
        
        # Create agent profile
        agent_profile = AgentProfile(
            id=uuid4(),
            user_account_id=agent_user.id,
            agency_name="Test Agency",
            phone="+61 400 000 001",
            commission_rate=15.00
        )
        db_session.add(agent_profile)
        db_session.commit()
    
    # Login and get token
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test.agent@agency.com", "password": "AgentPass123!"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def student_token(client, db_session, churchill_rto_id):
    """Create and authenticate a student user."""
    from app.models import UserAccount, UserRole, UserStatus, StudentProfile
    from app.core.security import get_password_hash
    from uuid import uuid4
    from datetime import date
    
    # Check if student already exists
    existing_student = db_session.query(UserAccount).filter(
        UserAccount.email == "john.doe@example.com"
    ).first()
    
    if not existing_student:
        # Create student user
        student_user = UserAccount(
            id=uuid4(),
            email="john.doe@example.com",
            password_hash=get_password_hash("StudentPass123!"),
            role=UserRole.STUDENT,
            rto_profile_id=UUID(churchill_rto_id),
            status=UserStatus.ACTIVE
        )
        db_session.add(student_user)
        db_session.flush()
        
        # Create student profile
        student_profile = StudentProfile(
            id=uuid4(),
            user_account_id=student_user.id,
            given_name="John",
            family_name="Doe",
            date_of_birth=date(1995, 3, 15),
            passport_number="JD1234567",
            nationality="Australian"
        )
        db_session.add(student_profile)
        db_session.commit()
    
    # Login and get token
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "john.doe@example.com", "password": "StudentPass123!"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def student_id(db_session):
    """Get student profile ID for the test student."""
    from app.models import UserAccount, StudentProfile
    
    user = db_session.query(UserAccount).filter(
        UserAccount.email == "john.doe@example.com"
    ).first()
    
    if user and user.student_profile:
        return str(user.student_profile.id)
    return None


@pytest.fixture
def test_application_id(client, agent_token, student_id, db_session, churchill_rto_id):
    """Create a test application and return its ID."""
    from app.models import CourseOffering
    from uuid import uuid4
    
    # Create course offering
    course = CourseOffering(
        id=uuid4(),
        course_code="TEST101",
        course_name="Test Course 101",
        intake="2025 Semester 1",
        campus="Sydney",
        tuition_fee=20000.00,
        is_active=True
    )
    db_session.add(course)
    db_session.flush()
    
    # Create application
    response = client.post(
        "/api/v1/applications",
        json={
            "student_profile_id": student_id,
            "course_offering_id": str(course.id)
        },
        headers={"Authorization": f"Bearer {agent_token}"}
    )
    assert response.status_code == 201
    return response.json()["application"]["id"]
