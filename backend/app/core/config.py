from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_env: str = "development"
    database_url: str
    test_database_url: str = ""
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
    cahaya_enabled: bool = False
    cahaya_gateway: str = "https://api-pay.cahayatech.com"
    cahaya_merchant_no: str = ""
    cahaya_terminal_no: str = ""
    cahaya_access_token: str = ""
    cahaya_notify_url: str = ""
    cahaya_timeout_seconds: int = 20
    frontend_base_url: str = "http://localhost:5173"
    trusted_proxy_cidrs: str = "127.0.0.1/32,::1/128,172.16.0.0/12"
    turnstile_site_key: str = ""
    turnstile_secret_key: str = ""
    tencent_cloud_secret_id: str = ""
    tencent_cloud_secret_key: str = ""
    tencent_ses_region: str = "ap-hongkong"
    tencent_ses_from_email: str = "no-reply@mail.nodepass.net"
    tencent_ses_template_id: int = 204003

    @property
    def redis_queue_name(self) -> str:
        return f"{self.redis_prefix}:queue"

    @property
    def secure_cookies(self) -> bool:
        return self.app_env == "production"

    @property
    def active_database_url(self) -> str:
        if self.app_env != "test":
            return self.database_url
        return validate_test_database_url(self.database_url, self.test_database_url)


def validate_test_database_url(database_url: str, test_database_url: str) -> str:
    if not test_database_url:
        raise ValueError("TEST_DATABASE_URL 未配置")
    database = make_url(database_url)
    test_database = make_url(test_database_url)
    test_name = (test_database.database or "").lower()
    if database.render_as_string(hide_password=False) == test_database.render_as_string(
        hide_password=False
    ):
        raise ValueError("测试数据库不能与业务数据库相同")
    if "test" not in test_name:
        raise ValueError("测试数据库名称必须包含 test")
    return test_database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
