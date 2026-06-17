from functools import lru_cache

from app.core.config import get_settings
from app.services.aliyun_audio import AliyunAudioClient
from app.services.dialogue import DialogueService
from app.services.llm import LLMClient


@lru_cache
def get_llm_client() -> LLMClient:
    return LLMClient(get_settings())


@lru_cache
def get_audio_client() -> AliyunAudioClient:
    return AliyunAudioClient(get_settings())


@lru_cache
def get_dialogue_service() -> DialogueService:
    return DialogueService(get_llm_client(), get_audio_client())

