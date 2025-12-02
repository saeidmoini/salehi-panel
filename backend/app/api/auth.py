from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..schemas.auth import LoginRequest, Token
from ..core.security import get_current_active_user
from ..schemas.user import AdminUserOut
from ..services import auth_service

router = APIRouter()


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    token = auth_service.authenticate_user(db, payload)
    return Token(access_token=token)


@router.get("/me", response_model=AdminUserOut)
def get_me(current_user=Depends(get_current_active_user)):
    return current_user
