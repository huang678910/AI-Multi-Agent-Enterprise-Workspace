"""Whisper 音频转录服务"""

import logging
import os
import tempfile

logger = logging.getLogger(__name__)

# Lazy-load Whisper model
_whisper_model = None


def _get_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        # Try small first (461MB, best Chinese quality), fall back to base (138MB)
        for model_name in ["small", "base"]:
            try:
                _whisper_model = whisper.load_model(model_name)
                logger.info(f"Whisper model loaded ({model_name})")
                break
            except Exception as e:
                logger.warning(f"Whisper {model_name} load failed: {e}")
        else:
            logger.warning("Whisper model unavailable. Audio transcription disabled.")
            _whisper_model = False
    return _whisper_model if _whisper_model is not False else None


async def transcribe_audio(file_path: str, language: str | None = None) -> str:
    """Transcribe audio file to text using Whisper

    Args:
        file_path: Path to audio file (.mp3, .wav, .m4a, .ogg)
        language: Optional language code (e.g., "zh", "en", "auto")

    Returns:
        Transcribed text, or empty string on failure
    """
    # Validate file exists and is readable
    if not os.path.exists(file_path):
        logger.error(f"Audio file not found: {file_path}")
        return ""

    file_size = os.path.getsize(file_path)
    if file_size > 25 * 1024 * 1024:  # 25MB limit
        logger.warning(f"Audio file too large: {file_size} bytes")
        return "[Audio file exceeds 25MB size limit]"

    model = _get_model()
    if not model:
        return "[Whisper model not available. Audio transcription requires 'openai-whisper' package.]"

    try:
        import asyncio
        loop = asyncio.get_running_loop()
        # Whisper is CPU-bound, run in thread pool
        result = await loop.run_in_executor(
            None,
            lambda: model.transcribe(file_path, language=language, fp16=False)
        )
        text = result.get("text", "").strip()
        if text:
            logger.info(f"Transcribed {len(text)} chars from {os.path.basename(file_path)}")
        return text
    except Exception as e:
        logger.error(f"Transcription failed for {file_path}: {e}")
        return f"[Transcription failed: {e}]"
