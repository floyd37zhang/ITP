from __future__ import annotations

import os
from typing import Optional

from lib.logger import get_logger

from ..models.resource import Resource, ResourceQuery, ResourceType
from ..storage.base import Storage

log = get_logger("mms.services.resource")


class ResourceService:

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def create(self, resource: Resource) -> Resource:
        existing = self._storage.get_resource_by_path(resource.file_path)
        if existing:
            resource.id = existing.id
            log.info(
                "Overwriting existing resource id=%d for %s",
                existing.id, resource.file_path,
            )
        return self._storage.save_resource(resource)

    def get(self, resource_id: int) -> Optional[Resource]:
        return self._storage.get_resource(resource_id)

    def get_by_path(self, file_path: str) -> Optional[Resource]:
        return self._storage.get_resource_by_path(file_path)

    def update(self, resource: Resource) -> Optional[Resource]:
        if resource.id is None:
            existing = self._storage.get_resource_by_path(resource.file_path)
            if existing:
                resource.id = existing.id
            else:
                return None
        return self._storage.save_resource(resource)

    def delete(self, resource_id: int) -> bool:
        return self._storage.delete_resource(resource_id)

    def delete_by_path(self, file_path: str) -> bool:
        return self._storage.delete_resource_by_path(file_path)

    def search(self, query: ResourceQuery) -> tuple[list[Resource], int]:
        return self._storage.query_resources(query)

    def list_by_grade_subject(
        self, grade: str, subject: str
    ) -> list[Resource]:
        q = ResourceQuery(grade=grade, subject=subject, limit=1000)
        items, _ = self._storage.query_resources(q)
        return items

    def filter_for_lesson_plans(
        self,
        grade: Optional[str] = None,
        subject: Optional[str] = None,
        version: Optional[str] = None,
        knowledge_point: Optional[str] = None,
        focus_tag: Optional[str] = None,
        class_level: Optional[str] = None,
        limit: int = 50,
    ) -> list[Resource]:
        q = ResourceQuery(
            grade=grade,
            subject=subject,
            version=version,
            knowledge_point=knowledge_point,
            focus_tag=focus_tag,
            class_level=class_level,
            resource_type=ResourceType.LESSON_PLAN,
            limit=limit,
        )
        items, _ = self._storage.query_resources(q)
        return items

    def health(self) -> bool:
        return self._storage.health_check()