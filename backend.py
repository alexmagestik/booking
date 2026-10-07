"""Бизнес-логика проекта: CRUD, проверка доступности, автосоздание таблиц."""

from datetime import datetime, timedelta
from typing import Optional

from postgres_driver import PostgresDriver
from models import Booking, Table, User


class BookingConflictError(Exception):
    """Выбрасывается, если столик уже занят на запрошенный интервал."""


def get_db() -> PostgresDriver:
    return PostgresDriver()


# ----------------------------------------------------------------------
# Автосоздание таблиц
# ----------------------------------------------------------------------
def init_db(db: Optional[PostgresDriver] = None) -> None:
    """Создать таблицы для моделей User, Table, Booking (если их нет)."""
    own = db is None
    db = db or get_db()
    try:
        for model in (User, Table, Booking):
            db.create_table(
                model.table_name,
                model.ddl_columns,
                primary_key="id",
                foreign_keys=model.foreign_keys,
                if_not_exists=True,
            )
    finally:
        if own:
            db.close()


def drop_all(db: Optional[PostgresDriver] = None) -> None:
    """Удалить все таблицы проекта."""
    own = db is None
    db = db or get_db()
    try:
        for model in (Booking, Table, User):
            db.drop_table(model.table_name, if_exists=True)
    finally:
        if own:
            db.close()


# ----------------------------------------------------------------------
# User CRUD
# ----------------------------------------------------------------------
def create_user(
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    db: Optional[PostgresDriver] = None,
) -> User:
    own = db is None
    db = db or get_db()
    try:
        user = User(name=name, email=email or None, phone=phone or None)
        user.id = db.insert(User.table_name, user.to_dict())
        return user
    finally:
        if own:
            db.close()


def get_user(user_id: int, db: Optional[PostgresDriver] = None) -> Optional[User]:
    own = db is None
    db = db or get_db()
    try:
        return User.from_row(db.select_one(User.table_name, "id = %s", (user_id,)))
    finally:
        if own:
            db.close()


def get_all_users(db: Optional[PostgresDriver] = None) -> list[User]:
    own = db is None
    db = db or get_db()
    try:
        rows = db.select(User.table_name, order_by="id")
        return [User.from_row(r) for r in rows]
    finally:
        if own:
            db.close()


def update_user(user_id: int, **fields) -> int:
    with get_db() as db:
        clean = {k: v for k, v in fields.items() if v is not None}
        return db.update(User.table_name, clean, "id = %s", (user_id,))


def delete_user(user_id: int) -> int:
    with get_db() as db:
        return db.delete(User.table_name, "id = %s", (user_id,))


# ----------------------------------------------------------------------
# Table CRUD
# ----------------------------------------------------------------------
def create_table(
    number: int,
    seats: int = 2,
    location: str = "hall",
    is_active: bool = True,
    db: Optional[PostgresDriver] = None,
) -> Table:
    own = db is None
    db = db or get_db()
    try:
        table = Table(number=number, seats=seats, location=location, is_active=is_active)
        table.id = db.insert(Table.table_name, table.to_dict())
        return table
    finally:
        if own:
            db.close()


def get_table(table_id: int, db: Optional[PostgresDriver] = None) -> Optional[Table]:
    own = db is None
    db = db or get_db()
    try:
        return Table.from_row(db.select_one(Table.table_name, "id = %s", (table_id,)))
    finally:
        if own:
            db.close()


def get_all_tables(db: Optional[PostgresDriver] = None) -> list[Table]:
    own = db is None
    db = db or get_db()
    try:
        rows = db.select(Table.table_name, order_by="number")
        return [Table.from_row(r) for r in rows]
    finally:
        if own:
            db.close()


def update_table(table_id: int, **fields) -> int:
    with get_db() as db:
        clean = {k: v for k, v in fields.items() if v is not None}
        return db.update(Table.table_name, clean, "id = %s", (table_id,))


def delete_table(table_id: int) -> int:
    with get_db() as db:
        return db.delete(Table.table_name, "id = %s", (table_id,))


# ----------------------------------------------------------------------
# Booking CRUD + проверка доступности
# ----------------------------------------------------------------------
def check_table_availability(
    table_id: int,
    start_time: datetime,
    duration_minutes: int = 60,
    db: Optional[PostgresDriver] = None,
    exclude_booking_id: Optional[int] = None,
) -> bool:
    """True, если столик свободен в заданном интервале.

    Запрещены пересекающиеся бронирования одного столика:
    существующее бронь [s1, e1) пересекается с новым [s2, e2),
    если s1 < e2 И s2 < e1.
    """
    return get_conflicting_bookings(
        table_id, start_time, duration_minutes, db, exclude_booking_id
    ) == []


def get_conflicting_bookings(
    table_id: int,
    start_time: datetime,
    duration_minutes: int = 60,
    db: Optional[PostgresDriver] = None,
    exclude_booking_id: Optional[int] = None,
) -> list[Booking]:
    own = db is None
    db = db or get_db()
    try:
        end_time = start_time + timedelta(minutes=duration_minutes)
        query = (
            "SELECT * FROM bookings "
            "WHERE table_id = %s "
            "AND status <> 'cancelled' "
            "AND start_time < %s "
            "AND start_time + duration_minutes * INTERVAL '1 minute' > %s"
        )
        params: list = [table_id, end_time, start_time]
        if exclude_booking_id is not None:
            query += " AND id <> %s"
            params.append(exclude_booking_id)
        query += " ORDER BY start_time"
        rows = db.fetchall(query, params)
        return [Booking.from_row(r) for r in rows]
    finally:
        if own:
            db.close()


