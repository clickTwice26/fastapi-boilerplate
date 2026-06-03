import logging

from app.core.config import Settings, settings
from app.core.logging import configure_logging
from app.core.security import stable_cache_key


def test_settings_urls_include_expected_drivers() -> None:
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.redis_url.startswith("redis://")


def test_settings_redis_url_with_password() -> None:
    custom_settings = Settings(
        secret_key="x" * 32,
        postgres_password="postgres-password",
        redis_password="redis-password",
    )

    assert custom_settings.redis_url == "redis://:redis-password@localhost:6379/0"


def test_stable_cache_key_is_namespaced_hash() -> None:
    key = stable_cache_key("namespace", "value")

    assert key.startswith("namespace:")
    assert key == stable_cache_key("namespace", "value")
    assert key != stable_cache_key("namespace", "other")


def test_configure_logging_replaces_root_handlers() -> None:
    root_logger = logging.getLogger()
    root_logger.handlers = [logging.NullHandler()]

    configure_logging()

    assert len(root_logger.handlers) == 1
    assert root_logger.level == logging.INFO
