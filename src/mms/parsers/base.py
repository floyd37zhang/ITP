from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Optional

from ..models.question import Question, QuestionType


QUESTION_TYPE_PATTERNS: dict[QuestionType, tuple[str, ...]] = {
    QuestionType.SINGLE_CHOICE: ("单项选择", "单选题", "选择题（单选）"),
    QuestionType.MULTIPLE_CHOICE: ("多项选择", "多选题", "选择题（多选）"),
    QuestionType.FILL_BLANK: ("填空题", "填空"),
    QuestionType.SHORT_ANSWER: ("简答题", "问答题", "简答"),
    QuestionType.ESSAY: ("作文", "议论文", "论述题"),
    QuestionType.CALCULATION: ("计算题", "计算", "解方程"),
    QuestionType.PROOF: ("证明题", "证明", "求证"),
    QuestionType.DRAWING: ("作图", "画图", "画图题", "作图题"),
    QuestionType.MATCHING: ("连线", "匹配", "配对"),
}

QUESTION_NUMBER_RE = re.compile(
    r"^\s*(?:第\s*)?(\d+)\s*[\.\、\)\]\(]"
)

SECTION_HEADER_RE = re.compile(
    r"^\s*[一二三四五六七八九十百千\d]+\s*[\.\、\)\]\(]\s*(.+)"
)


def _guess_type_from_context(content: str, options: list[str], full_block: str = "") -> QuestionType:
    haystack = full_block[:500] if full_block else content[:500]
    for qtype, keywords in QUESTION_TYPE_PATTERNS.items():
        for kw in keywords:
            if kw in haystack:
                return qtype
    if options:
        return QuestionType.SINGLE_CHOICE
    if re.search(r"[A-D]\s*[\.、]\s*\S", haystack):
        return QuestionType.SINGLE_CHOICE
    if "=" in content and any(op in content for op in ("+", "-", "×", "÷", "/", "x", "X")):
        return QuestionType.CALCULATION
    if "____" in content or "＿" in content or "（" in content:
        return QuestionType.FILL_BLANK
    return QuestionType.OTHER


def _split_into_blocks(text: str) -> list[tuple[int, str]]:
    lines = text.splitlines()
    blocks: list[tuple[int, str]] = []
    current_num: Optional[int] = None
    current_lines: list[str] = []
    pending_header: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            continue

        m = QUESTION_NUMBER_RE.match(line)
        if m:
            if current_num is not None and current_lines:
                blocks.append((current_num, "\n".join(current_lines).strip()))
            current_num = int(m.group(1))
            prefix = "\n".join(pending_header).strip()
            body = line[m.end():].strip()
            current_lines = ([prefix] if prefix else []) + [body]
            pending_header = []
        else:
            if SECTION_HEADER_RE.match(line):
                pending_header.append(line)
                if current_num is None:
                    continue
            elif current_num is not None:
                current_lines.append(line.strip())

    if current_num is not None and current_lines:
        blocks.append((current_num, "\n".join(current_lines).strip()))

    if not blocks and text.strip():
        blocks.append((1, text.strip()))

    return blocks


def _parse_options(block: str) -> tuple[str, list[str]]:
    option_re = re.compile(r"([A-D])\s*[\.、\)]\s*(.+)")
    lines = block.split("\n")
    options: list[str] = []
    question_lines: list[str] = []
    in_options = False

    for line in lines:
        m = option_re.match(line.strip())
        if m:
            in_options = True
            options.append(f"{m.group(1)}. {m.group(2).strip()}")
        elif in_options and line.strip():
            if options:
                options[-1] += " " + line.strip()
            else:
                question_lines.append(line.strip())
        else:
            question_lines.append(line.strip())

    question_text = "\n".join(question_lines)
    return question_text, options


def extract_questions_from_text(text: str) -> list[Question]:
    blocks = _split_into_blocks(text)
    questions: list[Question] = []

    for order, block in blocks:
        content, options = _parse_options(block)
        qtype = _guess_type_from_context(content, options, full_block=block)
        q = Question(
            order_index=order,
            question_type=qtype,
            content=content,
            options=options,
        )
        questions.append(q)

    return questions


class FileParser(ABC):

    @abstractmethod
    def parse(self, file_path: str) -> str: ...

    @abstractmethod
    def extract_questions(self, file_path: str) -> list[Question]: ...