def create_booking(
    user_id: int,
    table_id: int,
    start_time: datetime,
    duration_minutes: int = 60,
    guests_count: int = 1,
    status: str = "confirmed",
    db: Optional[PostgresDriver] = None,
) -> Booking:
    """Создать бронирование; бросает BookingConflictError при пересечении."""
    own = db is None
    db = db or get_db()
    try:
        if get_user(user_id, db) is None:
            raise ValueError(f"Пользователь с id={user_id} не найден")
        table = get_table(table_id, db)
        if table is None:
            raise ValueError(f"Столик с id={table_id} не найден")
        if not table.is_active:
            raise ValueError(f"Столик №{table.number} неактивен")
        if guests_count > table.seats:
            raise ValueError(
                f"Столик №{table.number} рассчитан на {table.seats} гостей, запрошено {guests_count}"
            )
        if duration_minutes <= 0:
            raise ValueError("Длительность должна быть положительной")

        if not check_table_availability(table_id, start_time, duration_minutes, db):
            conflicts = get_conflicting_bookings(table_id, start_time, duration_minutes, db)
            details = ", ".join(
                f"#{b.id} {b.start_time:%Y-%m-%d %H:%M}" for b in conflicts
            )
            raise BookingConflictError(
                f"Столик №{table.number} занят в указанный интервал ({details})"
            )

        booking = Booking(
            user_id=user_id,
            table_id=table_id,
            start_time=start_time,
            duration_minutes=duration_minutes,
            guests_count=guests_count,
            status=status,
        )
        booking.id = db.insert(Booking.table_name, booking.to_dict())
        return booking
    finally:
        if own:
            db.close()


def get_booking(booking_id: int, db: Optional[PostgresDriver] = None) -> Optional[Booking]:
    own = db is None
    db = db or get_db()
    try:
        return Booking.from_row(db.select_one(Booking.table_name, "id = %s", (booking_id,)))
    finally:
        if own:
            db.close()


def get_all_bookings(db: Optional[PostgresDriver] = None) -> list[Booking]:
    own = db is None
    db = db or get_db()
    try:
        rows = db.select(Booking.table_name, order_by="start_time")
        return [Booking.from_row(r) for r in rows]
    finally:
        if own:
            db.close()


def get_bookings_by_user(user_id: int, db: Optional[PostgresDriver] = None) -> list[Booking]:
    own = db is None
    db = db or get_db()
    try:
        rows = db.select(Booking.table_name, "user_id = %s", (user_id,), order_by="start_time")
        return [Booking.from_row(r) for r in rows]
    finally:
        if own:
            db.close()


def update_booking(booking_id: int, **fields) -> int:
    with get_db() as db:
        clean = {k: v for k, v in fields.items() if v is not None}
        return db.update(Booking.table_name, clean, "id = %s", (booking_id,))


def cancel_booking(booking_id: int) -> int:
    return update_booking(booking_id, status="cancelled")


def delete_booking(booking_id: int) -> int:
    with get_db() as db:
        return db.delete(Booking.table_name, "id = %s", (booking_id,))


# ----------------------------------------------------------------------
# Тестовые данные
# ----------------------------------------------------------------------
SEED_USERS = [
    ("Иван Петров", "ivan@example.com", "+7-900-111-22-33"),
    ("Мария Сидорова", "maria@example.com", "+7-900-222-33-44"),
    ("Алексей Кузнецов", "alex@example.com", "+7-900-333-44-55"),
    ("Ольга Смирнова", "olga@example.com", "+7-900-444-55-66"),
]

SEED_TABLES = [
    (1, 2, "hall"),
    (2, 4, "hall"),
    (3, 4, "terrace"),
    (4, 8, "private"),
]


def seed_data(db: Optional[PostgresDriver] = None) -> dict:
    """Добавить тестовые данные: пользователей, столики, бронирования."""
    own = db is None
    db = db or get_db()
    try:
        created = {"users": 0, "tables": 0, "bookings": 0}

        if db.count(User.table_name) == 0:
            for name, email, phone in SEED_USERS:
                create_user(name, email, phone, db)
                created["users"] += 1

        if db.count(Table.table_name) == 0:
            for number, seats, location in SEED_TABLES:
                create_table(number, seats, location, db=db)
                created["tables"] += 1

        if db.count(Booking.table_name) == 0:
            users = get_all_users(db)
            tables = get_all_tables(db)
            now = datetime.now().replace(minute=0, second=0, microsecond=0)
            samples = [
                (users[0].id, tables[0].id, now + timedelta(days=1, hours=19), 90, 2),
                (users[1].id, tables[1].id, now + timedelta(days=1, hours=20), 60, 3),
                (users[2].id, tables[2].id, now + timedelta(days=2, hours=18), 120, 4),
            ]
            for user_id, table_id, start, duration, guests in samples:
                try:
                    create_booking(user_id, table_id, start, duration, guests, db=db)
                    created["bookings"] += 1
                except BookingConflictError:
                    pass

        return created
    finally:
        if own:
            db.close()


def setup_database(seed: bool = True) -> dict:
    """Полная инициализация: создание таблиц + тестовые данные."""
    db = get_db()
    try:
        init_db(db)
        result = {"tables_created": True}
        if seed:
            result["seed"] = seed_data(db)
        return result
    finally:
        db.close()


if __name__ == "__main__":
    print("Инициализация базы данных...", setup_database())
    print("Пользователи:", len(get_all_users()))
    print("Столики:", len(get_all_tables()))
    print("Бронирования:", len(get_all_bookings()))
