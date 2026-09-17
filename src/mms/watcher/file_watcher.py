from __future__ import annotations

import os
from typing import Callable, Optional, Union

from watchdog.events import FileSystemEventHandler, FileSystemEvent
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

    @staticmethod
    def _as_str(path: Union[bytes, str]) -> str:
        return path.decode() if isinstance(path, bytes) else path

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = self._as_str(event.src_path)
        if self._is_supported(path):
            log.info("File created: %s", path)
            if self._on_created:
                self._on_created(path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = self._as_str(event.src_path)
        if self._is_supported(path):
            log.info("File deleted: %s", path)
            if self._on_deleted:
                self._on_deleted(path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = self._as_str(event.src_path)
        if self._is_supported(path):
            log.info("File modified: %s", path)
            if self._on_modified:
                self._on_modified(path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src = self._as_str(event.src_path)
        dest = self._as_str(event.dest_path)
        src_ok = self._is_supported(src)
        dest_ok = self._is_supported(dest)
        if src_ok and dest_ok and self._on_moved:
            log.info("File moved: %s -> %s", src, dest)
            self._on_moved(src, dest)
        elif src_ok and self._on_deleted:
            self._on_deleted(src)
        elif dest_ok and self._on_created:
            self._on_created(dest)


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
        self._observer = None

    def start(self) -> None:
        if self._observer is not None:
            return
        observer = Observer()
        for path in self._watch_paths:
            if os.path.isdir(path):
                observer.schedule(self._handler, path, recursive=True)
                log.info("Watching: %s", path)
            else:
                log.warning("Watch path does not exist: %s", path)
        observer.daemon = True
        observer.start()
        self._observer = observer
        log.info("File watcher started")

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=3)
            self._observer = None
            log.info("File watcher stopped")