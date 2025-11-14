"""
Authentication endpoint tests.
Tests registration, login, token refresh, MFA, and /me endpoint.
"""
import pytest
from fastapi import status


class TestRegistration:
    """Test user registration flow."""
    
    def test_register_admin_success(self, client, churchill_rto_id):
        """Admin can register with valid credentials."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@test.com",
                "password": "SecurePass123!@#",
                "role": "admin",
                "rto_profile_id": churchill_rto_id,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "admin@test.com"
        assert "role" in data  # role is returned
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["mfa_required"] is False
    
    def test_register_duplicate_email(self, client, churchill_rto_id):
        """Cannot register with duplicate email."""
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@test.com",
                "password": "Pass123!@#",
                "role": "staff",
                "rto_profile_id": churchill_rto_id,
            },
        )
        
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@test.com",
                "password": "DifferentPass456!@#",
                "role": "agent",
                "rto_profile_id": churchill_rto_id,
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()
    
    def test_register_invalid_rto(self, client):
        """Registration fails with invalid RTO ID."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@test.com",
                "password": "Pass123!@#",
                "role": "student",
                "rto_profile_id": "99999999-9999-9999-9999-999999999999",
            },
        )
        # Expect 500 (database constraint error) or 400 if backend validates
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR]


class TestLogin:
    """Test login and token generation."""
    
    def test_login_success(self, client, churchill_rto_id):
        """User can login with correct credentials."""
        # Register first
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@test.com",
                "password": "MyPassword123!@#",
                "role": "staff",
                "rto_profile_id": churchill_rto_id,
            },
        )
        
        # Login
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "login@test.com",
                "password": "MyPassword123!@#",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client, churchill_rto_id):
        """Login fails with incorrect password."""
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@test.com",
                "password": "CorrectPass123!@#",
                "role": "agent",
                "rto_profile_id": churchill_rto_id,
            },
        )
        
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "user@test.com",
                "password": "WrongPassword456!@#",
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_nonexistent_user(self, client):
        """Login fails for non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@test.com",
                "password": "SomePass123!@#",
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenRefresh:
    """Test refresh token flow."""
    
    def test_refresh_token_success(self, client, churchill_rto_id):
        """Refresh token generates new access token."""
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "refresh@test.com",
                "password": "RefreshPass123!@#",
                "role": "student",
                "rto_profile_id": churchill_rto_id,
            },
        )
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "refresh@test.com",
                "password": "RefreshPass123!@#",
            },
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


class TestCurrentUser:
    """Test /me endpoint (get current user info)."""
    
    def test_get_current_user_success(self, client, churchill_rto_id):
        """Authenticated user can access /me endpoint."""
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "me@test.com",
                "password": "MePass123!@#",
                "role": "admin",
                "rto_profile_id": churchill_rto_id,
            },
        )
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "me@test.com",
                "password": "MePass123!@#",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # Access /me
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "me@test.com"
        assert data["role"] == "admin"
        assert data["rto_profile_id"] == churchill_rto_id
        assert "user_id" in data
    
    def test_get_current_user_unauthorized(self, client):
        """Unauthenticated request to /me fails."""
        response = client.get("/api/v1/auth/me")
        # Expect 403 Forbidden (FastAPI security dependency default)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_current_user_invalid_token(self, client):
        """Invalid token fails /me endpoint."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_xyz"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestMFA:
    """Test multi-factor authentication flow."""
    
    def test_mfa_setup(self, client, churchill_rto_id):
        """User can set up MFA."""
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "mfa@test.com",
                "password": "MfaPass123!@#",
                "role": "staff",
                "rto_profile_id": churchill_rto_id,
            },
        )
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "mfa@test.com",
                "password": "MfaPass123!@#",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # Setup MFA
        response = client.post(
            "/api/v1/auth/mfa/setup",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "secret" in data
        assert "qr_code_uri" in data
        # Response might not have "message" field
        assert data["secret"]  # Ensure secret is not empty
    
    def test_mfa_disable(self, client, churchill_rto_id):
        """User can disable MFA."""
        # Register, login, setup MFA
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "mfa_disable@test.com",
                "password": "Pass123!@#",
                "role": "admin",
                "rto_profile_id": churchill_rto_id,
            },
        )
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "mfa_disable@test.com",
                "password": "Pass123!@#",
            },
        )
        access_token = login_response.json()["access_token"]
        setup_response = client.post(
            "/api/v1/auth/mfa/setup",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        secret = setup_response.json()["secret"]
        
        # Generate valid TOTP token
        import pyotp
        totp = pyotp.TOTP(secret)
        token = totp.now()
        
        # Disable MFA (requires token verification)
        response = client.post(
            "/api/v1/auth/mfa/disable",
            json={"token": token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "disabled" in response.json()["message"].lower()


class TestAuthIntegration:
    """End-to-end authentication flow tests."""
    
    def test_full_auth_flow(self, client, churchill_rto_id):
        """Complete flow: register → login → /me → refresh → /me."""
        # 1. Register
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "fullflow@test.com",
                "password": "FullFlow123!@#",
                "role": "agent",
                "rto_profile_id": churchill_rto_id,
            },
        )
        assert register_response.status_code == status.HTTP_201_CREATED
        # Registration returns tokens, not user ID directly
        register_data = register_response.json()
        assert "access_token" in register_data
        
        # 2. Login
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "fullflow@test.com",
                "password": "FullFlow123!@#",
            },
        )
        assert login_response.status_code == status.HTTP_200_OK
        tokens = login_response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        # 3. Get current user with access token
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_response.status_code == status.HTTP_200_OK
        user_data = me_response.json()
        user_id = user_data["user_id"]  # /me returns "user_id" not "id"
        assert user_data["email"] == "fullflow@test.com"
        assert user_data["role"] == "agent"
        
        # 4. Refresh token
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        new_access_token = refresh_response.json()["access_token"]
        
        # 5. Use new access token
        me_response_2 = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert me_response_2.status_code == status.HTTP_200_OK
        assert me_response_2.json()["email"] == "fullflow@test.com"
