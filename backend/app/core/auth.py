"""Authentication and JWT utilities for role-based authorization."""

import datetime
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from app.core.config import settings

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=False)


def create_access_token(username: str, role: str, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """Generate a signed JWT access token containing identity and role claims."""
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
    
    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
        "iat": datetime.datetime.now(datetime.timezone.utc)
    }
    
    encoded_jwt = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token signature expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("JWT token is invalid: %s", e)
        return None


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> dict:
    """Dependency that extracts and verifies Bearer token from Authorization header."""
    # If API Key is not set or we are in a permissive fallback, let dev mode pass
    if not settings.SYNEX_API_KEY:
        return {"sub": "developer", "role": "admin"}

    if not credentials:
        # Fallback check for request headers directly if HTTPBearer failed
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Allow raw SYNEX_API_KEY as a shortcut bearer token for CLI/demo scripts
    if token == settings.SYNEX_API_KEY:
        return {"sub": "sys-admin", "role": "admin"}
        
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or Expired Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return payload


def require_role(required_role: str):
    """Enforce minimum role access for endpoints."""
    # Hierarchy: admin > engineer > viewer
    role_hierarchy = {"viewer": 0, "engineer": 1, "admin": 2}
    
    async def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role", "viewer")
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_level < required_level:
            logger.warning("Access denied: User '%s' has role '%s', required: '%s'", current_user.get("sub"), user_role, required_role)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires '{required_role}' privilege"
            )
        return current_user
        
    return dependency
