"""Модель пользователя ресторана."""

from dataclasses import dataclass, field
from typing import ClassVar, Optional

from models.base import Model


@dataclass
class User(Model):
    table_name: ClassVar[str] = "users"
    ddl_columns: ClassVar[dict[str, str]] = {
        "name": "VARCHAR(120) NOT NULL",
        "email": "VARCHAR(120) UNIQUE",
        "phone": "VARCHAR(32)",
        "created_at": "TIMESTAMP NOT NULL DEFAULT NOW()",
    }
    foreign_keys: ClassVar[list[tuple[str, str, str]]] = []

    name: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None

    def __str__(self) -> str:
        return f"User(id={self.id}, name={self.name!r}, email={self.email!r})"
