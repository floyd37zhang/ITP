from __future__ import annotations

import pymupdf

from lib.logger import get_logger

from ..models.question import Question
from .base import FileParser, extract_questions_from_text

log = get_logger("mms.parsers.pdf")


class PdfParser(FileParser):

    def parse(self, file_path: str) -> str:
        try:
            doc = pymupdf.open(file_path)
            parts: list[str] = []
            for page in doc:
                text = page.get_text()
                if text.strip():
                    parts.append(text)
            doc.close()
            return "\n".join(parts)
        except Exception as exc:
            log.error("Failed to parse PDF file %s: %s", file_path, exc)
            return ""

    def extract_questions(self, file_path: str) -> list[Question]:
        text = self.parse(file_path)
        if not text:
            return []
        return extract_questions_from_text(text)