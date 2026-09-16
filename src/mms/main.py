from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lib.logger import get_logger, LogConfig
from lib.mysql_config import MySQLConfig

from .config import AppConfig
from .api import deps as api_deps
from .api.router_resources import router as resources_router
from .api.router_questions import router as questions_router
from .api.router_admin import router as admin_router, set_scanner
from .storage.base import Storage
from .storage.memory_storage import MemoryStorage
from .storage.mysql_storage import MySQLStorage
from .parsers.base import FileParser
from .parsers.word_parser import WordParser
from .parsers.pdf_parser import PdfParser
from .parsers.image_parser import ImageParser
from .scanner.file_scanner import FileScanner, compute_file_hash
from .watcher.file_watcher import FileWatcher

log = get_logger("mms")

PARSER_MAP: dict[str, FileParser] = {
    ".doc": WordParser(),
    ".docx": WordParser(),
    ".pdf": PdfParser(),
    ".png": ImageParser(),
    ".jpg": ImageParser(),
    ".jpeg": ImageParser(),
    ".gif": ImageParser(),
    ".bmp": ImageParser(),
    ".tiff": ImageParser(),
}


def _build_storage(config: AppConfig) -> Storage:
    if config.storage_backend == "mysql":
        log.info("Using MySQL storage backend")
        return MySQLStorage(config.mysql)
    log.info("Using in-memory storage backend (default)")
    return MemoryStorage()


def _build_app(config: AppConfig) -> tuple[FastAPI, FileScanner, FileWatcher | None]:
    storage = _build_storage(config)
    api_deps.set_storage(storage)

    app = FastAPI(
        title="MMS - 教学资源管理系统",
        version="0.1.0",
        description="教学资源元数据管理 + 试题提取 + 文件扫描",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(resources_router, prefix="/api/v1")
    app.include_router(questions_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")

    parsers = {
        ext: PARSER_MAP[ext]
        for ext in config.supported_extensions
        if ext in PARSER_MAP
    }

    scanner = FileScanner(
        storage=storage,
        parsers=parsers,
        supported_extensions=config.supported_extensions,
        scan_paths=config.scan_paths,
        scan_interval=config.scan_interval_seconds,
    )
    set_scanner(scanner)

    watcher: FileWatcher | None = None
    if config.enable_watcher:
        watcher = FileWatcher(
            watch_paths=config.scan_paths,
            on_created=scanner.scan_once,
            on_modified=scanner.scan_once,
            on_deleted=scanner.scan_once,
        )

    @app.on_event("startup")
    async def on_startup() -> None:
        log.info("MMS starting up")
        scanner.scan_once()
        scanner.run_forever()
        if watcher:
            watcher.start()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        log.info("MMS shutting down")
        scanner.stop()
        if watcher:
            watcher.stop()

    return app, scanner, watcher


def main() -> None:
    log_cfg = LogConfig(
        level=os.environ.get("MMS_LOG_LEVEL", "INFO"),
        enable_file=bool(os.environ.get("MMS_LOG_FILE")),
        file_path=os.environ.get("MMS_LOG_FILE"),
    )
    get_logger("mms", log_cfg)

    config = AppConfig.from_env()
    app, _, _ = _build_app(config)

    log.info(
        "Starting MMS API server on %s:%d (storage=%s)",
        config.api_host, config.api_port, config.storage_backend,
    )
    uvicorn.run(
        app,
        host=config.api_host,
        port=config.api_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()