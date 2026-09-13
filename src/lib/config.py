from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MySQLConfig:
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = ""
    charset: str = "utf8mb4"

    connect_timeout: int = 10
    read_timeout: Optional[int] = None
    write_timeout: Optional[int] = None

    max_connections: int = 10
    min_connections: int = 1

    autocommit: bool = False
    cursorclass: Optional[str] = None

    extra_kwargs: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "charset": self.charset,
            "connect_timeout": self.connect_timeout,
            "read_timeout": self.read_timeout,
            "write_timeout": self.write_timeout,
            "autocommit": self.autocommit,
            **self.extra_kwargs,
        }