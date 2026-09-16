from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .deps import get_question_service, get_resource_service
from ..models.question import Question, QuestionType
from ..services.question_service import QuestionService
from ..services.resource_service import ResourceService

router = APIRouter(prefix="/questions", tags=["questions"])


class QuestionBatchCreate(BaseModel):
    resource_id: int
    order_index: int = 0
    question_type: QuestionType = QuestionType.OTHER
    content: str = ""
    options: list[str] = Field(default_factory=list)
    answer: str = ""
    analysis: str = ""
    score: float = 5.0
    knowledge_points: list[str] = Field(default_factory=list)
    difficulty: int = Field(3, ge=1, le=5)


class QuestionPaperSelect(BaseModel):
    grade: str
    subject: str
    knowledge_points: Optional[list[str]] = None
    question_type: Optional[QuestionType] = None
    difficulty_min: Optional[int] = Field(default=None, ge=1, le=5)
    difficulty_max: Optional[int] = Field(default=None, ge=1, le=5)
    exclude_resource_ids: Optional[list[int]] = None
    limit: int = Field(100, ge=1, le=500)


@router.post("", response_model=dict)
def batch_create_questions(
    body: list[QuestionBatchCreate],
    qsvc: QuestionService = Depends(get_question_service),
) -> dict:
    questions = [Question(**q.model_dump()) for q in body]
    saved = qsvc.batch_save(questions)
    return {"saved": len(saved), "ids": [q.id for q in saved]}


@router.get("/by-resource/{resource_id}", response_model=dict)
def list_questions_by_resource(
    resource_id: int,
    qsvc: QuestionService = Depends(get_question_service),
    rsvc: ResourceService = Depends(get_resource_service),
) -> dict:
    resource = rsvc.get(resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    questions = qsvc.list_by_resource(resource_id)
    return {
        "resource": resource.to_dict(),
        "questions": [q.to_dict() for q in questions],
    }


@router.delete("/by-resource/{resource_id}", response_model=dict)
def delete_questions_by_resource(
    resource_id: int,
    qsvc: QuestionService = Depends(get_question_service),
) -> dict:
    count = qsvc.delete_by_resource(resource_id)
    return {"deleted": count}


@router.post("/select-for-paper", response_model=dict)
def select_questions_for_paper(
    body: QuestionPaperSelect,
    qsvc: QuestionService = Depends(get_question_service),
) -> dict:
    questions = qsvc.select_for_paper(
        grade=body.grade,
        subject=body.subject,
        knowledge_points=body.knowledge_points,
        question_type=body.question_type,
        difficulty_min=body.difficulty_min,
        difficulty_max=body.difficulty_max,
        exclude_resource_ids=body.exclude_resource_ids,
        limit=body.limit,
    )
    return {
        "questions": [q.to_dict() for q in questions],
        "total": len(questions),
    }