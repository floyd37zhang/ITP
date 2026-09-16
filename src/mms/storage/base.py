from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..models.resource import Resource, ResourceQuery
from ..models.question import Question


class Storage(ABC):

    @abstractmethod
    def save_resource(self, resource: Resource) -> Resource: ...

    @abstractmethod
    def get_resource(self, resource_id: int) -> Optional[Resource]: ...

    @abstractmethod
    def get_resource_by_path(self, file_path: str) -> Optional[Resource]: ...

    @abstractmethod
    def update_resource(self, resource: Resource) -> Resource: ...

    @abstractmethod
    def delete_resource(self, resource_id: int) -> bool: ...

    @abstractmethod
    def delete_resource_by_path(self, file_path: str) -> bool: ...

    @abstractmethod
    def query_resources(
        self, query: ResourceQuery
    ) -> tuple[list[Resource], int]: ...

    @abstractmethod
    def save_questions(self, questions: list[Question]) -> list[Question]: ...

    @abstractmethod
    def get_questions_by_resource(self, resource_id: int) -> list[Question]: ...

    @abstractmethod
    def delete_questions_by_resource(self, resource_id: int) -> int: ...

    @abstractmethod
    def health_check(self) -> bool: ...