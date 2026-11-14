from fastapi import APIRouter, Depends
from app.services.auth_service import require_auth
from app.services.supabase_service import store

router = APIRouter(
    prefix="/api/history",
    tags=["history"],
    dependencies=[Depends(require_auth)],
)


@router.get("")
def get_history():
    """학습 이력, 오답 문항 목록, 복습 필요 플래시카드 및 파인만 기록 통합 조회"""
    return store.get_full_history()
