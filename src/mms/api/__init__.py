from .deps import get_resource_service, get_question_service
from .router_resources import router as resources_router
from .router_questions import router as questions_router
from .router_admin import router as admin_router

__all__ = [
    "get_resource_service",
    "get_question_service",
    "resources_router",
    "questions_router",
    "admin_router",
]