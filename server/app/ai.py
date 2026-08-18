import anthropic

from app.config import settings
from app.models import Question, QuestionSet

MODEL = "claude-opus-5"

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    """Lazily construct the Anthropic client so a missing key doesn't crash the app at import time."""
    global _client
    if _client is None:
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy server/.env.example to server/.env "
                "and add your key from https://console.anthropic.com/"
            )
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def generate_questions(source_text: str, num_questions: int = 5) -> list[Question]:
    """Ask Claude to turn study notes into a set of multiple-choice quiz questions."""
    prompt = f"""You are creating a multiple-choice quiz for a live classroom game, based on the study notes below.

Generate exactly {num_questions} multiple-choice questions that test understanding of the key concepts in these notes.

Rules:
- Each question has exactly 4 answer options.
- Only one option is correct.
- The 3 incorrect options should be plausible, not obviously wrong.
- Questions should cover a range of concepts from the notes, not just the first paragraph.
- Keep each question and option concise enough to read quickly on a screen.
- Include a short explanation of why the correct answer is right.

Study notes:
---
{source_text}
---"""

    response = get_client().messages.parse(
        model=MODEL,
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
        output_format=QuestionSet,
    )

    return response.parsed_output.questions
