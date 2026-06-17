from datetime import timedelta

from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.security import hash_password, verify_password
from app.crud import repositories as repo
from app.models.domain import InviteCode, User, now_utc


def test_user_and_invite_crud():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = repo.users.create(
            session,
            User(
                email="u@example.com",
                display_name="User",
                password_hash=hash_password("password123"),
            ),
        )
        assert repo.users.by_email(session, "u@example.com").id == user.id
        assert verify_password("password123", user.password_hash)

        invite = repo.invites.create(
            session,
            InviteCode(
                code="TEAM-TEST",
                created_by=user.id,
                max_uses=1,
                expires_at=now_utc() + timedelta(hours=1),
            ),
        )
        assert invite.used_count == 0
        assert repo.invites.consume(session, "TEAM-TEST") is not None
        assert repo.invites.consume(session, "TEAM-TEST") is None
