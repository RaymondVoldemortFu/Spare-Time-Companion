from collections.abc import Generator
from datetime import timedelta

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.domain import InviteCode, User
from app.services.invites import generate_invite_code
from app.models.domain import now_utc


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    _apply_sqlite_compat_migrations()


def _apply_sqlite_compat_migrations() -> None:
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "invitecode" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("invitecode")}
    if "expires_at" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE invitecode ADD COLUMN expires_at DATETIME"))
            connection.execute(
                text(
                    "UPDATE invitecode SET expires_at = datetime(created_at, '+72 hours') "
                    "WHERE expires_at IS NULL"
                )
            )


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def seed_defaults() -> None:
    settings.validate_public_demo_secrets()
    with Session(engine) as session:
        legacy_invite = session.exec(select(InviteCode).where(InviteCode.code == "TEAM-DEMO")).first()
        if legacy_invite:
            legacy_invite.is_active = False
            session.add(legacy_invite)

        admin = session.exec(select(User).where(User.email == settings.ADMIN_EMAIL)).first()
        if not admin:
            session.add(
                User(
                    email=settings.ADMIN_EMAIL,
                    display_name="Demo Admin",
                    password_hash=hash_password(settings.ADMIN_PASSWORD),
                    role="admin",
                    is_active=True,
                )
            )
        elif not verify_password(settings.ADMIN_PASSWORD, admin.password_hash):
            admin.password_hash = hash_password(settings.ADMIN_PASSWORD)
            admin.role = "admin"
            admin.is_active = True
            session.add(admin)
        active_invite = session.exec(
            select(InviteCode).where(
                InviteCode.is_active == True,  # noqa: E712
                InviteCode.used_count < InviteCode.max_uses,
                InviteCode.expires_at > now_utc(),
            )
        ).first()
        if not active_invite:
            session.add(
                InviteCode(
                    code=generate_invite_code(),
                    created_by="system",
                    max_uses=20,
                    expires_at=now_utc() + timedelta(hours=72),
                )
            )
        session.commit()
