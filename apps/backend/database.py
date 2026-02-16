from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.auth.shared.infrastructure.sqlalchemy_base import AuthBase


def create_engine_for_url(database_url: str) -> Engine:
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(database_url, future=True, connect_args=connect_args)


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    engine = create_engine_for_url(database_url)
    return sessionmaker(engine, autoflush=False, autocommit=False, expire_on_commit=False)


def create_auth_schema(database_url: str) -> None:
    engine = create_engine_for_url(database_url)
    AuthBase.metadata.create_all(bind=engine)

