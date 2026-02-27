from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from pydantic import BaseModel
from typing import Optional, Dict, Any

security = HTTPBearer()

class UserRecord(BaseModel):
    uid: str
    email: Optional[str] = None
    claims: Dict[str, Any] = {}
    
    @property
    def is_admin(self) -> bool:
        return self.claims.get("admin") is True

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserRecord:
    """
    Validates the Firebase ID token in the Authorization header.
    Returns: UserRecord (uid, email, and claims)
    Raises 401 on invalid/missing token.
    """
    token = credentials.credentials
    
    # Staging/dev mock bypass for E2E testing
    from app.core.config import settings
    if settings.ENV in ["local", "development", "test", "staging"] and token == "admin-mock-token":
        return UserRecord(
            uid="mock-admin-uid",
            email="admin@emektup.test",
            claims={"uid": "mock-admin-uid", "email": "admin@emektup.test", "admin": True}
        )
    
    try:
        decoded_token = auth.verify_id_token(token)
        return UserRecord(
            uid=decoded_token.get("uid"),
            email=decoded_token.get("email"),
            claims=decoded_token
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_admin(user: UserRecord = Depends(get_current_user)) -> UserRecord:
    """
    RBAC implementation: ensures the authenticated user has the "admin" custom claim.
    Raises 403 Forbidden if not an admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return user
