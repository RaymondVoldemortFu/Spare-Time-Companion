import json
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import log_event
from app.models.domain import DesktopState, Memory, Message
from app.schemas.api import AgentDecision


SYSTEM_PROMPT = """你是 Spare-Time Companion 的云端陪伴 Agent。
你面向一个桌面陪伴设备。真实客户端只能播放语音并显示表情，不展示正文。
你需要根据用户输入、近期对话、记忆、反馈和桌面状态，自主决定本轮动作。
你会收到 current_time 上下文。涉及“现在适合做什么”、作息、习惯、卧室/书桌场景时，必须结合当前日期、时间、星期和用户习惯判断。
不要把所有输入都当成推荐任务；可以聊天、追问、确认、记录记忆、建议、重新生成或保持安静。
只输出 JSON，不要输出 Markdown。字段：
action: reply|ask|suggest|remember|confirm|regenerate|silent
speech_text: 适合语音播报的中文短回复，silent 时为空
expression: idle|listening|thinking|speaking|happy|curious|confused|error
animation: idle|pulse|blink|talk|nod|shake|error
memory: 如果用户明确要求记住，或有高置信偏好/愿望，写入一句记忆，否则 null
summary: 简短运行摘要，不要包含链式思考
"""

llm_logger = logging.getLogger("companion.llm")


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

    def decide(
        self,
        user_text: str,
        history: list[Message],
        memories: list[Memory],
        desktop_state: DesktopState | None,
        trigger: str,
    ) -> AgentDecision:
        tz = ZoneInfo(self.settings.APP_TIMEZONE)
        now = datetime.now(tz)
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        context = {
            "current_time": {
                "timezone": self.settings.APP_TIMEZONE,
                "iso": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M"),
                "weekday": now.strftime("%A"),
                "weekday_zh": weekdays[now.weekday()],
                "hour": now.hour,
            },
            "trigger": trigger,
            "recent_history": [{"role": m.role, "content": m.content} for m in history[-12:]],
            "memories": [m.content for m in memories[:20]],
            "desktop_state": desktop_state.state if desktop_state else {},
            "user_input": user_text,
        }
        started = time.perf_counter()
        log_event(
            llm_logger,
            logging.INFO,
            "llm_request_start",
            model=self.settings.MODEL_NAME or "qwen3.7-plus",
            trigger=trigger,
            request_context=context,
            input_chars=len(user_text),
            history_count=len(history),
            memory_count=len(memories),
        )
        try:
            completion = self.client.chat.completions.create(
                model=self.settings.MODEL_NAME or "qwen3.7-plus",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                ],
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"},
                timeout=self.settings.API_TIMEOUT_SECONDS,
            )
            content = completion.choices[0].message.content or ""
            decision = AgentDecision.model_validate_json(content)
            usage = getattr(completion, "usage", None)
            log_event(
                llm_logger,
                logging.INFO,
                "llm_request_success",
                model=self.settings.MODEL_NAME or "qwen3.7-plus",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                action=decision.action,
                expression=decision.expression,
                response=decision.model_dump(),
                output_chars=len(decision.speech_text or ""),
                prompt_tokens=getattr(usage, "prompt_tokens", None),
                completion_tokens=getattr(usage, "completion_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
            )
            return decision
        except (json.JSONDecodeError, ValidationError) as exc:
            log_event(
                llm_logger,
                logging.ERROR,
                "llm_request_bad_output",
                model=self.settings.MODEL_NAME or "qwen3.7-plus",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                error=str(exc),
                raw_response=locals().get("content", ""),
            )
            raise AppError("llm_bad_output", f"LLM returned invalid decision JSON: {exc}", 502) from exc
        except Exception as exc:
            log_event(
                llm_logger,
                logging.ERROR,
                "llm_request_failed",
                model=self.settings.MODEL_NAME or "qwen3.7-plus",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                error=str(exc),
            )
            raise AppError("llm_failed", f"LLM request failed: {exc}", 502) from exc

    def healthcheck(self) -> None:
        started = time.perf_counter()
        log_event(
            llm_logger,
            logging.INFO,
            "llm_healthcheck_start",
            model=self.settings.MODEL_NAME or "qwen3.7-plus",
        )
        try:
            self.client.chat.completions.create(
                model=self.settings.MODEL_NAME or "qwen3.7-plus",
                messages=[
                    {"role": "system", "content": "只输出 JSON。"},
                    {"role": "user", "content": '{"ok": true}'},
                ],
                response_format={"type": "json_object"},
                max_tokens=20,
                timeout=self.settings.API_TIMEOUT_SECONDS,
            )
            log_event(
                llm_logger,
                logging.INFO,
                "llm_healthcheck_success",
                model=self.settings.MODEL_NAME or "qwen3.7-plus",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
        except Exception as exc:
            log_event(
                llm_logger,
                logging.CRITICAL,
                "llm_healthcheck_failed",
                model=self.settings.MODEL_NAME or "qwen3.7-plus",
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                error=str(exc),
            )
            raise AppError("llm_unavailable", f"LLM startup check failed: {exc}", 503) from exc
