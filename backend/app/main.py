from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import documents, history, study
from app.services.supabase_service import store

app = FastAPI(
    title="MedStudy Portal API",
    description="의대생을 위한 AI 학습 포털 (요약·의학용어·근거링크·마인드맵·예상문제·플래시카드·파인만 튜터)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(study.router)
app.include_router(history.router)


@app.get("/health")
def health_check():
    """서버 및 저장소 상태 확인"""
    return {
        "status": "ok",
        "storage_mode": "supabase" if store.is_supabase else "local_fallback",
        "gemini_model": settings.gemini_model,
    }

