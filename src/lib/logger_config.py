from __future__ import annotations

import sys
from dataclasses import dataclass, field
from logging import DEBUG, ERROR, FATAL, INFO, WARNING, Formatter
from typing import Optional

Level = int

LEVEL_MAP = {
    "DEBUG": DEBUG,
    "INFO": INFO,
    "WARNING": WARNING,
    "ERROR": ERROR,
    "FATAL": FATAL,
    "NOTSET": 0,
}

DEFAULT_FMT = "%(asctime)s [%(levelname)-7s] %(name)s | %(message)s"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"

CONSOLE_COLOR_FMT = (
    "\033[1;34m%(asctime)s\033[0m "
    "\033[1;35m[%(levelname)-7s]\033[0m "
    "\033[1;33m%(name)s\033[0m "
    "| %(message)s"
)

LEVEL_COLORS = {
    DEBUG: "\033[36m",     # cyan
    INFO: "\033[32m",     # green
    WARNING: "\033[33m",  # yellow
    ERROR: "\033[31m",    # red
    FATAL: "\033[1;31m",  # bold red
}


class _ColorFormatter(Formatter):
    def format(self, record) -> str:
        color = LEVEL_COLORS.get(record.levelno, "")
        reset = "\033[0m"
        record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


@dataclass
class LogConfig:
    level: str | int = "INFO"

    enable_console: bool = True
    console_color: bool = True
    console_stream: object = field(default_factory=lambda: sys.stdout)

    enable_file: bool = False
    file_path: Optional[str] = None
    file_encoding: str = "utf-8"

    file_rotate_size: int = 0
    file_rotate_count: int = 5

    file_rotate_time: str = ""
    file_rotate_interval: int = 1
    file_rotate_count_by_time: int = 7

    fmt: str = DEFAULT_FMT
    datefmt: str = DEFAULT_DATEFMT

    propagate: bool = False

    def resolve_level(self) -> Level:
        if isinstance(self.level, str):
            return LEVEL_MAP.get(self.level.upper(), INFO)
        return self.level