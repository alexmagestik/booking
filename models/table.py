"""Модель столика в ресторане."""

from dataclasses import dataclass
from typing import ClassVar, Optional

from models.base import Model


@dataclass
class Table(Model):
    table_name: ClassVar[str] = "tables"
    ddl_columns: ClassVar[dict[str, str]] = {
        "number": "INTEGER NOT NULL UNIQUE",
        "seats": "INTEGER NOT NULL DEFAULT 2",
        "location": "VARCHAR(60) NOT NULL DEFAULT 'hall'",
        "is_active": "BOOLEAN NOT NULL DEFAULT TRUE",
    }
    foreign_keys: ClassVar[list[tuple[str, str, str]]] = []

    number: int = 0
    seats: int = 2
    location: str = "hall"
    is_active: bool = True

    def __str__(self) -> str:
        return f"Table(id={self.id}, number={self.number}, seats={self.seats}, location={self.location!r})"
