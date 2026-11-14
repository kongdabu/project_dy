from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE_PATH = Path(__file__).resolve().parent.parent / ".env"
MIN_AUTH_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """애플리케이션 환경 변수 설정"""

    ai_provider: str = "openrouter"
    openrouter_api_key: str = ""
    openrouter_model: str = "qwen/qwen3.7-flash"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_bucket: str = "study-materials"
    allowed_origins: str = "http://localhost:3000"

    # 1인 포털 접근 패스코드 및 토큰 서명 비밀키
    portal_passcode: str = ""
    auth_secret: str = ""
    # 명시적 로컬 개발 전용 옵션 (운영에서는 반드시 False 유지)
    allow_insecure_dev_auth: bool = False

    # 업로드 및 AI 호출 제한
    max_upload_mb: int = 500
    max_document_pages: int = 500
    ai_rate_limit_per_minute: int = 15
    ai_rate_limit_per_day: int = 150

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        """쉼표로 구분된 CORS 허용 도메인 목록 반환"""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def is_supabase_configured(self) -> bool:
        """Supabase 연동 설정 여부 확인"""
        return bool(self.supabase_url and self.supabase_key and "your-project" not in self.supabase_url)

    @property
    def is_auth_enabled(self) -> bool:
        """명시적 로컬 개발 우회 옵션이 꺼져 있으면 항상 인증 강제"""
        return not self.allow_insecure_dev_auth

    def validate_security_config(self) -> None:
        """서버 시작 시 인증 및 서명 비밀키 설정 검증"""
        if self.allow_insecure_dev_auth:
            return
        if not self.portal_passcode.strip():
            raise RuntimeError(
                "보안 설정 오류: PORTAL_PASSCODE가 설정되지 않았습니다. "
                "운영 환경에서는 반드시 PORTAL_PASSCODE를 설정하세요."
            )
        secret = self.auth_secret.strip()
        if len(secret) < MIN_AUTH_SECRET_LENGTH:
            raise RuntimeError(
                f"보안 설정 오류: AUTH_SECRET은 공백 제외 최소 {MIN_AUTH_SECRET_LENGTH}자 이상이어야 합니다."
            )


settings = Settings()
