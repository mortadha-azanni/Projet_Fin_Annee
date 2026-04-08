from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src import config

from .base import Base

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


try:
    DATABASE_URL = config.getDatabaseUrl()
except ValueError as error:
    raise RuntimeError(f"Invalid database configuration: {error}") from error

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
except Exception as error:
    raise RuntimeError("Failed to initialize database engine") from error

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def getSession() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def initDb() -> None:
    Base.metadata.create_all(bind=engine)
