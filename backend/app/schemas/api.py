from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=80)
    invite_code: str


class InviteCreate(BaseModel):
    max_uses: int = Field(default=20, ge=1, le=1000)
    ttl_hours: int = Field(default=72, ge=1, le=24 * 30)


class TextTurnRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[str] = None
    desktop_state: dict[str, Any] = Field(default_factory=dict)
    trigger: str = "text"


class TriggerRequest(BaseModel):
    conversation_id: Optional[str] = None
    desktop_state: dict[str, Any] = Field(default_factory=dict)
    trigger: str = "button"


class DesktopStateRequest(BaseModel):
    device_id: Optional[str] = None
    state: dict[str, Any]


class FeedbackRequest(BaseModel):
    conversation_id: str
    message_id: Optional[str] = None
    kind: str = Field(pattern="^(positive|negative|regenerate|remember|dismiss)$")
    note: Optional[str] = None


class TurnResponse(BaseModel):
    conversation_id: str
    transcript: Optional[str] = None
    action: str
    expression: str
    animation: str
    speech_text: Optional[str] = None
    audio_base64: Optional[str] = None
    audio_mime_type: Optional[str] = None
    debug: dict[str, Any] = Field(default_factory=dict)


class HistoryItem(BaseModel):
    id: str
    role: str
    content: str
    source: str
    created_at: datetime


class AgentDecision(BaseModel):
    action: str = Field(pattern="^(reply|ask|suggest|remember|confirm|regenerate|silent)$")
    speech_text: str = ""
    expression: str = Field(default="thinking")
    animation: str = Field(default="idle")
    memory: Optional[str] = None
    summary: str = ""
