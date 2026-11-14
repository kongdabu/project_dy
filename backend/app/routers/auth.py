from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from app.config import settings
from app.services.auth_service import (
    create_access_token,
    verify_access_token,
    verify_passcode,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    passcode: str


@router.get("/status")
def auth_status(authorization: Optional[str] = Header(default=None)):
    """인증 활성화 여부 및 현재 토큰 유효성 확인"""
    if not settings.is_auth_enabled:
        return {"auth_required": False, "authenticated": True}

    raw_token = ""
    if authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization[7:].strip()

    return {
        "auth_required": True,
        "authenticated": bool(raw_token and verify_access_token(raw_token)),
    }


@router.post("/login")
def login(body: LoginRequest):
    """패스코드 검증 후 서명된 세션 토큰 발급"""
    if not settings.is_auth_enabled:
        return {"access_token": "", "token_type": "bearer", "auth_required": False}

    if not verify_passcode(body.passcode):
        raise HTTPException(status_code=401, detail="패스코드가 올바르지 않습니다.")

    return {
        "access_token": create_access_token(),
        "token_type": "bearer",
        "auth_required": True,
    }

