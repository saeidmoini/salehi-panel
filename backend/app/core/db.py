from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from .config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)

def _ensure_callstatus_enum():
    # Ensure enum includes new statuses (PostgreSQL only)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF EXISTS (SELECT 1 FROM pg_type t WHERE t.typname = 'callstatus') THEN
                            PERFORM 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = 'callstatus' AND e.enumlabel = 'HANGUP';
                            IF NOT FOUND THEN
                                ALTER TYPE callstatus ADD VALUE 'HANGUP';
                            END IF;
                            PERFORM 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = 'callstatus' AND e.enumlabel = 'DISCONNECTED';
                            IF NOT FOUND THEN
                                ALTER TYPE callstatus ADD VALUE 'DISCONNECTED';
                            END IF;
                            PERFORM 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = 'callstatus' AND e.enumlabel = 'BUSY';
                            IF NOT FOUND THEN
                                ALTER TYPE callstatus ADD VALUE 'BUSY';
                            END IF;
                            PERFORM 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = 'callstatus' AND e.enumlabel = 'POWER_OFF';
                            IF NOT FOUND THEN
                                ALTER TYPE callstatus ADD VALUE 'POWER_OFF';
                            END IF;
                            PERFORM 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = 'callstatus' AND e.enumlabel = 'BANNED';
                            IF NOT FOUND THEN
                                ALTER TYPE callstatus ADD VALUE 'BANNED';
                            END IF;
                            PERFORM 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = 'callstatus' AND e.enumlabel = 'UNKNOWN';
                            IF NOT FOUND THEN
                                ALTER TYPE callstatus ADD VALUE 'UNKNOWN';
                            END IF;
                        END IF;
                    END$$;
                    """
                )
            )
    except Exception:
        # Ignore if not PostgreSQL or already updated
        pass


def _ensure_admin_columns():
    try:
        with engine.begin() as conn:
            inspector = inspect(conn)
            columns = {col["name"] for col in inspector.get_columns("admin_users")}

            conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
                            CREATE TYPE userrole AS ENUM ('ADMIN', 'AGENT');
                        END IF;
                    END$$;
                    """
                )
            )

            if "role" not in columns:
                conn.execute(text("ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS role userrole DEFAULT 'ADMIN'"))
                conn.execute(text("UPDATE admin_users SET role='ADMIN' WHERE role IS NULL"))
                conn.execute(text("ALTER TABLE admin_users ALTER COLUMN role DROP DEFAULT"))
            if "first_name" not in columns:
                conn.execute(text("ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS first_name VARCHAR(100)"))
            if "last_name" not in columns:
                conn.execute(text("ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS last_name VARCHAR(100)"))
            if "phone_number" not in columns:
                conn.execute(text("ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(32)"))
    except Exception:
        # Ignore if not PostgreSQL or already updated
        pass


def _ensure_phone_columns():
    """Ensure numbers table has required columns (renamed from phone_numbers)."""
    try:
        with engine.begin() as conn:
            inspector = inspect(conn)
            # Try new table name first, fall back to old name
            try:
                columns = {col["name"] for col in inspector.get_columns("numbers")}
                table_name = "numbers"
            except Exception:
                columns = {col["name"] for col in inspector.get_columns("phone_numbers")}
                table_name = "phone_numbers"

            if "last_user_message" not in columns:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS last_user_message VARCHAR(1000)"))
            if "assigned_agent_id" not in columns:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS assigned_agent_id INTEGER"))
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table_name}_assigned_agent_id ON {table_name} (assigned_agent_id)"))
            conn.execute(
                text(
                    f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.table_constraints
                            WHERE constraint_name = 'fk_{table_name}_assigned_agent'
                              AND table_name = '{table_name}'
                        ) THEN
                            ALTER TABLE {table_name}
                            ADD CONSTRAINT fk_{table_name}_assigned_agent
                            FOREIGN KEY (assigned_agent_id)
                            REFERENCES admin_users(id)
                            ON DELETE SET NULL;
                        END IF;
                    END$$;
                    """
                )
            )
    except Exception:
        # Ignore if not PostgreSQL or already updated
        pass


def _ensure_call_result_columns():
    """Ensure call_results table has required columns (renamed from call_attempts)."""
    try:
        with engine.begin() as conn:
            inspector = inspect(conn)
            # Try new table name first, fall back to old name
            try:
                columns = {col["name"] for col in inspector.get_columns("call_results")}
                table_name = "call_results"
            except Exception:
                columns = {col["name"] for col in inspector.get_columns("call_attempts")}
                table_name = "call_attempts"

            if "user_message" not in columns:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS user_message VARCHAR(1000)"))
            if "agent_id" not in columns:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS agent_id INTEGER"))
            if "call_direction" not in columns:
                conn.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        "ADD COLUMN IF NOT EXISTS call_direction VARCHAR(16) NOT NULL DEFAULT 'OUTBOUND'"
                    )
                )
                conn.execute(
                    text(
                        f"UPDATE {table_name} "
                        "SET call_direction = CASE WHEN status = 'INBOUND_CALL' THEN 'INBOUND' ELSE 'OUTBOUND' END "
                        "WHERE call_direction IS NULL"
                    )
                )
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table_name}_agent_id ON {table_name} (agent_id)"))
            conn.execute(
                text(
                    f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.table_constraints
                            WHERE constraint_name = 'fk_{table_name}_agent'
                              AND table_name = '{table_name}'
                        ) THEN
                            ALTER TABLE {table_name}
                            ADD CONSTRAINT fk_{table_name}_agent
                            FOREIGN KEY (agent_id)
                            REFERENCES admin_users(id)
                            ON DELETE SET NULL;
                        END IF;
                    END$$;
                    """
                )
            )
    except Exception:
        # Ignore if not PostgreSQL or already updated
        pass


_ensure_callstatus_enum()
_ensure_admin_columns()
_ensure_phone_columns()
_ensure_call_result_columns()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
