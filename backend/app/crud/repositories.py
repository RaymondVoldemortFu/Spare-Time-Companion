from sqlmodel import Session, col, select

from app.crud.base import CRUDBase
from app.models.domain import (
    AgentRun,
    AudioRecord,
    Conversation,
    DesktopState,
    Feedback,
    InviteCode,
    Memory,
    Message,
    User,
    now_utc,
)


class UserRepo(CRUDBase[User]):
    def __init__(self) -> None:
        super().__init__(User)

    def by_email(self, session: Session, email: str) -> User | None:
        return session.exec(select(User).where(User.email == email)).first()


class InviteRepo(CRUDBase[InviteCode]):
    def __init__(self) -> None:
        super().__init__(InviteCode)

    def by_code(self, session: Session, code: str) -> InviteCode | None:
        return session.exec(select(InviteCode).where(InviteCode.code == code)).first()

    def consume(self, session: Session, code: str) -> InviteCode | None:
        invite = self.by_code(session, code)
        if (
            not invite
            or not invite.is_active
            or invite.used_count >= invite.max_uses
            or invite.expires_at <= now_utc()
        ):
            return None
        invite.used_count += 1
        session.add(invite)
        session.commit()
        session.refresh(invite)
        return invite

    def available(self, session: Session, limit: int = 200) -> list[InviteCode]:
        return list(
            session.exec(
                select(InviteCode)
                .where(
                    InviteCode.is_active == True,  # noqa: E712
                    InviteCode.used_count < InviteCode.max_uses,
                    InviteCode.expires_at > now_utc(),
                )
                .order_by(col(InviteCode.expires_at).asc())
                .limit(limit)
            ).all()
        )


class ConversationRepo(CRUDBase[Conversation]):
    def __init__(self) -> None:
        super().__init__(Conversation)

    def get_or_create(self, session: Session, user_id: str, conversation_id: str | None) -> Conversation:
        if conversation_id:
            found = session.get(Conversation, conversation_id)
            if found and found.user_id == user_id:
                return found
        convo = Conversation(user_id=user_id)
        session.add(convo)
        session.commit()
        session.refresh(convo)
        return convo

    def touch(self, session: Session, conversation: Conversation) -> None:
        conversation.updated_at = now_utc()
        session.add(conversation)
        session.commit()


class MessageRepo(CRUDBase[Message]):
    def __init__(self) -> None:
        super().__init__(Message)

    def recent(self, session: Session, conversation_id: str, limit: int = 12) -> list[Message]:
        rows = session.exec(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(col(Message.created_at).desc())
            .limit(limit)
        ).all()
        return list(reversed(rows))

    def by_user(self, session: Session, user_id: str, limit: int = 100) -> list[Message]:
        return list(
            session.exec(
                select(Message)
                .where(Message.user_id == user_id)
                .order_by(col(Message.created_at).desc())
                .limit(limit)
            ).all()
        )


class MemoryRepo(CRUDBase[Memory]):
    def __init__(self) -> None:
        super().__init__(Memory)

    def recent_for_user(self, session: Session, user_id: str, limit: int = 20) -> list[Memory]:
        return list(
            session.exec(
                select(Memory)
                .where(Memory.user_id == user_id)
                .order_by(col(Memory.created_at).desc())
                .limit(limit)
            ).all()
        )


class DesktopStateRepo(CRUDBase[DesktopState]):
    def __init__(self) -> None:
        super().__init__(DesktopState)

    def latest(self, session: Session, user_id: str) -> DesktopState | None:
        return session.exec(
            select(DesktopState)
            .where(DesktopState.user_id == user_id)
            .order_by(col(DesktopState.created_at).desc())
            .limit(1)
        ).first()


class AgentRunRepo(CRUDBase[AgentRun]):
    def __init__(self) -> None:
        super().__init__(AgentRun)

    def recent(self, session: Session, user_id: str, limit: int = 50) -> list[AgentRun]:
        return list(
            session.exec(
                select(AgentRun)
                .where(AgentRun.user_id == user_id)
                .order_by(col(AgentRun.created_at).desc())
                .limit(limit)
            ).all()
        )


def clear_user_demo_data(session: Session, user_id: str) -> None:
    model_filters = [
        (AudioRecord, AudioRecord.user_id == user_id),
        (AgentRun, AgentRun.user_id == user_id),
        (DesktopState, DesktopState.user_id == user_id),
        (Feedback, Feedback.user_id == user_id),
        (Memory, Memory.user_id == user_id),
        (Message, Message.user_id == user_id),
        (Conversation, Conversation.user_id == user_id),
    ]
    for model, condition in model_filters:
        for item in session.exec(select(model).where(condition)).all():
            session.delete(item)
    session.commit()


users = UserRepo()
invites = InviteRepo()
conversations = ConversationRepo()
messages = MessageRepo()
memories = MemoryRepo()
desktop_states = DesktopStateRepo()
agent_runs = AgentRunRepo()
feedbacks = CRUDBase[Feedback](Feedback)
