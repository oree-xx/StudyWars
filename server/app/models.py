from typing import List

from pydantic import BaseModel, Field


class Question(BaseModel):
    """A single multiple-choice quiz question."""

    question: str
    options: List[str] = Field(
        min_length=4, max_length=4, description="Exactly 4 answer options."
    )
    correct_index: int = Field(
        ge=0, le=3, description="Index (0-3) of the correct option in `options`."
    )
    explanation: str = Field(description="Short explanation of why the answer is correct.")


class QuestionSet(BaseModel):
    """The shape Claude is asked to return — a flat list of questions."""

    questions: List[Question]


class GenerateQuestionsResponse(BaseModel):
    questions: List[Question]
