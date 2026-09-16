from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .deps import get_resource_service
from ..models.resource import Resource, ResourceType
from ..services.resource_service import ResourceService

router = APIRouter(prefix="/resources", tags=["resources"])


class ResourceCreate(BaseModel):
    file_path: str = Field(..., min_length=1)
    grade: str = ""
    subject: str = ""
    version: str = ""
    resource_type: ResourceType = ResourceType.LESSON_PLAN
    knowledge_points: list[str] = Field(default_factory=list)
    difficulty: int = Field(3, ge=1, le=5)
    class_level: str = ""
    focus_tags: list[str] = Field(default_factory=list)


class ResourceUpdate(BaseModel):
    grade: Optional[str] = None
    subject: Optional[str] = None
    version: Optional[str] = None
    resource_type: Optional[ResourceType] = None
    knowledge_points: Optional[list[str]] = None
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    class_level: Optional[str] = None
    focus_tags: Optional[list[str]] = None


@router.post("", response_model=dict)
def create_resource(
    body: ResourceCreate,
    svc: ResourceService = Depends(get_resource_service),
) -> dict:
    resource = Resource(**body.model_dump())
    result = svc.create(resource)
    return result.to_dict()


@router.get("/{resource_id}", response_model=dict)
def get_resource(
    resource_id: int,
    svc: ResourceService = Depends(get_resource_service),
) -> dict:
    resource = svc.get(resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource.to_dict()


@router.put("/{resource_id}", response_model=dict)
def update_resource(
    resource_id: int,
    body: ResourceUpdate,
    svc: ResourceService = Depends(get_resource_service),
) -> dict:
    existing = svc.get(resource_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(existing, key, value)

    result = svc.update(existing)
    if result is None:
        raise HTTPException(status_code=404, detail="Update failed")
    return result.to_dict()


@router.delete("/{resource_id}", response_model=dict)
def delete_resource(
    resource_id: int,
    svc: ResourceService = Depends(get_resource_service),
) -> dict:
    ok = svc.delete(resource_id)
    return {"success": ok}


@router.get("", response_model=dict)
def search_resources(
    file_path: Optional[str] = None,
    grade: Optional[str] = None,
    subject: Optional[str] = None,
    version: Optional[str] = None,
    resource_type: Optional[ResourceType] = None,
    knowledge_point: Optional[str] = None,
    difficulty_min: Optional[int] = Query(None, ge=1, le=5),
    difficulty_max: Optional[int] = Query(None, ge=1, le=5),
    class_level: Optional[str] = None,
    focus_tag: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    svc: ResourceService = Depends(get_resource_service),
) -> dict:
    from ..models.resource import ResourceQuery
    query = ResourceQuery(
        file_path=file_path,
        grade=grade,
        subject=subject,
        version=version,
        resource_type=resource_type,
        knowledge_point=knowledge_point,
        difficulty_min=difficulty_min,
        difficulty_max=difficulty_max,
        class_level=class_level,
        focus_tag=focus_tag,
        keyword=keyword,
        limit=limit,
        offset=offset,
    )
    items, total = svc.search(query)
    return {
        "items": [r.to_dict() for r in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }