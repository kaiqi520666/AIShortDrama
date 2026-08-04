from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_env: str = "development"
    database_url: str
    redis_url: str
    secret_key: str
    redis_prefix: str = "aisd"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_endpoint: str = ""
    oss_bucket_name: str = ""
    oss_public_base_url: str = ""
    toapis_key: str = ""
    toapis_url: str = "https://toapis.com"
    volcengine_speech_api_key: str = ""
    volcengine_speech_url: str = "https://openspeech.bytedance.com/api/v3/tts/create"
    aijws_api_key: str = ""
    aijws_base_url: str = "https://api.aijws.com/v1"
    aijws_model: str = "gpt-5.6-sol"
    aijws_reasoning_effort: str = "high"
    zpay_pid: str = ""
    zpay_key: str = ""
    zpay_gateway: str = "https://zpayz.cn"
    zpay_notify_url: str = ""
    zpay_return_url: str = ""
    frontend_base_url: str = "http://localhost:5173"

    @property
    def redis_queue_name(self) -> str:
        return f"{self.redis_prefix}:queue"

    @property
    def secure_cookies(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
