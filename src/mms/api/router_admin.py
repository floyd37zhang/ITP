from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends

from .deps import get_resource_service
from ..services.resource_service import ResourceService

router = APIRouter(prefix="/admin", tags=["admin"])


class _ScannerRef:
    scanner = None


_scanner_ref = _ScannerRef()


def set_scanner(scanner) -> None:
    _scanner_ref.scanner = scanner


@router.get("/health")
def health(
    svc: ResourceService = Depends(get_resource_service),
) -> dict:
    return {"status": "ok", "storage": svc.health()}


@router.post("/scan")
def trigger_scan() -> dict:
    scanner = _scanner_ref.scanner
    if scanner is None:
        return {"success": False, "error": "Scanner not initialized"}
    result = scanner.scan_once()
    return {"success": True, **result}