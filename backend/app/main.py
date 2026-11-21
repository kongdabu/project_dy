import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, documents, history, study
from app.services.supabase_service import store

# Render 등 운영 환경에서 app.* 모듈의 INFO/WARNING/ERROR 로그가 표준출력으로 즉시 남도록 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
    force=True,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """서버 기동 시 필수 보안 설정(PORTAL_PASSCODE, AUTH_SECRET) 검증"""
    settings.validate_security_config()
    yield


app = FastAPI(
    title="MedStudy Portal API",
    description="의대생을 위한 AI 학습 포털 (요약·의학용어·근거링크·마인드맵·예상문제·플래시카드·파인만 튜터)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(study.router)
app.include_router(history.router)


@app.api_route("/", methods=["GET", "HEAD"])
def root():
    """Render 기본 헬스체크(HEAD /) 및 루트 접속용 200 OK 응답"""
    return {"service": "MedStudy Portal API", "status": "ok"}


@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    """서버 및 저장소 상태 확인"""
    provider = (settings.ai_provider or "openrouter").strip().lower()
    active_model = (
        settings.openrouter_model if provider == "openrouter" else settings.gemini_model
    )
    return {
        "status": "ok",
        "storage_mode": "supabase" if store.is_supabase else "local_fallback",
        "ai_provider": provider,
        "ai_model": active_model,
        "auth_enabled": settings.is_auth_enabled,
    }
