from __future__ import annotations

from ..services.resource_service import ResourceService
from ..services.question_service import QuestionService
from ..storage.base import Storage

_storage: Storage | None = None
_resource_svc: ResourceService | None = None
_question_svc: QuestionService | None = None


def set_storage(storage: Storage) -> None:
    global _storage, _resource_svc, _question_svc
    _storage = storage
    _resource_svc = ResourceService(storage)
    _question_svc = QuestionService(storage)


def get_resource_service() -> ResourceService:
    assert _resource_svc is not None, "Storage not initialized"
    return _resource_svc


def get_question_service() -> QuestionService:
    assert _question_svc is not None, "Storage not initialized"
    return _question_svc