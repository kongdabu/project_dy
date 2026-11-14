from fastapi import APIRouter
from app.services.supabase_service import store

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def get_history():
    """학습 이력, 오답 문항 목록, 복습 필요 플래시카드 및 파인만 기록 통합 조회"""
    return store.get_full_history()

