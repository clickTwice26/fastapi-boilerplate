from types import SimpleNamespace

from app.api.v1.routes.users import get_user_repository
from app.repositories.user_repository import UserRepository


def test_get_user_repository_returns_repository_instance() -> None:
    dummy_session = SimpleNamespace()
    repo = get_user_repository(session=dummy_session)
    assert isinstance(repo, UserRepository)
    assert repo.session is dummy_session
