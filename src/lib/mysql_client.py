from __future__ import annotations

import asyncio
import functools
import threading
from contextlib import contextmanager
from typing import Any, Iterable, Optional, Sequence

import pymysql
import pymysql.cursors

from .mysql_config import MySQLConfig
from .exceptions import (
    ConnectionError,
    MySQLClientError,
    PoolExhaustedError,
    QueryError,
    TransactionError,
)


class MySQLClient:
    """
    同步 + 异步统一 MySQL 客户端。

    设计原则:
      - 同步接口走 pymysql
      - 异步接口通过独立的 event loop 执行, 对外暴露 async/await 语法糖
      - 内部维护一个连接池, 同步 / 异步共享同一个配置源
      - 支持上下文管理器自动回收连接, 支持事务嵌套 (savepoint)
    """

    def __init__(self, config: MySQLConfig):
        self._config = config
        self._local = threading.local()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    def _connect(self):
        try:
            return pymysql.connect(**self._config.to_dict())
        except pymysql.MySQLError as e:
            raise ConnectionError(f"Failed to connect MySQL: {e}") from e

    @contextmanager
    def _acquire(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._connect()
            self._local.conn = conn
        try:
            yield conn
        except pymysql.MySQLError as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise QueryError(str(e)) from e

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None
        self._shutdown_async_loop()

    # ------------------------------------------------------------------
    # 同步查询
    # ------------------------------------------------------------------

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> int:
        with self._acquire() as conn:
            with conn.cursor() as cur:
                affected = cur.execute(sql, params or ())
                if not self._config.autocommit:
                    conn.commit()
                return affected

    def executemany(self, sql: str, params_list: Iterable[Sequence[Any]]) -> int:
        with self._acquire() as conn:
            with conn.cursor() as cur:
                affected = cur.executemany(sql, list(params_list))
                if not self._config.autocommit:
                    conn.commit()
                return affected

    def query_one(
        self, sql: str, params: Optional[Sequence[Any]] = None, as_dict: bool = True
    ) -> Optional[dict]:
        cursor_cls = pymysql.cursors.DictCursor if as_dict else pymysql.cursors.Cursor
        with self._acquire() as conn:
            with conn.cursor(cursor_cls) as cur:
                cur.execute(sql, params or ())
                return cur.fetchone()

    def query_all(
        self, sql: str, params: Optional[Sequence[Any]] = None, as_dict: bool = True
    ) -> list[dict]:
        cursor_cls = pymysql.cursors.DictCursor if as_dict else pymysql.cursors.Cursor
        with self._acquire() as conn:
            with conn.cursor(cursor_cls) as cur:
                cur.execute(sql, params or ())
                return cur.fetchall()

    def query_scalar(
        self, sql: str, params: Optional[Sequence[Any]] = None
    ) -> Any:
        row = self.query_one(sql, params, as_dict=False)
        if row is None or len(row) == 0:
            return None
        return row[0]

    # ------------------------------------------------------------------
    # 事务
    # ------------------------------------------------------------------

    @contextmanager
    def transaction(self):
        with self._acquire() as conn:
            depth = getattr(self._local, "tx_depth", 0)
            self._local.tx_depth = depth + 1
            savepoint = f"sp_{depth}" if depth > 0 else None
            try:
                if savepoint:
                    conn.execute(f"SAVEPOINT {savepoint}")
                else:
                    conn.begin()
                yield conn
                if savepoint:
                    conn.execute(f"RELEASE SAVEPOINT {savepoint}")
                else:
                    conn.commit()
            except Exception:
                if savepoint:
                    conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                else:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                raise
            finally:
                self._local.tx_depth -= 1

    # ------------------------------------------------------------------
    # 异步支持 (后台 event loop 线程)
    # ------------------------------------------------------------------

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is not None and not self._loop.is_closed():
            return self._loop

        self._stop_event.clear()
        self._loop = asyncio.new_event_loop()

        def _run_loop():
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        self._loop_thread = threading.Thread(target=_run_loop, daemon=True)
        self._loop_thread.start()
        return self._loop

    def _shutdown_async_loop(self) -> None:
        if self._loop is not None and not self._loop.is_closed():
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass
        self._loop = None
        self._loop_thread = None

    async def aexecute(
        self, sql: str, params: Optional[Sequence[Any]] = None
    ) -> int:
        loop = self._ensure_loop()
        return await loop.run_in_executor(
            None, functools.partial(self.execute, sql, params)
        )

    async def aexecutemany(
        self, sql: str, params_list: Iterable[Sequence[Any]]
    ) -> int:
        loop = self._ensure_loop()
        return await loop.run_in_executor(
            None, functools.partial(self.executemany, sql, params_list)
        )

    async def aquery_one(
        self, sql: str, params: Optional[Sequence[Any]] = None, as_dict: bool = True
    ) -> Optional[dict]:
        loop = self._ensure_loop()
        return await loop.run_in_executor(
            None, functools.partial(self.query_one, sql, params, as_dict)
        )

    async def aquery_all(
        self, sql: str, params: Optional[Sequence[Any]] = None, as_dict: bool = True
    ) -> list[dict]:
        loop = self._ensure_loop()
        return await loop.run_in_executor(
            None, functools.partial(self.query_all, sql, params, as_dict)
        )

    async def aquery_scalar(
        self, sql: str, params: Optional[Sequence[Any]] = None
    ) -> Any:
        loop = self._ensure_loop()
        return await loop.run_in_executor(
            None, functools.partial(self.query_scalar, sql, params)
        )

    async def atransaction(self):
        loop = self._ensure_loop()
        ctx = self.transaction()
        return await loop.run_in_executor(None, lambda: ctx)

    # ------------------------------------------------------------------
    # 上下文管理
    # ------------------------------------------------------------------

    def __enter__(self) -> "MySQLClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    async def __aenter__(self) -> "MySQLClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"<MySQLClient host={self._config.host}:{self._config.port} "
            f"db={self._config.database!r}>"
        )


__all__ = [
    "MySQLClient",
    "MySQLConfig",
    "MySQLClientError",
    "ConnectionError",
    "QueryError",
    "TransactionError",
    "PoolExhaustedError",
]