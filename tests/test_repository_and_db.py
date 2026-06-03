from uuid import uuid4

import pytest

from app.db import session as session_module
from app.db.base import Base, User
from app.db.session import get_db_session
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate


class FakeScalarResult:
    def __init__(self, values) -> None:
        self.values = values

    def all(self):
        return self.values


class FakeResult:
    def __init__(self, scalar=None, values=None) -> None:
        self.scalar = scalar
        self.values = values or []

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self.values)


class FakeSession:
    def __init__(self, results=None) -> None:
        self.results = list(results or [])
        self.added = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        self.closed = True

    def add(self, value) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        return None

    async def refresh(self, value) -> None:
        return None

    async def execute(self, statement):
        assert statement is not None
        return self.results.pop(0)

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


async def test_user_repository_create() -> None:
    session = FakeSession()
    repository = UserRepository(session)

    user = await repository.create(UserCreate(email="alan@example.com", full_name="Alan Turing"))

    assert user.email == "alan@example.com"
    assert user.full_name == "Alan Turing"
    assert session.added == [user]


async def test_user_repository_getters_and_list() -> None:
    user = User(email="katherine@example.com", full_name="Katherine Johnson")
    session = FakeSession(
        results=[
            FakeResult(scalar=user),
            FakeResult(scalar=None),
            FakeResult(values=[user]),
        ]
    )
    repository = UserRepository(session)

    assert await repository.get_by_id(uuid4()) is user
    assert await repository.get_by_email("missing@example.com") is None
    assert await repository.list(limit=10, offset=0) == [user]


async def test_get_db_session_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    monkeypatch.setattr(session_module, "AsyncSessionLocal", lambda: session)

    generator = get_db_session()
    yielded = await anext(generator)
    assert yielded is session

    with pytest.raises(StopAsyncIteration):
        await anext(generator)

    assert session.committed is True
    assert session.rolled_back is False
    assert session.closed is True


async def test_get_db_session_rolls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    monkeypatch.setattr(session_module, "AsyncSessionLocal", lambda: session)

    generator = get_db_session()
    yielded = await anext(generator)
    assert yielded is session

    with pytest.raises(RuntimeError, match="fail"):
        await generator.athrow(RuntimeError("fail"))

    assert session.committed is False
    assert session.rolled_back is True
    assert session.closed is True


def test_base_exports_user_model() -> None:
    assert "users" in Base.metadata.tables
    assert User.__tablename__ == "users"
