from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.mysql_config import MySQLConfig


@dataclass
class AppConfig:
    storage_backend: str = "memory"
    mysql: MySQLConfig = field(default_factory=MySQLConfig)
    scan_paths: list[str] = field(default_factory=lambda: ["/data/resources"])
    scan_interval_seconds: int = 300
    enable_watcher: bool = True
    supported_extensions: tuple[str, ...] = (
        ".doc", ".docx", ".pdf",
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff",
    )
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_file: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AppConfig":
        cfg = cls()
        cfg.storage_backend = os.environ.get("MMS_STORAGE", "memory")
        cfg.mysql = MySQLConfig(
            host=os.environ.get("MMS_DB_HOST", "127.0.0.1"),
            port=int(os.environ.get("MMS_DB_PORT", "3306")),
            user=os.environ.get("MMS_DB_USER", "root"),
            password=os.environ.get("MMS_DB_PASSWORD", ""),
            database=os.environ.get("MMS_DB_NAME", "mms"),
        )
        paths = os.environ.get("MMS_SCAN_PATHS", "/data/resources")
        cfg.scan_paths = [p.strip() for p in paths.split(",") if p.strip()]
        cfg.scan_interval_seconds = int(
            os.environ.get("MMS_SCAN_INTERVAL", "300")
        )
        cfg.api_host = os.environ.get("MMS_API_HOST", "0.0.0.0")
        cfg.api_port = int(os.environ.get("MMS_API_PORT", "8000"))
        cfg.log_file = os.environ.get("MMS_LOG_FILE")
        return cfg