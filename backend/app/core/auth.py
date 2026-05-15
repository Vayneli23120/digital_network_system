"""
Authentication module
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


class User:
    """Mock user model for development"""
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get current authenticated user
    In production, this should validate JWT token
    """
    # Mock authentication for development
    # In production, decode and verify JWT token here
    return User(id=1, username="admin", email="admin@example.com")


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Get current active user"""
    return current_user
