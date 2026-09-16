from __future__ import annotations

from typing import Optional

from lib.logger import get_logger

from ..models.question import Question, QuestionType
from ..storage.base import Storage

log = get_logger("mms.services.question")


class QuestionService:

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def batch_save(self, questions: list[Question]) -> list[Question]:
        if not questions:
            return []
        return self._storage.save_questions(questions)

    def list_by_resource(self, resource_id: int) -> list[Question]:
        return self._storage.get_questions_by_resource(resource_id)

    def delete_by_resource(self, resource_id: int) -> int:
        return self._storage.delete_questions_by_resource(resource_id)

    def select_for_paper(
        self,
        grade: str,
        subject: str,
        knowledge_points: Optional[list[str]] = None,
        question_type: Optional[QuestionType] = None,
        difficulty_min: Optional[int] = None,
        difficulty_max: Optional[int] = None,
        exclude_resource_ids: Optional[list[int]] = None,
        limit: int = 100,
    ) -> list[Question]:
        from ..models.resource import ResourceQuery, ResourceType

        res_q = ResourceQuery(
            grade=grade,
            subject=subject,
            limit=500,
        )
        resources, _ = self._storage.query_resources(res_q)

        selected: list[Question] = []
        for r in resources:
            if exclude_resource_ids and r.id in exclude_resource_ids:
                continue
            questions = self._storage.get_questions_by_resource(r.id)
            for q in questions:
                if question_type and q.question_type != question_type:
                    continue
                if difficulty_min is not None and q.difficulty < difficulty_min:
                    continue
                if difficulty_max is not None and q.difficulty > difficulty_max:
                    continue
                if knowledge_points:
                    if not any(kp in q.knowledge_points for kp in knowledge_points):
                        continue
                selected.append(q)
                if len(selected) >= limit:
                    return selected
        return selected