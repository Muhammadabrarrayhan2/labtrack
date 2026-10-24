from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()
_url = make_url(settings.sqlalchemy_url)
IS_SQLITE = _url.get_backend_name() == "sqlite"

if IS_SQLITE:
    engine = create_engine(_url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

else:
    # Small pool: Cloud Run scales out with instances, and db-f1-micro allows ~25 connections
    engine = create_engine(_url, pool_pre_ping=True, pool_size=5, max_overflow=2, pool_recycle=1800)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
