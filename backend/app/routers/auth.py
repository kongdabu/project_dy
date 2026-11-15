from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
from app.config import settings
from app.services.auth_service import (
    create_access_token,
    login_rate_limiter,
    verify_access_token,
    verify_passcode,
)
from app.services.rate_limiter import get_client_ip

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    passcode: str


@router.get("/status")
def auth_status(authorization: Optional[str] = Header(default=None)):
    """인증 활성화 여부 및 현재 토큰 유효성 확인"""
    if settings.allow_insecure_dev_auth:
        return {"auth_required": False, "authenticated": True}

    raw_token = ""
    if authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization[7:].strip()

    return {
        "auth_required": True,
        "authenticated": bool(raw_token and verify_access_token(raw_token)),
    }


@router.post("/login")
def login(request: Request, body: LoginRequest):
    """IP별 실패 제한을 적용하여 패스코드 검증 후 서명된 세션 토큰 발급"""
    if settings.allow_insecure_dev_auth:
        return {"access_token": "", "token_type": "bearer", "auth_required": False}

    client_ip = get_client_ip(request)
    login_rate_limiter.check_allowed(client_ip)

    if not verify_passcode(body.passcode):
        login_rate_limiter.record_failure(client_ip)
        raise HTTPException(status_code=401, detail="패스코드가 올바르지 않습니다.")

    login_rate_limiter.clear(client_ip)
    return {
        "access_token": create_access_token(),
        "token_type": "bearer",
        "auth_required": True,
    }
