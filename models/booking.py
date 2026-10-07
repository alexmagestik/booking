"""Модель бронирования столика."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import ClassVar, Optional

from models.base import Model


@dataclass
class Booking(Model):
    table_name: ClassVar[str] = "bookings"
    ddl_columns: ClassVar[dict[str, str]] = {
        "user_id": "INTEGER NOT NULL",
        "table_id": "INTEGER NOT NULL",
        "start_time": "TIMESTAMP NOT NULL",
        "duration_minutes": "INTEGER NOT NULL DEFAULT 60",
        "guests_count": "INTEGER NOT NULL DEFAULT 1",
        "status": "VARCHAR(20) NOT NULL DEFAULT 'confirmed'",
        "created_at": "TIMESTAMP NOT NULL DEFAULT NOW()",
    }
    foreign_keys: ClassVar[list[tuple[str, str, str]]] = [
        ("user_id", "users", "id"),
        ("table_id", "tables", "id"),
    ]

    user_id: int = 0
    table_id: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    duration_minutes: int = 60
    guests_count: int = 1
    status: str = "confirmed"

    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(minutes=self.duration_minutes)

    def overlaps(self, start: datetime, end: datetime) -> bool:
        """Проверка пересечения временных интервалов."""
        return self.start_time < end and start < self.end_time

    def __str__(self) -> str:
        return (
            f"Booking(id={self.id}, user_id={self.user_id}, table_id={self.table_id}, "
            f"start={self.start_time}, duration={self.duration_minutes}m)"
        )
