from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE_PATH = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """애플리케이션 환경 변수 설정"""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_bucket: str = "study-materials"
    allowed_origins: str = "http://localhost:3000"

    # 1인 포털 접근 패스코드 및 토큰 서명 비밀키
    portal_passcode: str = ""
    auth_secret: str = ""

    # 업로드 및 AI 호출 제한
    max_upload_mb: int = 20
    max_document_pages: int = 150
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
        """패스코드 인증 활성화 여부"""
        return bool(self.portal_passcode.strip())


settings = Settings()
