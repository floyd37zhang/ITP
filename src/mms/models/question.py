from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


def _coerce_dt(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return datetime.now()


class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    CALCULATION = "calculation"
    PROOF = "proof"
    DRAWING = "drawing"
    MATCHING = "matching"
    OTHER = "other"


@dataclass
class Question:
    id: Optional[int] = None
    resource_id: int = 0
    order_index: int = 0

    question_type: QuestionType = QuestionType.OTHER
    content: str = ""
    options: list[str] = field(default_factory=list)
    answer: str = ""
    analysis: str = ""
    score: float = 5.0

    knowledge_points: list[str] = field(default_factory=list)
    difficulty: int = 3

    images: list[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if isinstance(self.question_type, str):
            self.question_type = QuestionType(self.question_type)
        self.created_at = _coerce_dt(self.created_at)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "order_index": self.order_index,
            "question_type": self.question_type.value,
            "content": self.content,
            "options": self.options,
            "answer": self.answer,
            "analysis": self.analysis,
            "score": self.score,
            "knowledge_points": self.knowledge_points,
            "difficulty": self.difficulty,
            "images": self.images,
            "created_at": self.created_at.isoformat(),
        }