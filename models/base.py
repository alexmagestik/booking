"""Базовый класс модели: описание таблицы и сериализация."""

from dataclasses import asdict, dataclass, fields
from typing import Any, ClassVar, Optional


@dataclass
class Model:
    table_name: ClassVar[str] = ""
    ddl_columns: ClassVar[dict[str, str]] = {}
    foreign_keys: ClassVar[list[tuple[str, str, str]]] = []
    id: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Значения полей (без id, если оно None)."""
        data = asdict(self)
        if data.get("id") is None:
            data.pop("id", None)
        return data

    @classmethod
    def from_row(cls, row: Optional[dict[str, Any]]) -> Optional["Model"]:
        if row is None:
            return None
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in row.items() if k in allowed})

    @classmethod
    def create_ddl(cls) -> None:
        """Создать таблицу для модели (через PostgresDriver)."""
        from postgres_driver import PostgresDriver

        with PostgresDriver() as db:
            db.create_table(
                cls.table_name,
                cls.ddl_columns,
                primary_key="id",
                foreign_keys=cls.foreign_keys,
            )
