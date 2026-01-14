"""AI service for generating topic titles."""

import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

TITLE_PROMPT = """Generate a concise topic title (max 60 characters) for a forum discussion based on the user's message.
Return ONLY the title, nothing else. No quotes, no explanation.
The title should capture the main subject or question."""

WORKLOG_SUMMARY_PROMPT = """You are a professional work log formatter. Given a list of work entries, generate a clean, well-organized work log summary.

Format the output as:
- Group related tasks together if applicable
- Use clear, professional language
- Include a brief summary section at the end
- Keep the tone professional but concise

Output in Markdown format suitable for documentation."""


class AIService:
    """Service for AI-powered features like title generation."""

    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name

    def generate_topic_title(self, message: str) -> str:
        """Generate a concise topic title from a message.

        Args:
            message: The user's message to base the title on

        Returns:
            A concise topic title (max 60 chars)
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": TITLE_PROMPT},
                    {"role": "user", "content": message},
                ],
                max_tokens=50,
                temperature=0.3,
            )
            title = response.choices[0].message.content.strip()
            # Ensure max length
            if len(title) > 60:
                title = title[:57] + "..."
            return title
        except Exception as e:
            logger.error(f"AI title generation failed: {e}")
            # Fallback to truncation
            return (message[:57] + "...") if len(message) > 60 else message

    def generate_worklog_summary(self, entries: str) -> str:
        """Generate a formatted work log summary from entries.

        Args:
            entries: The formatted work log entries

        Returns:
            A professionally formatted work log summary
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": WORKLOG_SUMMARY_PROMPT},
                    {"role": "user", "content": entries},
                ],
                max_tokens=1000,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI work log summary generation failed: {e}")
            # Fallback to raw entries
            return f"**Work Log Summary**\n\n{entries}"
