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
