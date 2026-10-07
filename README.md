# Система бронирования столиков ресторана

Проект на Python: работа с PostgreSQL через `psycopg2`, модели `User` / `Table` / `Booking`,
CRUD-логика, запрет пересекающихся бронирований и графический интерфейс на `tkinter`.

## Структура

```
booking/
├── postgres_driver.py     # класс PostgresDriver (DDL + CRUD над psycopg2)
├── models/
│   ├── base.py            # базовая модель
│   ├── user.py            # модель User
│   ├── table.py           # модель Table
│   └── booking.py         # модель Booking
├── backend.py             # CRUD, check_table_availability, init_db, seed_data
├── app.py                 # GUI (tkinter)
├── requirements.txt
├── .env.example           # шаблон параметров подключения
└── .env                   # реальные параметры подключения (не коммитить)
```

## Настройка

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # и заполнить параметры вашего PostgreSQL
```

Параметры подключения читаются из `.env`:

| Переменная    | Описание            |
|---------------|---------------------|
| `PGHOST`      | хост                |
| `PGPORT`      | порт                |
| `PGDATABASE`  | имя базы данных     |
| `PGUSER`      | пользователь        |
| `PGPASSWORD`  | пароль              |

## Запуск

```bash
# 1. Создать таблицы и загрузить тестовые данные
python3 backend.py

# 2. Запустить графический интерфейс
python3 app.py
```

`app.py` при старте также автоматически создаёт таблицы и загружает тестовые данные,
если их ещё нет.

## Тестовые данные

При первом запуске создаются:

- **4 пользователя**: Иван Петров, Мария Сидорова, Алексей Кузнецов, Ольга Смирнова
- **4 столика**: №1 (2 места, hall), №2 (4 места, hall), №3 (4 места, terrace), №4 (8 мест, private)
- **3 бронирования**: на завтра/послезавтра для столиков 1–3

## Проверка доступности

`backend.check_table_availability(table_id, start_time, duration_minutes, ...)`
возвращает `True`, если столик свободен. Пересечение интервалов определяется по правилу:

```
existing_start < new_end AND new_start < existing_end
```

Создание бронирования (`create_booking`) дополнительно бросает `BookingConflictError`,
если интервал пересекается с уже существующим активным бронированием того же столика.

Пример в консоли:

```python
from datetime import datetime
import backend as bk

bk.init_db()
start = datetime(2026, 10, 10, 19, 0)
print(bk.check_table_availability(1, start, 90))   # True / False
print(bk.get_conflicting_bookings(1, start, 90))   # список конфликтов
```

## GUI (app.py)

Вкладки приложения:

- **Пользователи** — добавление/удаление клиентов
- **Столики** — добавление/удаление столов
- **Бронирование** — создание брони, кнопка **«Проверить доступность»**, отмена брони
- **Проверка доступности** — отдельная вкладка с кнопкой **«Проверить доступность»**
  и подробным отчётом по свободным/занятым интервалам

## Основные функции backend.py

| Функция                       | Назначение                                    |
|-------------------------------|-----------------------------------------------|
| `init_db()`                   | автосоздание таблиц User, Table, Booking      |
| `setup_database(seed=True)`   | создание таблиц + тестовые данные             |
| `create_user/get/get_all/update/delete_user` | CRUD пользователей             |
| `create_table/get/get_all/update/delete_table` | CRUD столов                 |
| `create_booking/get/get_all/cancel/delete_booking` | CRUD бронирований      |
| `check_table_availability()`  | проверка столика на пересечение броней        |
| `get_conflicting_bookings()`  | список бронирований, пересекающих интервал    |
