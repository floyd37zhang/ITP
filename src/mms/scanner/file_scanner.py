from __future__ import annotations

import hashlib
import os
import re
import threading
from pathlib import Path
from typing import Callable, Optional

from lib.logger import get_logger

from ..models.resource import Resource, ResourceQuery, ResourceType
from ..storage.base import Storage
from ..parsers.base import FileParser

log = get_logger("mms.scanner")


def compute_file_hash(file_path: str, chunk_size: int = 8192) -> str:
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
    except OSError as exc:
        log.warning("Cannot hash file %s: %s", file_path, exc)
    return h.hexdigest()


def infer_metadata_from_path(file_path: str) -> dict:
    path_parts = Path(file_path).parts
    info: dict = {}

    grade_pattern = re.compile(r"(?:(?:一|二|三|四|五|六|七|八|九|十)年级|[1-9][0-9]?年级)")
    subject_set = {"语文", "数学", "英语", "物理", "化学", "生物",
                   "历史", "地理", "政治", "科学", "综合"}
    version_set = {"人教版", "北师大版", "苏教版", "浙教版", "鲁教版",
                  "沪教版", "粤教版", "湘教版", "教科版", "人教版新",
                  "部编版", "统编版"}
    level_set = {"重点班", "普通班", "实验班", "提高班", "基础班", "竞赛班"}

    for part in path_parts:
        if not info.get("grade"):
            m = grade_pattern.search(part)
            if m:
                info["grade"] = m.group(0)
        if not info.get("subject") and part in subject_set:
            info["subject"] = part
        if not info.get("version"):
            for v in version_set:
                if v in part:
                    info["version"] = v
                    break
        if not info.get("class_level") and part in level_set:
            info["class_level"] = part

    return info


def guess_resource_type(file_name: str, extension: str) -> ResourceType:
    ext = extension.lower()
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}:
        return ResourceType.IMAGE
    if any(kw in file_name for kw in ("试卷", "试题", "考试", "月考试卷", "期中", "期末", "模拟", "中考", "高考")):
        return ResourceType.EXAM_PAPER
    if any(kw in file_name for kw in ("教案", "教学设计", "备课", "课件")):
        return ResourceType.LESSON_PLAN
    return ResourceType.LESSON_PLAN


class FileScanner:

    def __init__(
        self,
        storage: Storage,
        parsers: dict[str, FileParser],
        supported_extensions: tuple[str, ...],
        scan_paths: list[str],
        scan_interval: int = 300,
        on_new_file: Optional[Callable[[str], None]] = None,
        on_deleted_file: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._storage = storage
        self._parsers = parsers
        self._supported_extensions = tuple(e.lower() for e in supported_extensions)
        self._scan_paths = list(scan_paths)
        self._scan_interval = scan_interval
        self._on_new_file = on_new_file
        self._on_deleted_file = on_deleted_file
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def scan_once(self) -> dict:
        current_files: set[str] = set()
        added = 0
        updated = 0

        for base in self._scan_paths:
            if not os.path.isdir(base):
                log.warning("Scan path does not exist: %s", base)
                continue
            for root, dirs, files in os.walk(base):
                for fname in files:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in self._supported_extensions:
                        continue
                    full_path = os.path.abspath(os.path.join(root, fname))
                    current_files.add(full_path)

                    if self._index_file(full_path, ext):
                        added += 1

        stored, _ = self._storage.query_resources(
            ResourceQuery(limit=100000)
        )
        stored_paths = {r.file_path for r in stored}

        for path in stored_paths - current_files:
            if self._storage.delete_resource_by_path(path):
                log.info("Removed resource for deleted file: %s", path)
                if self._on_deleted_file:
                    self._on_deleted_file(path)

        log.info("Scan complete: added=%d, checked=%d", added, len(current_files))
        return {"scanned": len(current_files), "added": added}

    def _index_file(self, file_path: str, extension: str) -> bool:
        try:
            stat = os.stat(file_path)
            file_hash = compute_file_hash(file_path)

            existing = self._storage.get_resource_by_path(file_path)

            if existing and existing.file_hash == file_hash:
                return False

            file_name = os.path.basename(file_path)
            meta_from_path = infer_metadata_from_path(file_path)
            rtype = guess_resource_type(file_name, extension)

            resource = Resource(
                file_path=file_path,
                file_name=file_name,
                file_extension=extension,
                grade=meta_from_path.get("grade", ""),
                subject=meta_from_path.get("subject", ""),
                version=meta_from_path.get("version", ""),
                resource_type=rtype,
                class_level=meta_from_path.get("class_level", ""),
                file_size=stat.st_size,
                file_hash=file_hash,
            )

            resource = self._storage.save_resource(resource)
            log.info(
                "Indexed resource: %s (type=%s, id=%s)",
                file_path, rtype.value, resource.id,
            )

            parser = self._parsers.get(extension)
            if parser and resource.id:
                try:
                    questions = parser.extract_questions(file_path)
                    self._storage.delete_questions_by_resource(resource.id)
                    for q in questions:
                        q.resource_id = resource.id
                        q.knowledge_points = list(resource.knowledge_points)
                    self._storage.save_questions(questions)
                    log.info(
                        "Extracted %d questions from %s",
                        len(questions), file_path,
                    )
                except Exception as exc:
                    log.error("Failed to extract questions from %s: %s", file_path, exc)

            if self._on_new_file:
                self._on_new_file(file_path)

            return True
        except Exception as exc:
            log.error("Failed to index file %s: %s", file_path, exc)
            return False

    def run_forever(self) -> None:
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        log.info(
            "File scanner started, interval=%ds, paths=%s",
            self._scan_interval, self._scan_paths,
        )
        while not self._stop_event.is_set():
            try:
                self.scan_once()
            except Exception as exc:
                log.error("Scanner iteration failed: %s", exc)
            self._stop_event.wait(self._scan_interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        log.info("File scanner stopped")