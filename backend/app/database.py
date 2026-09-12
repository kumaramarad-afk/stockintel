from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def _make_engine():
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return engine
    except Exception:
        sqlite_path = Path(__file__).resolve().parents[1] / "data" / "stockintel.db"
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        return create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_user_schema() -> None:
    import app.models  # noqa: F401 — register every mapped table

    Base.metadata.create_all(bind=engine)
    dialect = engine.dialect.name
    extra_columns = {
        "plan": "VARCHAR(32) DEFAULT 'free'",
        "reports_generated": "INTEGER DEFAULT 0",
        "subscribed_at": "TIMESTAMPTZ" if dialect == "postgresql" else "DATETIME",
        "stripe_customer_id": "VARCHAR(255)",
        "stripe_subscription_id": "VARCHAR(255)",
        "oauth_provider": "VARCHAR(32)",
        "oauth_subject": "VARCHAR(255)",
        "newsletter_subscription_status": "VARCHAR(50) DEFAULT 'none'",
        "newsletter_email_preference": "VARCHAR(50) DEFAULT 'daily'",
        "newsletter_subscribed_at": "TIMESTAMPTZ" if dialect == "postgresql" else "DATETIME",
    }
    if dialect == "postgresql":
        with engine.begin() as connection:
            for name, definition in extra_columns.items():
                connection.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {name} {definition}"))
            connection.execute(
                text(
                    """
                    UPDATE users
                    SET reports_generated = (
                        SELECT COUNT(*) FROM report_views WHERE report_views.user_id = users.id
                    )
                    WHERE COALESCE(reports_generated, 0) = 0
                    """
                )
            )
            connection.execute(text("ALTER TABLE newsletter_issues ADD COLUMN IF NOT EXISTS ticker VARCHAR(16)"))
        return
    if dialect != "sqlite":
        return
    with engine.connect() as connection:
        cols = {row[1] for row in connection.execute(text("PRAGMA table_info(users)"))}
        issue_cols = {row[1] for row in connection.execute(text("PRAGMA table_info(newsletter_issues)"))}
        connection.commit()
    for name, definition in extra_columns.items():
        if name in cols:
            continue
        sqlite_def = definition.replace("TIMESTAMPTZ", "DATETIME")
        try:
            with engine.begin() as connection:
                connection.execute(text(f'ALTER TABLE users ADD COLUMN "{name}" {sqlite_def}'))
        except Exception:
            continue
    if "ticker" not in issue_cols:
        try:
            with engine.begin() as connection:
                connection.execute(text('ALTER TABLE newsletter_issues ADD COLUMN ticker VARCHAR(16)'))
        except Exception:
            pass
    with engine.begin() as connection:
        try:
            connection.execute(
                text(
                    """
                    UPDATE users
                    SET reports_generated = (
                        SELECT COUNT(*) FROM report_views WHERE report_views.user_id = users.id
                    )
                    WHERE COALESCE(reports_generated, 0) = 0
                    """
                )
            )
        except Exception:
            pass
