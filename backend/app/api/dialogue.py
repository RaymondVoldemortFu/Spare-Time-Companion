import json
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.core.errors import AppError
from app.crud import repositories as repo
from app.models.domain import Conversation, DesktopState, Feedback, Memory, Message
from app.schemas.api import (
    DesktopStateRequest,
    FeedbackRequest,
    HistoryItem,
    TextTurnRequest,
    TriggerRequest,
    TurnResponse,
)
from app.services.dialogue import DialogueService
from app.services.factory import get_dialogue_service


router = APIRouter(prefix="/companion", tags=["companion"])


@router.post("/turn/text", response_model=TurnResponse)
def text_turn(
    payload: TextTurnRequest,
    session: SessionDep,
    user: CurrentUser,
    service: DialogueService = Depends(get_dialogue_service),
) -> TurnResponse:
    return service.handle_text(
        session=session,
        user=user,
        text=payload.text,
        conversation_id=payload.conversation_id,
        desktop_state=payload.desktop_state,
        trigger=payload.trigger,
    )


@router.post("/turn/trigger", response_model=TurnResponse)
def trigger_turn(
    payload: TriggerRequest,
    session: SessionDep,
    user: CurrentUser,
    service: DialogueService = Depends(get_dialogue_service),
) -> TurnResponse:
    return service.handle_text(
        session=session,
        user=user,
        text=f"[主动触发事件: {payload.trigger}]",
        conversation_id=payload.conversation_id,
        desktop_state=payload.desktop_state,
        trigger=payload.trigger,
    )


@router.post("/turn/audio", response_model=TurnResponse)
async def audio_turn(
    session: SessionDep,
    user: CurrentUser,
    file: UploadFile = File(...),
    conversation_id: str | None = Form(default=None),
    desktop_state_json: str = Form(default="{}"),
    service: DialogueService = Depends(get_dialogue_service),
) -> TurnResponse:
    try:
        desktop_state = json.loads(desktop_state_json)
    except json.JSONDecodeError as exc:
        raise AppError("bad_desktop_state", "desktop_state_json must be valid JSON", 400) from exc
    data = await file.read()
    return service.handle_audio(
        session=session,
        user=user,
        audio_bytes=data,
        mime_type=file.content_type or "audio/wav",
        conversation_id=conversation_id,
        desktop_state=desktop_state,
    )


@router.post("/state")
def report_state(payload: DesktopStateRequest, session: SessionDep, user: CurrentUser) -> dict:
    item = repo.desktop_states.create(
        session,
        DesktopState(user_id=user.id, device_id=payload.device_id, state=payload.state),
    )
    return {"id": item.id, "created_at": item.created_at}


@router.post("/feedback")
def feedback(payload: FeedbackRequest, session: SessionDep, user: CurrentUser) -> dict:
    item = repo.feedbacks.create(
        session,
        Feedback(
            user_id=user.id,
            conversation_id=payload.conversation_id,
            message_id=payload.message_id,
            kind=payload.kind,
            note=payload.note,
        ),
    )
    if payload.kind in {"negative", "regenerate", "dismiss"} and payload.note:
        repo.memories.create(
            session,
            Memory(user_id=user.id, content=f"用户反馈：{payload.note}", source="feedback"),
        )
    return {"id": item.id}


@router.get("/history", response_model=list[HistoryItem])
def history(session: SessionDep, user: CurrentUser, limit: int = 100) -> list[HistoryItem]:
    return [
        HistoryItem(
            id=item.id,
            role=item.role,
            content=item.content,
            source=item.source,
            created_at=item.created_at,
        )
        for item in repo.messages.by_user(session, user.id, limit=limit)
    ]


@router.get("/memories")
def memories(session: SessionDep, user: CurrentUser) -> list[dict]:
    return [
        {"id": item.id, "content": item.content, "source": item.source, "created_at": item.created_at}
        for item in repo.memories.recent_for_user(session, user.id)
    ]


@router.get("/agent-runs")
def agent_runs(session: SessionDep, user: CurrentUser) -> list[dict]:
    return [
        {
            "id": item.id,
            "conversation_id": item.conversation_id,
            "action": item.action,
            "expression": item.expression,
            "speech_text": item.speech_text,
            "tool_summary": item.tool_summary,
            "audio_status": item.audio_status,
            "created_at": item.created_at,
        }
        for item in repo.agent_runs.recent(session, user.id)
    ]


@router.post("/demo/reset")
def reset_demo(session: SessionDep, user: CurrentUser) -> dict:
    repo.clear_user_demo_data(session, user.id)
    return {"ok": True}


@router.post("/demo/sample")
def sample_demo(session: SessionDep, user: CurrentUser) -> dict:
    repo.clear_user_demo_data(session, user.id)
    settings = get_settings()
    now = datetime.now(ZoneInfo(settings.APP_TIMEZONE))
    conversation = repo.conversations.create(
        session, Conversation(user_id=user.id, title="卧室晚间陪伴 demo")
    )
    memories = [
        "设备放在卧室床头柜，用户晚上通常在卧室使用它。",
        "用户工作日 22:00 后喜欢降低屏幕亮度，不希望被强打扰。",
        "用户睡前习惯看 15 到 25 分钟纸质书，偏好轻松散文和科普短文。",
        "用户如果在 23:30 后仍然清醒，通常需要温和提醒准备睡觉。",
        "用户不喜欢睡前高强度运动或复杂任务，偏好安静、低刺激的建议。",
    ]
    for content in memories:
        repo.memories.create(session, Memory(user_id=user.id, content=content, source="demo_seed"))

    repo.desktop_states.create(
        session,
        DesktopState(
            user_id=user.id,
            state={
                "room": "bedroom",
                "device_location": "bedside_table",
                "ambient_light": "warm_dim",
                "presence": "in_bedroom",
                "active_app": "none",
                "idle_minutes": 18,
                "is_playing_audio": False,
                "local_time": now.isoformat(),
            },
        ),
    )
    history = [
        ("user", "我最近晚上总是刷手机刷太久。"),
        ("assistant", "我记一下：晚上如果你已经在卧室，可以优先提醒你做低刺激的放松活动。"),
        ("user", "我睡前看纸质书会更容易放松。"),
        ("assistant", "好的，我会把睡前阅读作为你的晚间偏好。"),
    ]
    for role, content in history:
        repo.messages.create(
            session,
            Message(
                conversation_id=conversation.id,
                user_id=user.id,
                role=role,
                content=content,
                source="demo_seed",
            ),
        )

    prompt = (
        f"现在是{now.strftime('%H:%M')}，我在卧室，有点想放松一下。"
        "按照我的习惯，现在适合做什么？"
    )
    return {
        "ok": True,
        "conversation_id": conversation.id,
        "prompt": prompt,
        "seeded": {
            "memories": len(memories),
            "messages": len(history),
            "state": "bedroom_evening",
            "time": now.isoformat(),
        },
    }
