from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from .config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)

# Ensure enum includes new statuses (PostgreSQL only)
try:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_type t WHERE t.typname = 'callstatus') THEN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_enum e
                            JOIN pg_type t ON t.oid = e.enumtypid
                            WHERE t.typname = 'callstatus' AND e.enumlabel = 'HANGUP'
                        ) THEN
                            ALTER TYPE callstatus ADD VALUE 'HANGUP';
                        END IF;
                    END IF;
                END$$;
                """
            )
        )
except Exception:
    # Ignore if not PostgreSQL or already updated
    pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
