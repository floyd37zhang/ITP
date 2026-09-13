from __future__ import annotations

import logging
import os
import threading
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional

from .logger_config import (
    CONSOLE_COLOR_FMT,
    DEFAULT_DATEFMT,
    DEFAULT_FMT,
    LogConfig,
    _ColorFormatter,
)


class LoggerManager:
    """
    日志管理器: 装配 handler / formatter, 提供子 logger 的工厂方法.

    设计原则:
      - 零外部依赖, 完全基于标准库 logging
      - 单例根 logger, 避免 handler 重复挂载
      - 控制台 + 文件滚动 (按大小 / 按时间) 三种输出可自由组合
      - 调用方只需 get_logger(__name__) 即可使用, 配置一次性初始化
    """

    _instance: Optional["LoggerManager"] = None
    _lock = threading.Lock()

    def __init__(self, config: Optional[LogConfig] = None):
        self._config = config or LogConfig()
        self._root_name = "app"
        self._configured = False
        self._setup()

    # ------------------------------------------------------------------
    # 单例 + 初始化
    # ------------------------------------------------------------------

    @classmethod
    def get(cls, config: Optional[LogConfig] = None) -> "LoggerManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config)
            elif config is not None and not cls._instance._configured:
                cls._instance._reconfigure(config)
            return cls._instance

    def _setup(self) -> None:
        root = logging.getLogger(self._root_name)
        root.setLevel(self._config.resolve_level())
        root.propagate = self._config.propagate

        for h in list(root.handlers):
            root.removeHandler(h)
            h.close()

        if self._config.enable_console:
            self._add_console_handler(root)

        if self._config.enable_file and self._config.file_path:
            self._add_file_handler(root)

        self._configured = True

    def _reconfigure(self, config: LogConfig) -> None:
        self._config = config
        self._configured = False
        self._setup()

    # ------------------------------------------------------------------
    # Handler 装配
    # ------------------------------------------------------------------

    def _add_console_handler(self, root: logging.Logger) -> None:
        handler = logging.StreamHandler(self._config.console_stream)
        if self._config.console_color:
            handler.setFormatter(_ColorFormatter(CONSOLE_COLOR_FMT, DEFAULT_DATEFMT))
        else:
            handler.setFormatter(
                logging.Formatter(self._config.fmt, self._config.datefmt)
            )
        root.addHandler(handler)

    def _add_file_handler(self, root: logging.Logger) -> None:
        path = self._config.file_path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        fmt = logging.Formatter(self._config.fmt, self._config.datefmt)

        if self._config.file_rotate_size > 0:
            handler = RotatingFileHandler(
                path,
                maxBytes=self._config.file_rotate_size,
                backupCount=self._config.file_rotate_count,
                encoding=self._config.file_encoding,
            )
        elif self._config.file_rotate_time:
            handler = TimedRotatingFileHandler(
                path,
                when=self._config.file_rotate_time,
                interval=self._config.file_rotate_interval,
                backupCount=self._config.file_rotate_count_by_time,
                encoding=self._config.file_encoding,
            )
        else:
            handler = logging.FileHandler(path, encoding=self._config.file_encoding)

        handler.setFormatter(fmt)
        root.addHandler(handler)

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def get_logger(self, name: str = "") -> logging.Logger:
        if not name:
            return logging.getLogger(self._root_name)
        return logging.getLogger(f"{self._root_name}.{name}")

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            if cls._instance is not None:
                root = logging.getLogger(cls._instance._root_name)
                for h in list(root.handlers):
                    root.removeHandler(h)
                    h.close()
            cls._instance = None


_default_manager: Optional[LoggerManager] = None


def get_logger(name: str = "", config: Optional[LogConfig] = None) -> logging.Logger:
    global _default_manager
    if _default_manager is None:
        _default_manager = LoggerManager(config)
    elif config is not None:
        _default_manager._reconfigure(config)
    return _default_manager.get_logger(name)