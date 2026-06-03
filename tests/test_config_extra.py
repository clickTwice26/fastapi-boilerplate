from app.core.config import Settings


def test_redis_host_redis_normalizes_to_localhost() -> None:
    s = Settings(redis_host="redis")
    assert "localhost" in s.redis_url


def test_redis_url_without_password_has_no_auth_prefix() -> None:
    s = Settings(redis_password=None)
    # ensure there is no authentication section when password is None
    url = s.redis_url
    assert "@" not in url.split("redis://", 1)[1]


def test_redis_host_redis_not_normalized_when_not_local() -> None:
    s = Settings(redis_host="redis", app_env="production")
    # when not in local env, the host should remain 'redis'
    assert "redis://redis:" in s.redis_url
