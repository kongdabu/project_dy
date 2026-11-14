import base64
import hashlib
import hmac
import json
import time
from collections import deque
from threading import Lock
from typing import Optional
from fastapi import Header, HTTPException, Query
from app.config import MIN_AUTH_SECRET_LENGTH, settings

TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7  # 7일
LOGIN_WINDOW_SECONDS = 600  # 10분
LOGIN_MAX_FAILURES = 5
LOGIN_MAX_LOCKOUT_SECONDS = 300  # 최대 5분 상한


class LoginRateLimiter:
    """IP별 로그인 실패 횟수 추적 및 점진적 임시 차단"""

    def __init__(self) -> None:
        self._failures: dict[str, deque[float]] = {}
        self._locked_until: dict[str, float] = {}
        self._lock = Lock()

    def check_allowed(self, ip: str) -> None:
        now = time.time()
        with self._lock:
            until = self._locked_until.get(ip, 0.0)
            if until > now:
                retry_after = max(1, int(until - now))
                raise HTTPException(
                    status_code=429,
                    detail=f"로그인 시도가 너무 많습니다. {retry_after}초 후 다시 시도해 주세요.",
                )

    def record_failure(self, ip: str) -> None:
        now = time.time()
        with self._lock:
            q = self._failures.setdefault(ip, deque())
            while q and now - q[0] > LOGIN_WINDOW_SECONDS:
                q.popleft()
            q.append(now)
            if len(q) >= LOGIN_MAX_FAILURES:
                # 5회부터 60초, 추가 실패마다 2배씩 증가 (최대 300초)
                over = len(q) - LOGIN_MAX_FAILURES
                lock_sec = min(60 * (2 ** over), LOGIN_MAX_LOCKOUT_SECONDS)
                self._locked_until[ip] = now + lock_sec

    def clear(self, ip: str) -> None:
        with self._lock:
            self._failures.pop(ip, None)
            self._locked_until.pop(ip, None)


login_rate_limiter = LoginRateLimiter()


def _get_signing_secret() -> bytes:
    """공백 제거 후 검증된 AUTH_SECRET만 반환 (빈 키/패스코드 폴백 금지)"""
    secret = settings.auth_secret.strip()
    if len(secret) < MIN_AUTH_SECRET_LENGTH:
        raise HTTPException(status_code=503, detail="서버 인증 비밀키 설정이 올바르지 않습니다.")
    return secret.encode("utf-8")


def verify_passcode(passcode: str) -> bool:
    """상수 시간 비교로 패스코드 검증 (빈 패스코드 자동 통과 금지)"""
    expected = settings.portal_passcode.strip()
    if not expected:
        return False
    return hmac.compare_digest(passcode.strip().encode("utf-8"), expected.encode("utf-8"))


def create_access_token() -> str:
    """HMAC-SHA256 서명된 세션 토큰 생성"""
    secret = _get_signing_secret()
    payload = {
        "sub": "portal_owner",
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
    sig = hmac.new(secret, payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_access_token(token: str) -> bool:
    """서명 및 만료 시간 검증"""
    secret_str = settings.auth_secret.strip()
    if len(secret_str) < MIN_AUTH_SECRET_LENGTH:
        return False
    secret = secret_str.encode("utf-8")

    try:
        payload_b64, sig = token.split(".", 1)
    except ValueError:
        return False

    expected_sig = hmac.new(secret, payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
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
    """모든 보호된 API 라우터에서 사용하는 인증 의존성 (명시적 개발 옵션 외에는 항상 검증)"""
    if settings.allow_insecure_dev_auth:
        return

    raw_token = ""
    if authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization[7:].strip()
    elif token:
        raw_token = token.strip()

    if not raw_token or not verify_access_token(raw_token):
        raise HTTPException(status_code=401, detail="인증이 필요하거나 세션이 만료되었습니다.")
