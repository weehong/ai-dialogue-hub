"""AI service for WorkLog AI - DeepSeek summarization and OpenAI Whisper transcription."""

import io
import logging
from typing import Any, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = """You are an Elite Executive Assistant. Analyze the work logs and create a professional summary in valid Markdown format.

Create a summary with these sections:
1. **High Impact Tasks** - Key accomplishments and significant work items
2. **Timeline** - Chronological overview with clean grammar
3. **Carry-over/Next Steps** - Items that need follow-up or continuation

Keep the summary concise but comprehensive. Use bullet points for clarity."""


class AIService:
    """Service for AI operations - summarization and voice transcription."""

    def __init__(
        self,
        deepseek_api_key: Optional[str] = None,
        deepseek_base_url: str = "https://api.deepseek.com",
        deepseek_model: str = "deepseek-chat",
        openai_api_key: Optional[str] = None,
    ):
        """Initialize AI service with optional DeepSeek and OpenAI clients.

        Args:
            deepseek_api_key: API key for DeepSeek
            deepseek_base_url: Base URL for DeepSeek API
            deepseek_model: Model name for DeepSeek
            openai_api_key: API key for OpenAI (Whisper)
        """
        self.deepseek_client: Optional[OpenAI] = None
        self.openai_client: Optional[OpenAI] = None
        self.deepseek_model = deepseek_model

        if deepseek_api_key:
            self.deepseek_client = OpenAI(
                api_key=deepseek_api_key,
                base_url=deepseek_base_url,
            )
            logger.info(f"DeepSeek client initialized (model: {deepseek_model})")

        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
            logger.info("OpenAI client initialized for Whisper")

    def transcribe_voice(
        self, audio_bytes: bytes, file_format: str = "ogg"
    ) -> Optional[str]:
        """Transcribe voice audio using OpenAI Whisper.

        Args:
            audio_bytes: Audio file bytes
            file_format: Audio format (ogg, mp3, m4a, etc.)

        Returns:
            Transcribed text or None on failure
        """
        if not self.openai_client:
            logger.warning("OpenAI client not configured for transcription")
            return None

        try:
            # Create a file-like object from bytes
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = f"voice.{file_format}"

            response = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
            transcribed_text = response.text.strip()
            logger.info(f"Transcribed voice message: {len(transcribed_text)} chars")
            return transcribed_text

        except Exception as e:
            logger.error(f"Voice transcription failed: {e}")
            return None

    def generate_summary(
        self, logs: list[dict[str, Any]], date_str: str, timezone_str: str
    ) -> Optional[str]:
        """Generate a summary of work logs using DeepSeek.

        Args:
            logs: List of log documents
            date_str: Date string for context
            timezone_str: Timezone string for formatting

        Returns:
            Markdown-formatted summary or None on failure
        """
        if not self.deepseek_client:
            logger.warning("DeepSeek client not configured for summarization")
            return None

        if not logs:
            return None

        try:
            # Import here to avoid circular dependency
            from worklog.services.timezone_service import format_timestamp

            # Format logs into prompt
            log_lines = []
            for log in logs:
                timestamp = format_timestamp(log["timestamp"], timezone_str)
                content = log["content"]
                content_type = log.get("content_type", "text")
                type_indicator = " [voice]" if content_type == "voice" else ""
                log_lines.append(f"[{timestamp}]{type_indicator} - {content}")

            logs_text = "\n".join(log_lines)
            user_prompt = f"Work logs for {date_str}:\n\n{logs_text}"

            response = self.deepseek_client.chat.completions.create(
                model=self.deepseek_model,
                messages=[
                    {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
            )

            summary = response.choices[0].message.content
            logger.info(f"Generated summary for {date_str}")
            return summary

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return None
