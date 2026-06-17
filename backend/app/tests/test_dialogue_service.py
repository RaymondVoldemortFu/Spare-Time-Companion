from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.security import hash_password
from app.models.domain import User
from app.schemas.api import AgentDecision
from app.services.aliyun_audio import SpeechResult, TTSResult
from app.services.dialogue import DialogueService


class FakeLLM:
    def decide(self, *args, **kwargs):
        return AgentDecision(
            action="suggest",
            speech_text="先站起来喝口水，然后休息三分钟。",
            expression="happy",
            animation="talk",
            memory="用户疲惫时偏好轻量休息建议",
            summary="生成轻量休息建议",
        )


class FakeAudio:
    def synthesize(self, text: str):
        assert text
        return TTSResult(audio=b"audio")

    def transcribe(self, audio: bytes, mime_type: str):
        assert audio
        assert "wav" in mime_type
        return SpeechResult(text="我有点累")


def test_dialogue_text_flow():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    service = DialogueService(FakeLLM(), FakeAudio())
    with Session(engine) as session:
        user = User(
            email="u@example.com",
            display_name="User",
            password_hash=hash_password("password123"),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        result = service.handle_text(
            session=session,
            user=user,
            text="我有点累",
            conversation_id=None,
            desktop_state={"presence": "at_desk"},
            trigger="text",
        )
        assert result.action == "suggest"
        assert result.audio_base64
        assert result.speech_text == "先站起来喝口水，然后休息三分钟。"

