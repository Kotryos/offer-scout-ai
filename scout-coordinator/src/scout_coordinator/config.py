from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    resend_api_key: str = ""
    resend_webhook_secret: str = ""
    resend_base_url: str = "https://api.resend.com"
    resend_timeout_seconds: float = 30.0

    gmail_smtp_username: str = ""
    gmail_smtp_app_password: str = ""
    gmail_smtp_host: str = "smtp.gmail.com"
    gmail_smtp_port: int = 587

    scout_agent_base_url: str = "http://localhost:8080"
    scout_agent_timeout_seconds: float = 120.0
    scout_agent_auth_mode: str = "none"
    scout_agent_audience: str = ""
    profile_context: str = "Software engineer interested in remote work."

    task_backend: str = "local"
    cloud_tasks_project: str = ""
    cloud_tasks_location: str = ""
    cloud_tasks_queue: str = ""
    cloud_tasks_target_url: str = ""
    cloud_tasks_service_account_email: str = ""
    cloud_tasks_oidc_audience: str = ""
    cloud_tasks_dispatch_deadline_seconds: int = 600
    max_attachment_bytes: int = 5 * 1024 * 1024
    max_offer_text_chars: int = 50_000
    local_task_retry_attempts: int = 3

    app_name: str = "scout-coordinator"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
