from __future__ import annotations

from lib.logger import get_logger

from ..models.question import Question
from .base import FileParser

log = get_logger("mms.parsers.image")


class ImageParser(FileParser):

    def parse(self, file_path: str) -> str:
        log.debug("Image file, no text extraction: %s", file_path)
        return ""

    def extract_questions(self, file_path: str) -> list[Question]:
        return []