import time
from collections import deque
from threading import Lock
from fastapi import HTTPException, Request
from app.config import settings


def get_client_ip(request: Request) -> str:
    """
    리버스 프록시 환경에서 스푸핑을 방지하여 클라이언트 IP를 추출한다.
    클라이언트가 임의로 보낸 X-Forwarded-For 앞부분([0])은 신뢰하지 않고,
    프록시가 마지막에 추가한 IP([-1])를 사용한다.
    """
    forwarded_parts = [
        part.strip()
        for part in request.headers.get("x-forwarded-for", "").split(",")
        if part.strip()
    ]
    if forwarded_parts:
        return forwarded_parts[-1]
    return request.client.host if request.client else "unknown"


class SlidingWindowRateLimiter:
    """메모리 기반 분당/일일 AI 호출 속도 제한기"""

    def __init__(self) -> None:
        self._minute_hits: dict[str, deque[float]] = {}
        self._day_hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.time()
        with self._lock:
            m_queue = self._minute_hits.setdefault(key, deque())
            while m_queue and now - m_queue[0] > 60:
                m_queue.popleft()
            if len(m_queue) >= settings.ai_rate_limit_per_minute:
                raise HTTPException(
                    status_code=429,
                    detail="AI 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
                )

            d_queue = self._day_hits.setdefault(key, deque())
            while d_queue and now - d_queue[0] > 86400:
                d_queue.popleft()
            if len(d_queue) >= settings.ai_rate_limit_per_day:
                raise HTTPException(
                    status_code=429,
                    detail="일일 AI 사용량 상한에 도달했습니다. 내일 다시 시도해 주세요.",
                )

            m_queue.append(now)
            d_queue.append(now)


ai_rate_limiter = SlidingWindowRateLimiter()


def enforce_ai_rate_limit(request: Request) -> None:
    """AI 엔드포인트 호출 전 속도 및 일일 사용량 검사"""
    ai_rate_limiter.check(get_client_ip(request))
