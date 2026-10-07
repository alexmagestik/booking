"""Минимальный драйвер для работы с PostgreSQL на базе psycopg2."""

import os
from typing import Any, Iterable, Optional, Sequence

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor, execute_values
from dotenv import load_dotenv

load_dotenv()

DEFAULT_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": os.getenv("PGPORT", "5432"),
    "dbname": os.getenv("PGDATABASE", "postgres"),
    "user": os.getenv("PGUSER", "postgres"),
    "password": os.getenv("PGPASSWORD", "postgres"),
}


class PostgresDriver:
    """Тонкая обёртка над psycopg2 с CRUD-операциями для таблиц проекта."""

    def __init__(self, **overrides: Any) -> None:
        self.config = {**DEFAULT_CONFIG, **{k: v for k, v in overrides.items() if v}}
        self.conn = None

    # ------------------------------------------------------------------
    # Подключение
    # ------------------------------------------------------------------
    def connect(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.config)
            self.conn.autocommit = False
        return self.conn

    def close(self) -> None:
        if self.conn is not None and not self.conn.closed:
            self.conn.close()
        self.conn = None

    def __enter__(self) -> "PostgresDriver":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()

    def commit(self) -> None:
        if self.conn is not None and not self.conn.closed:
            self.conn.commit()

    def rollback(self) -> None:
        if self.conn is not None and not self.conn.closed:
            self.conn.rollback()

    # ------------------------------------------------------------------
    # Низкоуровневые запросы
    # ------------------------------------------------------------------
    def _cursor(self, cursor_factory=None):
        conn = self.connect()
        return conn.cursor(cursor_factory=cursor_factory)

    def execute(self, query: Any, params: Sequence[Any] = ()) -> int:
        """Выполнить запрос, вернуть количество затронутых строк."""
        with self._cursor() as cur:
            cur.execute(query, params)
            return cur.rowcount

    def fetchone(self, query: Any, params: Sequence[Any] = ()) -> Optional[dict]:
        with self._cursor(RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row is not None else None

    def fetchall(self, query: Any, params: Sequence[Any] = ()) -> list[dict]:
        with self._cursor(RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def scalar(self, query: Any, params: Sequence[Any] = ()) -> Any:
        with self._cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return row[0] if row is not None else None

    # ------------------------------------------------------------------
    # DDL: создание / удаление таблиц
    # ------------------------------------------------------------------
    def create_table(
        self,
        table: str,
        columns: dict[str, str],
        primary_key: str = "id",
        foreign_keys: Optional[list[tuple[str, str, str]]] = None,
        if_not_exists: bool = True,
    ) -> None:
        """Создать таблицу.

        :param columns: {"name": "VARCHAR(100) NOT NULL", ...}
        :param foreign_keys: [(column, ref_table, ref_column), ...]
        """
        exists = sql.SQL("IF NOT EXISTS ") if if_not_exists else sql.SQL("")
        cols = []
        if primary_key and primary_key not in columns:
            cols.append(
                sql.SQL("{} SERIAL").format(sql.Identifier(primary_key))
            )
        for name, definition in columns.items():
            cols.append(sql.SQL("{} {}").format(sql.Identifier(name), sql.SQL(definition)))
        if primary_key:
            cols.append(sql.SQL("PRIMARY KEY ({})").format(sql.Identifier(primary_key)))
        for col, ref_table, ref_col in foreign_keys or []:
            cols.append(
                sql.SQL("FOREIGN KEY ({}) REFERENCES {} ({})").format(
                    sql.Identifier(col),
                    sql.Identifier(ref_table),
                    sql.Identifier(ref_col),
                )
            )
        query = sql.SQL("CREATE TABLE {}{} ({})").format(
            exists, sql.Identifier(table), sql.SQL(", ").join(cols)
        )
        self.execute(query)
        self.commit()

    def drop_table(self, table: str, if_exists: bool = True) -> None:
        exists = sql.SQL("IF EXISTS ") if if_exists else sql.SQL("")
        self.execute(sql.SQL("DROP TABLE {}{}").format(exists, sql.Identifier(table)))
        self.commit()

    def table_exists(self, table: str) -> bool:
        row = self.fetchone(
            "SELECT to_regclass(%s) IS NOT NULL AS exists", (table,)
        )
        return bool(row and row["exists"])

    def truncate(self, table: str, cascade: bool = False) -> None:
        suffix = sql.SQL(" CASCADE") if cascade else sql.SQL("")
        self.execute(sql.SQL("TRUNCATE TABLE {}{}").format(sql.Identifier(table), suffix))
        self.commit()

    # ------------------------------------------------------------------
    # INSERT
    # ------------------------------------------------------------------
    def insert(self, table: str, data: dict[str, Any]) -> Any:
        """Вставить строку, вернуть значение primary key (id)."""
        if not data:
            raise ValueError("data не может быть пустым")
        columns = list(data.keys())
        values = [data[c] for c in columns]
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
            sql.Identifier(table),
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.SQL(", ").join(sql.Placeholder() * len(columns)),
        )
        with self._cursor() as cur:
            cur.execute(query, values)
            new_id = cur.fetchone()[0]
        self.commit()
        return new_id

    def bulk_insert(
        self, table: str, columns: Sequence[str], rows: Iterable[Sequence[Any]]
    ) -> int:
        """Массовая вставка строк."""
        query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
            sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, columns))
        )
        rows = list(rows)
        if not rows:
            return 0
        with self._cursor() as cur:
            execute_values(cur, query.as_string(self.connect()), rows)
            count = cur.rowcount
        self.commit()
        return count

    # ------------------------------------------------------------------
    # SELECT
    # ------------------------------------------------------------------
    def select(
        self,
        table: str,
        where: Optional[str] = None,
        params: Sequence[Any] = (),
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        query = [sql.SQL("SELECT * FROM {}").format(sql.Identifier(table))]
        if where:
            query.append(sql.SQL(" WHERE ") + sql.SQL(where))
        if order_by:
            query.append(sql.SQL(" ORDER BY ") + sql.SQL(order_by))
        if limit is not None:
            query.append(sql.SQL(" LIMIT {}").format(sql.Literal(limit)))
        return self.fetchall(sql.SQL("").join(query), params)

    def select_one(
        self, table: str, where: Optional[str] = None, params: Sequence[Any] = ()
    ) -> Optional[dict]:
        rows = self.select(table, where, params, limit=1)
        return rows[0] if rows else None

    def count(self, table: str, where: Optional[str] = None, params: Sequence[Any] = ()) -> int:
        query = sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table))
        if where:
            query = query + sql.SQL(" WHERE ") + sql.SQL(where)
        return int(self.scalar(query, params))

    # ------------------------------------------------------------------
    # UPDATE / DELETE
    # ------------------------------------------------------------------
    def update(self, table: str, data: dict[str, Any], where: str, params: Sequence[Any] = ()) -> int:
        if not data:
            return 0
        sets = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder())
            for col in data
        )
        query = sql.SQL("UPDATE {} SET {} WHERE {}").format(
            sql.Identifier(table), sets, sql.SQL(where)
        )
        count = self.execute(query, list(data.values()) + list(params))
        self.commit()
        return count

    def delete(self, table: str, where: str, params: Sequence[Any] = ()) -> int:
        query = sql.SQL("DELETE FROM {} WHERE {}").format(sql.Identifier(table), sql.SQL(where))
        count = self.execute(query, params)
        self.commit()
        return count

    # ------------------------------------------------------------------
    # Служебное
    # ------------------------------------------------------------------
    def ping(self) -> bool:
        try:
            return self.scalar("SELECT 1") == 1
        except psycopg2.Error:
            return False
