from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="SAT-SA")
    environment: str = Field(default="development")

    secret_key: str = Field(
        default="dev-secret-change-me-please-0123456789abcdef"
    )
    access_token_expire_minutes: int = Field(default=480)

    database_url: str = Field(default="sqlite+aiosqlite:///./sat_sa.db")
    cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")

    admin_username: str = Field(default="admin")
    admin_email: str = Field(default="admin@sat-sa.gov.in")
    admin_password: str = Field(default="Admin@12345")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()