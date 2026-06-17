import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.aliyun_audio import AliyunAudioClient
from app.services.llm import LLMClient


def main() -> None:
    configure_logging()
    settings = get_settings()
    print(f"Checking LLM model: {settings.MODEL_NAME or 'qwen3.7-plus'}")
    LLMClient(settings).healthcheck()
    print("LLM OK")

    print(f"Checking TTS model: {settings.VOICE_MODEL}, voice: {settings.TTS_VOICE}")
    tts = AliyunAudioClient(settings).synthesize("你好，这是语音合成可用性检查。")
    print(f"TTS OK, bytes={len(tts.audio)}, mime={tts.mime_type}")


if __name__ == "__main__":
    main()
