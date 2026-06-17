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
        session, Conversation(user_id=user.id, title="全天候习惯陪伴 demo")
    )
    memories = [
        "设备放在卧室床头柜，用户晚上通常在卧室使用它。",
        "用户早晨 07:30 到 08:30 通常刚醒来，适合轻声问候、天气提醒和 3 分钟拉伸。",
        "用户早晨不喜欢立刻收到复杂任务建议，偏好先喝水、拉开窗帘、听一小段轻音乐。",
        "用户工作日上午 10:30 左右容易久坐，适合提醒站起来活动肩颈或补水。",
        "用户午饭后 13:10 到 13:40 容易犯困，偏好 15 分钟午休或短暂闭眼，不适合安排新任务。",
        "用户下午 15:30 左右注意力下降时，喜欢喝无糖茶并做一个很小的整理任务。",
        "用户傍晚 18:30 到 19:30 通常刚回到卧室或书桌旁，适合建议收拾桌面、换衣服或播放放松音乐。",
        "用户晚上 20:00 到 21:30 如果还在书桌前，通常愿意做轻量复盘或明日计划。",
        "用户工作日 22:00 后喜欢降低屏幕亮度，不希望被强打扰。",
        "用户睡前习惯看 15 到 25 分钟纸质书，偏好轻松散文和科普短文。",
        "用户如果在 23:30 后仍然清醒，通常需要温和提醒准备睡觉。",
        "用户不喜欢睡前高强度运动或复杂任务，偏好安静、低刺激的建议。",
        "用户周末上午更愿意整理房间或洗衣服，但不喜欢被催促。",
        "用户明确表示不喜欢睡前刷短视频，因为容易拖到凌晨。",
        "用户喜欢被用自然语气提醒，不喜欢命令式表达。",
    ]
    for content in memories:
        repo.memories.create(session, Memory(user_id=user.id, content=content, source="demo_seed"))

    states = [
        {
            "label": "morning_bedroom",
            "room": "bedroom",
            "device_location": "bedside_table",
            "ambient_light": "morning_soft",
            "presence": "just_woke_up",
            "idle_minutes": 6,
            "local_time": now.replace(hour=7, minute=48, second=0, microsecond=0).isoformat(),
        },
        {
            "label": "late_morning_desk",
            "room": "study",
            "device_location": "desk_left",
            "ambient_light": "daylight",
            "presence": "at_desk",
            "active_app": "course-notes",
            "idle_minutes": 42,
            "local_time": now.replace(hour=10, minute=36, second=0, microsecond=0).isoformat(),
        },
        {
            "label": "after_lunch",
            "room": "bedroom",
            "device_location": "bedside_table",
            "ambient_light": "daylight_dim",
            "presence": "near_bed",
            "idle_minutes": 15,
            "local_time": now.replace(hour=13, minute=22, second=0, microsecond=0).isoformat(),
        },
        {
            "label": "afternoon_slump",
            "room": "study",
            "device_location": "desk_left",
            "ambient_light": "daylight",
            "presence": "at_desk",
            "active_app": "browser",
            "idle_minutes": 25,
            "local_time": now.replace(hour=15, minute=37, second=0, microsecond=0).isoformat(),
        },
        {
            "label": "evening_transition",
            "room": "bedroom",
            "device_location": "bedside_table",
            "ambient_light": "warm",
            "presence": "in_bedroom",
            "idle_minutes": 8,
            "local_time": now.replace(hour=19, minute=4, second=0, microsecond=0).isoformat(),
        },
        {
            "label": "bedtime_current",
            "room": "bedroom",
            "device_location": "bedside_table",
            "ambient_light": "warm_dim",
            "presence": "in_bedroom",
            "active_app": "none",
            "idle_minutes": 18,
            "is_playing_audio": False,
            "local_time": now.isoformat(),
        },
    ]
    for state in states:
        repo.desktop_states.create(session, DesktopState(user_id=user.id, state=state))

    history = [
        ("user", "早上刚醒，脑子有点懵。"),
        ("assistant", "那我轻一点。先喝两口水、拉开窗帘，再做三分钟肩颈拉伸就好。"),
        ("user", "上午我坐太久会忘记休息。"),
        ("assistant", "我会在你久坐一段时间后，用不打断的方式提醒你活动一下。"),
        ("user", "中午吃完饭我容易困。"),
        ("assistant", "午饭后我优先建议你闭眼休息十五分钟，不安排复杂任务。"),
        ("user", "下午三四点我经常开始乱刷网页。"),
        ("assistant", "这个时段我可以建议你泡杯无糖茶，再做一个两分钟能完成的小整理。"),
        ("user", "晚上回到卧室的时候，我想先安静下来。"),
        ("assistant", "傍晚回卧室后，我会先给你低刺激的放松建议，比如换衣服、整理床头或放轻音乐。"),
        ("user", "晚上八九点如果还没结束，我可以做一点复盘。"),
        ("assistant", "好的，20:00 到 21:30 我会把轻量复盘和明日计划作为优先选项。"),
        ("user", "我最近晚上总是刷手机刷太久。"),
        ("assistant", "我记一下：晚上如果你已经在卧室，可以优先提醒你做低刺激的放松活动。"),
        ("user", "我睡前看纸质书会更容易放松。"),
        ("assistant", "好的，我会把睡前阅读作为你的晚间偏好。"),
        ("user", "如果都快十二点了，你就温柔提醒我睡觉。"),
        ("assistant", "明白，23:30 以后我会更偏向温和收尾，不再建议新的活动。"),
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
            "states": len(states),
            "state": "all_day_habits",
            "time": now.isoformat(),
        },
    }
