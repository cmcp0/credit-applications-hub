from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from apps.backend.auth.dependencies import get_password_hasher
from apps.backend.database import create_engine_for_url
from apps.backend.main import create_app
from apps.backend.rate_limit.redis_storage import InMemorySlidingWindowStorage
from apps.backend.settings import Settings
from src.auth.shared.infrastructure.sqlalchemy_base import AuthBase
from tests.auth.fixtures.seed import PASSWORD, TEST_USERS, seed_auth_data
from tests.auth.fixtures.test_password_hasher import TestPasswordHasher


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'auth-test.db'}"
    return Settings(
        database_url=database_url,
        auth_jwt_secret="test-secret",
        auth_jwt_issuer="credit-applications-hub",
        auth_jwt_audience="credit-applications-hub-api",
        auth_jwt_ttl_seconds=3600,
        rate_limit_enabled=True,
        rate_limit_redis_url="redis://unused",
        rate_limit_public_window_seconds=60,
        rate_limit_public_max_requests=120,
        rate_limit_login_ip_window_seconds=60,
        rate_limit_login_ip_max_requests=10,
        rate_limit_login_email_ip_window_seconds=300,
        rate_limit_login_email_ip_max_requests=5,
        rate_limit_key_pepper="test-pepper",
    )


@pytest.fixture
def session_factory(settings: Settings) -> sessionmaker[Session]:
    engine = create_engine_for_url(settings.database_url)
    AuthBase.metadata.create_all(bind=engine)

    factory: sessionmaker[Session] = sessionmaker(
        engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    test_password_hasher = TestPasswordHasher()
    with factory() as session:
        seed_auth_data(session, password_hasher=test_password_hasher)

    yield factory

    AuthBase.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def app(settings: Settings, session_factory: sessionmaker[Session]):
    storage = InMemorySlidingWindowStorage()
    app_instance = create_app(
        settings=settings,
        session_factory=session_factory,
        rate_limit_storage=storage,
    )
    test_password_hasher = TestPasswordHasher()
    app_instance.dependency_overrides[get_password_hasher] = lambda: test_password_hasher
    return app_instance


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


@pytest.fixture
def seeded_users() -> dict[str, dict[str, str]]:
    return {
        "customer": {"email": TEST_USERS["customer"]["email"], "password": PASSWORD},
        "operation": {"email": TEST_USERS["operation"]["email"], "password": PASSWORD},
        "admin": {"email": TEST_USERS["admin"]["email"], "password": PASSWORD},
        "inactive": {"email": TEST_USERS["inactive_customer"]["email"], "password": PASSWORD},
    }
