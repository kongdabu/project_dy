import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional
from fastapi import Header, HTTPException, Query
from app.config import settings

# auth_secret 미설정 시 프로세스 기동 시점의 안전한 임시 시크릿 사용
_EPHEMERAL_SECRET = secrets.token_hex(32)
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7  # 7일


def _get_signing_secret() -> bytes:
    secret = (settings.auth_secret or settings.portal_passcode or _EPHEMERAL_SECRET).strip()
    return secret.encode("utf-8")


def verify_passcode(passcode: str) -> bool:
    """상수 시간 비교로 패스코드 검증"""
    expected = settings.portal_passcode.strip()
    if not expected:
        return True
    return hmac.compare_digest(passcode.strip().encode("utf-8"), expected.encode("utf-8"))


def create_access_token() -> str:
    """HMAC-SHA256 서명된 세션 토큰 생성"""
    payload = {
        "sub": "portal_owner",
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
    sig = hmac.new(_get_signing_secret(), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_access_token(token: str) -> bool:
    """서명 및 만료 시간 검증"""
    try:
        payload_b64, sig = token.split(".", 1)
    except ValueError:
        return False

    expected_sig = hmac.new(_get_signing_secret(), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return False

    padding = "=" * (-len(payload_b64) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8"))
    except Exception:
        return False

    return int(payload.get("exp", 0)) > int(time.time())


def require_auth(
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> None:
    """모든 보호된 API 라우터에서 사용하는 인증 의존성"""
    if not settings.is_auth_enabled:
        return

    raw_token = ""
    if authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization[7:].strip()
    elif token:
        raw_token = token.strip()

    if not raw_token or not verify_access_token(raw_token):
        raise HTTPException(status_code=401, detail="인증이 필요하거나 세션이 만료되었습니다.")

