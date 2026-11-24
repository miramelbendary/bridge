"""Engine and session factory. One `Database` instance lives on `app.state.db`."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker


class Database:
    def __init__(self, url: str, echo: bool = False) -> None:
        kwargs: dict = {"echo": echo, "pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        self.engine: Engine = create_engine(url, **kwargs)
        if url.startswith("sqlite"):
            # SQLite ignores foreign keys unless asked; keep behaviour close to PostgreSQL.
            @event.listens_for(self.engine, "connect")
            def _enable_fk(dbapi_conn, _record):  # pragma: no cover - trivial
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def ping(self) -> bool:
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True

    def dispose(self) -> None:
        self.engine.dispose()


def get_db(request: Request) -> Iterator[Session]:
    """Request-scoped session. Routes commit explicitly; anything uncommitted is rolled back."""
    session: Session = request.app.state.db.session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
