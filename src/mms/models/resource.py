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


class ResourceType(str, Enum):
    LESSON_PLAN = "lesson_plan"
    EXAM_PAPER = "exam_paper"
    IMAGE = "image"


@dataclass
class Resource:
    id: Optional[int] = None
    file_path: str = ""
    file_name: str = ""
    file_extension: str = ""

    grade: str = ""
    subject: str = ""
    version: str = ""

    resource_type: ResourceType = ResourceType.LESSON_PLAN
    knowledge_points: list[str] = field(default_factory=list)
    difficulty: int = 3
    class_level: str = ""
    focus_tags: list[str] = field(default_factory=list)

    file_size: int = 0
    file_hash: str = ""

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if isinstance(self.resource_type, str):
            self.resource_type = ResourceType(self.resource_type)
        self.created_at = _coerce_dt(self.created_at)
        self.updated_at = _coerce_dt(self.updated_at)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_extension": self.file_extension,
            "grade": self.grade,
            "subject": self.subject,
            "version": self.version,
            "resource_type": self.resource_type.value,
            "knowledge_points": self.knowledge_points,
            "difficulty": self.difficulty,
            "class_level": self.class_level,
            "focus_tags": self.focus_tags,
            "file_size": self.file_size,
            "file_hash": self.file_hash,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class ResourceQuery:
    file_path: Optional[str] = None
    grade: Optional[str] = None
    subject: Optional[str] = None
    version: Optional[str] = None
    resource_type: Optional[ResourceType] = None
    knowledge_point: Optional[str] = None
    difficulty_min: Optional[int] = None
    difficulty_max: Optional[int] = None
    class_level: Optional[str] = None
    focus_tag: Optional[str] = None
    keyword: Optional[str] = None
    limit: int = 100
    offset: int = 0