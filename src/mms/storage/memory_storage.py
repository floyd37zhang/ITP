from __future__ import annotations

import threading
from datetime import datetime
from typing import Optional

from ..models.resource import Resource, ResourceQuery, ResourceType
from ..models.question import Question
from .base import Storage


def _match_resource(resource: Resource, q: ResourceQuery) -> bool:
    if q.file_path is not None and q.file_path not in resource.file_path:
        return False
    if q.grade is not None and resource.grade != q.grade:
        return False
    if q.subject is not None and resource.subject != q.subject:
        return False
    if q.version is not None and resource.version != q.version:
        return False
    if q.resource_type is not None and resource.resource_type != q.resource_type:
        return False
    if q.knowledge_point is not None and q.knowledge_point not in resource.knowledge_points:
        return False
    if q.difficulty_min is not None and resource.difficulty < q.difficulty_min:
        return False
    if q.difficulty_max is not None and resource.difficulty > q.difficulty_max:
        return False
    if q.class_level is not None and resource.class_level != q.class_level:
        return False
    if q.focus_tag is not None and q.focus_tag not in resource.focus_tags:
        return False
    if q.keyword is not None:
        haystack = " ".join([
            resource.file_name,
            resource.grade,
            resource.subject,
            resource.version,
            " ".join(resource.knowledge_points),
            " ".join(resource.focus_tags),
        ])
        if q.keyword.lower() not in haystack.lower():
            return False
    return True


class MemoryStorage(Storage):

    def __init__(self) -> None:
        self._resources: dict[int, Resource] = {}
        self._resource_path_index: dict[str, int] = {}
        self._questions: dict[int, Question] = {}
        self._lock = threading.RLock()
        self._next_resource_id = 1
        self._next_question_id = 1

    def save_resource(self, resource: Resource) -> Resource:
        with self._lock:
            if resource.id is None:
                resource.id = self._next_resource_id
                self._next_resource_id += 1
            resource.updated_at = datetime.now()
            self._resources[resource.id] = resource
            self._resource_path_index[resource.file_path] = resource.id
            return resource

    def get_resource(self, resource_id: int) -> Optional[Resource]:
        with self._lock:
            r = self._resources.get(resource_id)
            if r is None:
                return None
            return Resource(**r.to_dict())

    def get_resource_by_path(self, file_path: str) -> Optional[Resource]:
        with self._lock:
            rid = self._resource_path_index.get(file_path)
            if rid is None:
                return None
            return self.get_resource(rid)

    def update_resource(self, resource: Resource) -> Resource:
        return self.save_resource(resource)

    def delete_resource(self, resource_id: int) -> bool:
        with self._lock:
            r = self._resources.pop(resource_id, None)
            if r is None:
                return False
            self._resource_path_index.pop(r.file_path, None)
            self.delete_questions_by_resource(resource_id)
            return True

    def delete_resource_by_path(self, file_path: str) -> bool:
        with self._lock:
            rid = self._resource_path_index.get(file_path)
            if rid is None:
                return False
            return self.delete_resource(rid)

    def query_resources(
        self, query: ResourceQuery
    ) -> tuple[list[Resource], int]:
        with self._lock:
            all_items = list(self._resources.values())
            matched = [r for r in all_items if _match_resource(r, query)]
            total = len(matched)
            matched = sorted(matched, key=lambda x: x.updated_at, reverse=True)
            page = matched[query.offset:query.offset + query.limit]
            return [Resource(**r.to_dict()) for r in page], total

    def save_questions(self, questions: list[Question]) -> list[Question]:
        with self._lock:
            saved = []
            for q in questions:
                if q.id is None:
                    q.id = self._next_question_id
                    self._next_question_id += 1
                self._questions[q.id] = q
                saved.append(q)
            return saved

    def get_questions_by_resource(self, resource_id: int) -> list[Question]:
        with self._lock:
            result = [
                Question(**q.to_dict())
                for q in self._questions.values()
                if q.resource_id == resource_id
            ]
            result.sort(key=lambda x: x.order_index)
            return result

    def delete_questions_by_resource(self, resource_id: int) -> int:
        with self._lock:
            to_delete = [
                qid for qid, q in self._questions.items()
                if q.resource_id == resource_id
            ]
            for qid in to_delete:
                del self._questions[qid]
            return len(to_delete)

    def health_check(self) -> bool:
        return True