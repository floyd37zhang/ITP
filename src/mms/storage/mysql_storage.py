from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lib.mysql_client import MySQLClient
from lib.mysql_config import MySQLConfig
from lib.logger import get_logger

from ..models.resource import Resource, ResourceQuery, ResourceType
from ..models.question import Question, QuestionType
from .base import Storage

log = get_logger("mms.storage.mysql")


def _resource_from_row(row: dict) -> Resource:
    return Resource(
        id=row.get("id"),
        file_path=row.get("file_path", ""),
        file_name=row.get("file_name", ""),
        file_extension=row.get("file_extension", ""),
        grade=row.get("grade", ""),
        subject=row.get("subject", ""),
        version=row.get("version", ""),
        resource_type=ResourceType(row.get("resource_type", "lesson_plan")),
        knowledge_points=json.loads(row.get("knowledge_points") or "[]"),
        difficulty=row.get("difficulty", 3),
        class_level=row.get("class_level", ""),
        focus_tags=json.loads(row.get("focus_tags") or "[]"),
        file_size=row.get("file_size", 0),
        file_hash=row.get("file_hash", ""),
        created_at=row.get("created_at") or datetime.now(),
        updated_at=row.get("updated_at") or datetime.now(),
    )


def _question_from_row(row: dict) -> Question:
    return Question(
        id=row.get("id"),
        resource_id=row.get("resource_id", 0),
        order_index=row.get("order_index", 0),
        question_type=QuestionType(row.get("question_type", "other")),
        content=row.get("content", ""),
        options=json.loads(row.get("options") or "[]"),
        answer=row.get("answer", ""),
        analysis=row.get("analysis", ""),
        score=row.get("score", 5.0),
        knowledge_points=json.loads(row.get("knowledge_points") or "[]"),
        difficulty=row.get("difficulty", 3),
        images=json.loads(row.get("images") or "[]"),
        created_at=row.get("created_at") or datetime.now(),
    )


_SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS resources (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        file_path VARCHAR(1024) NOT NULL UNIQUE,
        file_name VARCHAR(512) NOT NULL,
        file_extension VARCHAR(32) NOT NULL,
        grade VARCHAR(64) DEFAULT '',
        subject VARCHAR(64) DEFAULT '',
        version VARCHAR(64) DEFAULT '',
        resource_type VARCHAR(32) NOT NULL,
        knowledge_points JSON DEFAULT (JSON_ARRAY()),
        difficulty INT DEFAULT 3,
        class_level VARCHAR(64) DEFAULT '',
        focus_tags JSON DEFAULT (JSON_ARRAY()),
        file_size BIGINT DEFAULT 0,
        file_hash VARCHAR(128) DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_grade (grade),
        INDEX idx_subject (subject),
        INDEX idx_type (resource_type),
        INDEX idx_hash (file_hash)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS questions (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        resource_id BIGINT NOT NULL,
        order_index INT NOT NULL DEFAULT 0,
        question_type VARCHAR(32) NOT NULL,
        content TEXT,
        options JSON DEFAULT (JSON_ARRAY()),
        answer TEXT,
        analysis TEXT,
        score FLOAT DEFAULT 5.0,
        knowledge_points JSON DEFAULT (JSON_ARRAY()),
        difficulty INT DEFAULT 3,
        images JSON DEFAULT (JSON_ARRAY()),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_resource (resource_id),
        CONSTRAINT fk_questions_resource FOREIGN KEY (resource_id)
            REFERENCES resources(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
]


class MySQLStorage(Storage):

    def __init__(self, config: MySQLConfig) -> None:
        self._client = MySQLClient(config)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        log.info("Ensuring database schema exists")
        try:
            for sql in _SCHEMA_SQL:
                self._client.execute(sql)
            log.info("Schema ready")
        except Exception as exc:
            log.error("Failed to ensure schema: %s", exc)
            raise

    def save_resource(self, resource: Resource) -> Resource:
        now = datetime.now()
        kp = json.dumps(resource.knowledge_points, ensure_ascii=False)
        ft = json.dumps(resource.focus_tags, ensure_ascii=False)

        if resource.id is None:
            sql = """
                INSERT INTO resources
                (file_path, file_name, file_extension, grade, subject, version,
                 resource_type, knowledge_points, difficulty, class_level,
                 focus_tags, file_size, file_hash, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                resource.file_path, resource.file_name, resource.file_extension,
                resource.grade, resource.subject, resource.version,
                resource.resource_type.value, kp, resource.difficulty, resource.class_level,
                ft, resource.file_size, resource.file_hash, now, now,
            )
            self._client.execute(sql, params)
            row = self._client.query_one(
                "SELECT LAST_INSERT_ID() AS id"
            )
            resource.id = int(row["id"]) if row else None
        else:
            sql = """
                UPDATE resources SET
                    file_name = %s, file_extension = %s, grade = %s, subject = %s,
                    version = %s, resource_type = %s, knowledge_points = %s,
                    difficulty = %s, class_level = %s, focus_tags = %s,
                    file_size = %s, file_hash = %s, updated_at = %s
                WHERE id = %s
            """
            params = (
                resource.file_name, resource.file_extension, resource.grade,
                resource.subject, resource.version, resource.resource_type.value,
                kp, resource.difficulty, resource.class_level, ft,
                resource.file_size, resource.file_hash, now, resource.id,
            )
            self._client.execute(sql, params)
        resource.updated_at = now
        return resource

    def get_resource(self, resource_id: int) -> Optional[Resource]:
        row = self._client.query_one(
            "SELECT * FROM resources WHERE id = %s", (resource_id,)
        )
        if row is None:
            return None
        return _resource_from_row(row)

    def get_resource_by_path(self, file_path: str) -> Optional[Resource]:
        row = self._client.query_one(
            "SELECT * FROM resources WHERE file_path = %s", (file_path,)
        )
        if row is None:
            return None
        return _resource_from_row(row)

    def update_resource(self, resource: Resource) -> Resource:
        return self.save_resource(resource)

    def delete_resource(self, resource_id: int) -> bool:
        affected = self._client.execute(
            "DELETE FROM resources WHERE id = %s", (resource_id,)
        )
        return affected > 0

    def delete_resource_by_path(self, file_path: str) -> bool:
        affected = self._client.execute(
            "DELETE FROM resources WHERE file_path = %s", (file_path,)
        )
        return affected > 0

    def query_resources(
        self, query: ResourceQuery
    ) -> tuple[list[Resource], int]:
        conditions: list[str] = []
        params: list = []

        if query.file_path is not None:
            conditions.append("file_path LIKE %s")
            params.append(f"%{query.file_path}%")
        if query.grade is not None:
            conditions.append("grade = %s")
            params.append(query.grade)
        if query.subject is not None:
            conditions.append("subject = %s")
            params.append(query.subject)
        if query.version is not None:
            conditions.append("version = %s")
            params.append(query.version)
        if query.resource_type is not None:
            conditions.append("resource_type = %s")
            params.append(query.resource_type.value)
        if query.knowledge_point is not None:
            conditions.append("JSON_CONTAINS(knowledge_points, JSON_QUOTE(%s))")
            params.append(query.knowledge_point)
        if query.difficulty_min is not None:
            conditions.append("difficulty >= %s")
            params.append(query.difficulty_min)
        if query.difficulty_max is not None:
            conditions.append("difficulty <= %s")
            params.append(query.difficulty_max)
        if query.class_level is not None:
            conditions.append("class_level = %s")
            params.append(query.class_level)
        if query.focus_tag is not None:
            conditions.append("JSON_CONTAINS(focus_tags, JSON_QUOTE(%s))")
            params.append(query.focus_tag)
        if query.keyword is not None:
            conditions.append(
                "(file_name LIKE %s OR grade LIKE %s OR subject LIKE %s OR "
                "version LIKE %s OR focus_tags LIKE %s)"
            )
            kw = f"%{query.keyword}%"
            params.extend([kw, kw, kw, kw, kw])

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        total_sql = f"SELECT COUNT(*) AS c FROM resources {where}"
        count_row = self._client.query_one(total_sql, params)
        total = int(count_row["c"]) if count_row else 0

        data_sql = (
            f"SELECT * FROM resources {where} "
            f"ORDER BY updated_at DESC LIMIT %s OFFSET %s"
        )
        rows = self._client.query_all(
            data_sql, [*params, query.limit, query.offset]
        )
        return [_resource_from_row(r) for r in rows], total

    def save_questions(self, questions: list[Question]) -> list[Question]:
        if not questions:
            return []

        values = []
        now = datetime.now()
        for q in questions:
            values.append((
                q.resource_id, q.order_index, q.question_type.value,
                q.content,
                json.dumps(q.options, ensure_ascii=False),
                q.answer, q.analysis, q.score,
                json.dumps(q.knowledge_points, ensure_ascii=False),
                q.difficulty,
                json.dumps(q.images, ensure_ascii=False),
                now,
            ))

        sql = """
            INSERT INTO questions
            (resource_id, order_index, question_type, content, options,
             answer, analysis, score, knowledge_points, difficulty, images, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self._client.executemany(sql, values)

        rows = self._client.query_all(
            "SELECT id, resource_id, order_index FROM questions "
            "WHERE resource_id = %s AND created_at = %s ORDER BY id DESC LIMIT %s",
            (questions[0].resource_id, now, len(questions))
        )
        for idx, row in enumerate(reversed(rows)):
            if idx < len(questions):
                questions[idx].id = int(row["id"])
        return questions

    def get_questions_by_resource(self, resource_id: int) -> list[Question]:
        rows = self._client.query_all(
            "SELECT * FROM questions WHERE resource_id = %s ORDER BY order_index",
            (resource_id,)
        )
        return [_question_from_row(r) for r in rows]

    def delete_questions_by_resource(self, resource_id: int) -> int:
        return self._client.execute(
            "DELETE FROM questions WHERE resource_id = %s", (resource_id,)
        )

    def health_check(self) -> bool:
        try:
            self._client.query_scalar("SELECT 1")
            return True
        except Exception:
            return False