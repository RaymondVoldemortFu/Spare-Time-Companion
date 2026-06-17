import base64
import logging
import os
import time
import wave
from dataclasses import dataclass, field
from io import BytesIO
from threading import Event

import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
from dashscope.audio.tts_v2 import SpeechSynthesizer

from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import log_event


@dataclass
class SpeechResult:
    text: str


@dataclass
class TTSResult:
    audio: bytes
    mime_type: str = "audio/mpeg"

    @property
    def base64(self) -> str:
        return base64.b64encode(self.audio).decode("ascii")


@dataclass
class _ASRCallback(RecognitionCallback):
    done: Event = field(default_factory=Event)
    sentences: list[str] = field(default_factory=list)
    error: str | None = None

    def on_complete(self) -> None:
        self.done.set()

    def on_close(self) -> None:
        self.done.set()

    def on_error(self, result: RecognitionResult) -> None:
        self.error = str(result)
        self.done.set()

    def on_event(self, result: RecognitionResult) -> None:
        sentence = result.get_sentence()
        if sentence and result.is_sentence_end():
            text = sentence.get("text")
            if text:
                self.sentences.append(text)


def _decode_wav_pcm(audio: bytes) -> tuple[bytes, int]:
    try:
        with wave.open(BytesIO(audio), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            if channels != 1 or sample_width != 2:
                raise AppError(
                    "invalid_audio",
                    "Audio must be mono 16-bit WAV PCM for ASR",
                    400,
                )
            return wav.readframes(wav.getnframes()), sample_rate
    except wave.Error as exc:
        raise AppError("invalid_audio", "Audio must be a valid WAV file", 400) from exc


class AliyunAudioClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        dashscope.api_key = settings.ALI_API_KEY
        os.environ["DASHSCOPE_API_KEY"] = settings.ALI_API_KEY

    def transcribe(self, audio: bytes, mime_type: str) -> SpeechResult:
        asr_logger = logging.getLogger("companion.asr")
        started = time.perf_counter()
        log_event(
            asr_logger,
            logging.INFO,
            "asr_request_start",
            model=self.settings.ASR_MODEL,
            mime_type=mime_type,
            byte_size=len(audio),
        )
        if len(audio) > self.settings.MAX_AUDIO_BYTES:
            log_event(
                asr_logger,
                logging.WARNING,
                "asr_request_rejected",
                model=self.settings.ASR_MODEL,
                reason="audio_too_large",
                byte_size=len(audio),
            )
            raise AppError("audio_too_large", "Audio payload is too large", 413)
        if "wav" not in mime_type and "wave" not in mime_type:
            log_event(
                asr_logger,
                logging.WARNING,
                "asr_request_rejected",
                model=self.settings.ASR_MODEL,
                reason="invalid_mime_type",
                mime_type=mime_type,
            )
            raise AppError("invalid_audio", "Only WAV audio is accepted by this demo", 400)

        pcm, sample_rate = _decode_wav_pcm(audio)
        callback = _ASRCallback()
        recognizer = Recognition(
            model=self.settings.ASR_MODEL,
            callback=callback,
            format="pcm",
            sample_rate=sample_rate,
        )
        try:
            recognizer.start()
            chunk_size = max(sample_rate // 10 * 2, 3200)
            for index in range(0, len(pcm), chunk_size):
                recognizer.send_audio_frame(pcm[index : index + chunk_size])
            recognizer.stop()
            callback.done.wait(timeout=self.settings.API_TIMEOUT_SECONDS)
        except Exception as exc:
            log_event(
                asr_logger,
                logging.ERROR,
                "asr_request_failed",
                model=self.settings.ASR_MODEL,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                sample_rate=sample_rate,
                pcm_bytes=len(pcm),
                error=str(exc),
            )
            raise AppError("asr_failed", f"Aliyun ASR failed: {exc}", 502) from exc

        if callback.error:
            log_event(
                asr_logger,
                logging.ERROR,
                "asr_request_failed",
                model=self.settings.ASR_MODEL,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                sample_rate=sample_rate,
                pcm_bytes=len(pcm),
                error=callback.error,
            )
            raise AppError("asr_failed", f"Aliyun ASR failed: {callback.error}", 502)
        text = "".join(callback.sentences).strip()
        if not text:
            log_event(
                asr_logger,
                logging.WARNING,
                "asr_request_empty",
                model=self.settings.ASR_MODEL,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                sample_rate=sample_rate,
                pcm_bytes=len(pcm),
            )
            raise AppError("asr_empty", "Aliyun ASR returned no transcript", 422)
        log_event(
            asr_logger,
            logging.INFO,
            "asr_request_success",
            model=self.settings.ASR_MODEL,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            sample_rate=sample_rate,
            pcm_bytes=len(pcm),
            transcript_chars=len(text),
            transcript=text,
        )
        return SpeechResult(text=text)

    def synthesize(self, text: str) -> TTSResult:
        tts_logger = logging.getLogger("companion.tts")
        started = time.perf_counter()
        log_event(
            tts_logger,
            logging.INFO,
            "tts_request_start",
            model=self.settings.VOICE_MODEL,
            voice=self.settings.TTS_VOICE,
            text_chars=len(text),
            text=text,
        )
        if not text.strip():
            log_event(
                tts_logger,
                logging.WARNING,
                "tts_request_rejected",
                model=self.settings.VOICE_MODEL,
                voice=self.settings.TTS_VOICE,
                reason="empty_text",
            )
            raise AppError("tts_empty_text", "TTS text is empty", 400)
        try:
            synthesizer = SpeechSynthesizer(
                model=self.settings.VOICE_MODEL,
                voice=self.settings.TTS_VOICE,
            )
            audio = synthesizer.call(text, timeout_millis=int(self.settings.API_TIMEOUT_SECONDS * 1000))
        except Exception as exc:
            log_event(
                tts_logger,
                logging.ERROR,
                "tts_request_failed",
                model=self.settings.VOICE_MODEL,
                voice=self.settings.TTS_VOICE,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                error=str(exc),
            )
            raise AppError("tts_failed", f"Aliyun TTS failed: {exc}", 502) from exc
        if not audio:
            log_event(
                tts_logger,
                logging.ERROR,
                "tts_request_failed",
                model=self.settings.VOICE_MODEL,
                voice=self.settings.TTS_VOICE,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                error="empty_audio",
            )
            raise AppError("tts_failed", "Aliyun TTS returned empty audio", 502)
        log_event(
            tts_logger,
            logging.INFO,
            "tts_request_success",
            model=self.settings.VOICE_MODEL,
            voice=self.settings.TTS_VOICE,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            audio_bytes=len(audio),
            mime_type="audio/mpeg",
            text=text,
        )
        return TTSResult(audio=audio)

    def healthcheck(self) -> None:
        # TTS is the cheapest reliable audio-side startup check. ASR is validated on upload
        # because it requires real user audio.
        self.synthesize("启动检查")
