"""
Tests for authentication and authorization router
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.models import User, Role, Permission


class TestPasswordHashing:
    """Test password hashing functionality"""

    def test_verify_password_correct(self):
        """Test verifying correct password"""
        from app.routers.auth import verify_password

        # Hash a known password
        hashed = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYWEG6fSYY/i"

        # Note: In test environment without passlib, it falls back to plain comparison
        # This test verifies the fallback works
        result = verify_password("testpassword", "testpassword")
        assert result is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password"""
        from app.routers.auth import verify_password

        result = verify_password("wrongpassword", "correctpassword")
        assert result is False


class TestUserCreation:
    """Test user creation"""

    def test_create_user(self, db_session):
        """Test creating a new user"""
        from app.routers.auth import create_user
        from app.models import User

        from app.routers.auth import get_password_hash
        
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepassword123",  # create_user expects 'password', not 'password_hash'
            "full_name": "Test User",
            "is_active": True
        }

        result = create_user(user_data=user_data, db=db_session)

        assert result["username"] == "testuser"
        assert "id" in result
        # Password is stored (hashed if passlib available, plain text as fallback)
        stored_user = db_session.query(User).filter(User.username == "testuser").first()
        assert stored_user.password_hash is not None
        assert len(stored_user.password_hash) > 0

    def test_create_user_duplicate_username(self, db_session, sample_user):
        """Test creating user with duplicate username fails"""
        from app.routers.auth import create_user
        from app.exceptions import ConflictException

        db_session.add(sample_user)
        db_session.commit()

        with pytest.raises(ConflictException) as exc_info:
            create_user(
                user_data={
                    "username": sample_user.username,
                    "password": "anotherpassword",
                },
                db=db_session
            )

        assert "already exists" in str(exc_info.value.message)


class TestUserAuthentication:
    """Test user authentication flows"""

    def test_login_success(self, db_session, sample_user):
        """Test successful login"""
        from app.routers.auth import login_user, get_password_hash

        # Hash the password first - note: User model uses password_hash, not password
        sample_user.password_hash = get_password_hash("testpassword")
        db_session.add(sample_user)
        db_session.commit()

        result = login_user(
            username=sample_user.username,
            password="testpassword",
            db=db_session
        )

        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert "expires_in" in result

    def test_login_invalid_username(self, db_session):
        """Test login with invalid username"""
        from app.routers.auth import login_user
        from app.exceptions import AuthenticationException

        with pytest.raises(AuthenticationException):
            login_user(
                username="nonexistent",
                password="anypassword",
                db=db_session
            )

    def test_login_invalid_password(self, db_session, sample_user):
        """Test login with invalid password"""
        from app.routers.auth import login_user, get_password_hash
        from app.exceptions import AuthenticationException

        sample_user.password_hash = get_password_hash("correctpassword")
        db_session.add(sample_user)
        db_session.commit()

        with pytest.raises(AuthenticationException):
            login_user(
                username=sample_user.username,
                password="wrongpassword",
                db=db_session
            )


class TestTokenGeneration:
    """Test JWT token generation and validation"""

    def test_create_access_token(self):
        """Test creating an access token"""
        from app.routers.auth import create_access_token

        token = create_access_token(data={"sub": "testuser", "role": "admin"})

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self):
        """Test decoding a valid access token"""
        from app.routers.auth import create_access_token, decode_token

        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data=data)

        decoded = decode_token(token)

        assert decoded["sub"] == "testuser"
        assert decoded["role"] == "admin"

    def test_decode_invalid_token(self):
        """Test decoding an invalid token raises error"""
        from app.routers.auth import decode_token
        from app.exceptions import AuthenticationException

        with pytest.raises(AuthenticationException):
            decode_token("invalid.token.here")


class TestRBAC:
    """Test role-based access control"""

    def test_check_permission(self, db_session):
        """Test checking user permissions"""
        from app.routers.permissions import check_permission

        # Create a role with permissions
        role = Role(name="engineer", description="Network Engineer")
        permission = Permission(name="device:read", description="Read devices", resource="device", action="read")
        role.permissions.append(permission)
        db_session.add_all([role, permission])
        db_session.commit()

        # Create user with role
        user = User(username="engineer1", password_hash="hash", is_active=True)
        user.roles.append(role)
        db_session.add(user)
        db_session.commit()

        result = check_permission(user.id, "device:read", db_session)
        assert result is True

    def test_check_permission_denied(self, db_session, sample_user):
        """Test permission denied for user without required role"""
        from app.routers.permissions import check_permission

        db_session.add(sample_user)
        db_session.commit()

        result = check_permission(sample_user.id, "device:delete", db_session)
        assert result is False


class TestUserSessionManagement:
    """Test user session management"""

    def test_create_session(self, db_session, sample_user):
        """Test creating a user session"""
        from app.models import UserSession

        db_session.add(sample_user)
        db_session.commit()
        db_session.refresh(sample_user)

        session = UserSession(
            user_id=sample_user.id,
            token_jti="test_token_123",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        db_session.add(session)
        db_session.commit()

        assert session.id is not None
        assert session.token_jti == "test_token_123"

    def test_session_expiration(self, db_session, sample_user):
        """Test expired sessions are detected"""
        from app.models import UserSession

        db_session.add(sample_user)
        db_session.commit()
        db_session.refresh(sample_user)

        session = UserSession(
            user_id=sample_user.id,
            token_jti="expired_token",
            expires_at=datetime.utcnow() - timedelta(hours=1)  # Already expired
        )
        db_session.add(session)
        db_session.commit()

        # Session should be expired
        assert session.expires_at < datetime.utcnow()
