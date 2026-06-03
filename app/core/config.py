from __future__ import annotations

from functools import cached_property
from typing import Optional

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "FastAPI Boilerplate"
    app_env: str = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    secret_key: SecretStr = Field(
        default="local-development-secret-change-before-production",
        min_length=32,
    )
    allowed_origins: list[str] = ["http://localhost:8000"]

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "fastapi_boilerplate"
    postgres_user: str = "fastapi"
    postgres_password: SecretStr = SecretStr("fastapi_password")
    database_pool_size: int = 10
    database_max_overflow: int = 20

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[SecretStr] = None
    cache_default_ttl_seconds: int = 60

    rate_limit_enabled: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def database_url(self) -> str:
        password = self.postgres_password.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def redis_url(self) -> str:
        password = self.redis_password.get_secret_value() if self.redis_password else None
        auth = f":{password}@" if password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()
