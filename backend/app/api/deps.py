from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..core.security import get_current_active_user
from ..core.config import get_settings
from ..models.user import UserRole

settings = get_settings()
http_bearer = HTTPBearer(auto_error=False)


def get_active_admin(current_user=Depends(get_current_active_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")
    return current_user


def get_superuser(current_user=Depends(get_current_active_user)):
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser only")
    return current_user


def get_dialer_auth(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)):
    if not credentials or credentials.credentials != settings.dialer_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid dialer token")
    return True


def db_session() -> Session:
    return Depends(get_db)
