from __future__ import annotations

import os
import threading
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from lib.logger import get_logger

log = get_logger("mms.watcher")


class _Handler(FileSystemEventHandler):

    def __init__(
        self,
        on_created: Optional[Callable[[str], None]] = None,
        on_deleted: Optional[Callable[[str], None]] = None,
        on_modified: Optional[Callable[[str], None]] = None,
        on_moved: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self._on_created = on_created
        self._on_deleted = on_deleted
        self._on_modified = on_modified
        self._on_moved = on_moved
        self._supported_ext: set[str] = {
            ".doc", ".docx", ".pdf",
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff",
        }

    def _is_supported(self, path: str) -> bool:
        return os.path.splitext(path)[1].lower() in self._supported_ext

    def on_created(self, event):
        if event.is_directory:
            return
        if self._is_supported(event.src_path):
            log.info("File created: %s", event.src_path)
            if self._on_created:
                self._on_created(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        if self._is_supported(event.src_path):
            log.info("File deleted: %s", event.src_path)
            if self._on_deleted:
                self._on_deleted(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        if self._is_supported(event.src_path):
            log.info("File modified: %s", event.src_path)
            if self._on_modified:
                self._on_modified(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        src_ok = self._is_supported(event.src_path)
        dest_ok = self._is_supported(event.dest_path)
        if src_ok and dest_ok and self._on_moved:
            log.info("File moved: %s -> %s", event.src_path, event.dest_path)
            self._on_moved(event.src_path, event.dest_path)
        elif src_ok and self._on_deleted:
            self._on_deleted(event.src_path)
        elif dest_ok and self._on_created:
            self._on_created(event.dest_path)


class FileWatcher:

    def __init__(
        self,
        watch_paths: list[str],
        on_created: Optional[Callable[[str], None]] = None,
        on_deleted: Optional[Callable[[str], None]] = None,
        on_modified: Optional[Callable[[str], None]] = None,
        on_moved: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self._watch_paths = watch_paths
        self._handler = _Handler(
            on_created=on_created,
            on_deleted=on_deleted,
            on_modified=on_modified,
            on_moved=on_moved,
        )
        self._observer: Optional[Observer] = None

    def start(self) -> None:
        if self._observer is not None:
            return
        self._observer = Observer()
        for path in self._watch_paths:
            if os.path.isdir(path):
                self._observer.schedule(self._handler, path, recursive=True)
                log.info("Watching: %s", path)
            else:
                log.warning("Watch path does not exist: %s", path)
        self._observer.daemon = True
        self._observer.start()
        log.info("File watcher started")

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=3)
            self._observer = None
            log.info("File watcher stopped")