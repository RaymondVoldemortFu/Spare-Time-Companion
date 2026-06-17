from sqlmodel import Session

from app.crud import repositories as repo
from app.models.domain import AgentRun, DesktopState, Memory, Message, User
from app.schemas.api import TurnResponse
from app.services.aliyun_audio import AliyunAudioClient
from app.services.llm import LLMClient


class DialogueService:
    def __init__(self, llm: LLMClient, audio: AliyunAudioClient):
        self.llm = llm
        self.audio = audio

    def handle_text(
        self,
        session: Session,
        user: User,
        text: str,
        conversation_id: str | None,
        desktop_state: dict,
        trigger: str,
        synthesize: bool = True,
    ) -> TurnResponse:
        conversation = repo.conversations.get_or_create(session, user.id, conversation_id)
        if desktop_state:
            repo.desktop_states.create(
                session, DesktopState(user_id=user.id, state=desktop_state)
            )
        latest_state = repo.desktop_states.latest(session, user.id)

        repo.messages.create(
            session,
            Message(
                conversation_id=conversation.id,
                user_id=user.id,
                role="user",
                content=text,
                source=trigger,
            ),
        )
        history = repo.messages.recent(session, conversation.id)
        memories = repo.memories.recent_for_user(session, user.id)
        decision = self.llm.decide(text, history, memories, latest_state, trigger)

        if decision.memory:
            repo.memories.create(
                session,
                Memory(user_id=user.id, content=decision.memory, source=f"agent:{trigger}"),
            )

        assistant_message_id = None
        if decision.speech_text:
            assistant_message = repo.messages.create(
                session,
                Message(
                    conversation_id=conversation.id,
                    user_id=user.id,
                    role="assistant",
                    content=decision.speech_text,
                    source="llm",
                ),
            )
            assistant_message_id = assistant_message.id

        audio_base64 = None
        audio_mime_type = None
        audio_status = "not_requested"
        if synthesize and decision.speech_text:
            tts = self.audio.synthesize(decision.speech_text)
            audio_base64 = tts.base64
            audio_mime_type = tts.mime_type
            audio_status = "generated"

        run = repo.agent_runs.create(
            session,
            AgentRun(
                user_id=user.id,
                conversation_id=conversation.id,
                input_source=trigger,
                transcript=text,
                action=decision.action,
                expression=decision.expression,
                speech_text=decision.speech_text,
                tool_summary={"summary": decision.summary, "memory": decision.memory},
                audio_status=audio_status,
            ),
        )
        repo.conversations.touch(session, conversation)

        return TurnResponse(
            conversation_id=conversation.id,
            transcript=text,
            action=decision.action,
            expression=decision.expression,
            animation=decision.animation,
            speech_text=decision.speech_text or None,
            audio_base64=audio_base64,
            audio_mime_type=audio_mime_type,
            debug={
                "agent_run_id": run.id,
                "assistant_message_id": assistant_message_id,
                "summary": decision.summary,
            },
        )

    def handle_audio(
        self,
        session: Session,
        user: User,
        audio_bytes: bytes,
        mime_type: str,
        conversation_id: str | None,
        desktop_state: dict,
    ) -> TurnResponse:
        transcript = self.audio.transcribe(audio_bytes, mime_type).text
        return self.handle_text(
            session=session,
            user=user,
            text=transcript,
            conversation_id=conversation_id,
            desktop_state=desktop_state,
            trigger="voice",
            synthesize=True,
        )

