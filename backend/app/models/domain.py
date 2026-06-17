from datetime import UTC, datetime
from enum import StrEnum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


def now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def new_id() -> str:
    return str(uuid4())


class Role(StrEnum):
    admin = "admin"
    user = "user"
    device = "device"


class User(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    email: str = Field(index=True, unique=True)
    display_name: str
    password_hash: str
    role: str = Field(default=Role.user.value, index=True)
    is_active: bool = True
    created_at: datetime = Field(default_factory=now_utc)


class InviteCode(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    code: str = Field(index=True, unique=True)
    created_by: str
    max_uses: int = 20
    used_count: int = 0
    is_active: bool = True
    created_at: datetime = Field(default_factory=now_utc)
    expires_at: datetime = Field(index=True)


class Device(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(index=True)
    name: str
    device_token_hash: str
    created_at: datetime = Field(default_factory=now_utc)


class Conversation(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(index=True)
    title: str = "Default"
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class Message(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    conversation_id: str = Field(index=True)
    user_id: str = Field(index=True)
    role: str
    content: str
    source: str = "text"
    created_at: datetime = Field(default_factory=now_utc)


class Memory(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(index=True)
    content: str
    source: str
    confidence: float = 1.0
    created_at: datetime = Field(default_factory=now_utc)


class Feedback(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(index=True)
    conversation_id: str = Field(index=True)
    message_id: Optional[str] = Field(default=None, index=True)
    kind: str
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=now_utc)


class DesktopState(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(index=True)
    device_id: Optional[str] = Field(default=None, index=True)
    state: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now_utc)


class AgentRun(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(index=True)
    conversation_id: str = Field(index=True)
    input_source: str
    transcript: Optional[str] = None
    action: str
    expression: str
    speech_text: Optional[str] = None
    tool_summary: dict = Field(default_factory=dict, sa_column=Column(JSON))
    audio_status: str = "not_requested"
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=now_utc)


class AudioRecord(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(index=True)
    conversation_id: str = Field(index=True)
    direction: str
    mime_type: str
    byte_size: int
    created_at: datetime = Field(default_factory=now_utc)
