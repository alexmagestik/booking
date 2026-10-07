"""Tkinter-интерфейс системы бронирования столиков ресторана."""

import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

import backend as bk
from backend import BookingConflictError

DATE_FORMATS = ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%Y-%m-%dT%H:%M", "%Y/%m/%d %H:%M")


def parse_datetime(value: str) -> datetime:
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError("Неверный формат даты/времени. Используйте ГГГГ-ММ-ДД ЧЧ:ММ")


class BookingApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Ресторан — бронирование столиков")
        self.geometry("980x620")
        self.minsize(860, 560)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._build_users_tab()
        self._build_tables_tab()
        self._build_bookings_tab()
        self._build_availability_tab()
        self._build_log()

        self.refresh_all()

    # ------------------------------------------------------------------
    # Вкладка "Пользователи"
    # ------------------------------------------------------------------
    def _build_users_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=" Пользователи ")

        form = ttk.LabelFrame(tab, text="Новый пользователь")
        form.pack(fill=tk.X, padx=8, pady=6)

        self.user_name = self._add_entry(form, 0, "Имя")
        self.user_email = self._add_entry(form, 1, "Email")
        self.user_phone = self._add_entry(form, 2, "Телефон")

        btns = ttk.Frame(form)
        btns.grid(row=3, column=0, columnspan=2, sticky="w", pady=6, padx=6)
        ttk.Button(btns, text="Добавить", command=self.add_user).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Удалить выбранного", command=self.delete_user).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Обновить список", command=self.refresh_users).pack(side=tk.LEFT, padx=4)

        self.users_tree = self._add_tree(
            tab, [("id", 50), ("name", 220), ("email", 240), ("phone", 180)]
        )

    # ------------------------------------------------------------------
    # Вкладка "Столики"
    # ------------------------------------------------------------------
    def _build_tables_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=" Столики ")

        form = ttk.LabelFrame(tab, text="Новый столик")
        form.pack(fill=tk.X, padx=8, pady=6)

        self.table_number = self._add_entry(form, 0, "Номер")
        self.table_seats = self._add_entry(form, 1, "Мест")
        self.table_location = self._add_entry(form, 2, "Зона (hall/terrace/private)")

        btns = ttk.Frame(form)
        btns.grid(row=3, column=0, columnspan=2, sticky="w", pady=6, padx=6)
        ttk.Button(btns, text="Добавить", command=self.add_table).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Удалить выбранного", command=self.delete_table).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Обновить список", command=self.refresh_tables).pack(side=tk.LEFT, padx=4)

        self.tables_tree = self._add_tree(
            tab,
            [("id", 50), ("number", 80), ("seats", 70), ("location", 150), ("is_active", 90)],
        )

    # ------------------------------------------------------------------
    # Вкладка "Бронирование"
    # ------------------------------------------------------------------
    def _build_bookings_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=" Бронирование ")

        form = ttk.LabelFrame(tab, text="Новое бронирование")
        form.pack(fill=tk.X, padx=8, pady=6)

        self.booking_user = self._add_combo(form, 0, "Клиент")
        self.booking_table = self._add_combo(form, 1, "Столик")
        self.booking_start = self._add_entry(form, 2, "Начало (ГГГГ-ММ-ДД ЧЧ:ММ)")
        self.booking_duration = self._add_entry(form, 3, "Длительность, мин")
        self.booking_guests = self._add_entry(form, 4, "Гостей")

        self.booking_start.insert(0, (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d 19:00"))
        self.booking_duration.insert(0, "60")
        self.booking_guests.insert(0, "2")

        btns = ttk.Frame(form)
        btns.grid(row=5, column=0, columnspan=2, sticky="w", pady=6, padx=6)
        ttk.Button(btns, text="Забронировать", command=self.add_booking).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Проверить доступность", command=self.check_availability_from_booking).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btns, text="Отменить выбранное", command=self.cancel_booking).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Обновить список", command=self.refresh_bookings).pack(side=tk.LEFT, padx=4)

        self.bookings_tree = self._add_tree(
            tab,
            [
                ("id", 50),
                ("user", 170),
                ("table", 90),
                ("start_time", 150),
                ("duration", 90),
                ("guests", 70),
                ("status", 110),
            ],
        )

    # ------------------------------------------------------------------
    # Вкладка "Проверка доступности"
    # ------------------------------------------------------------------
    def _build_availability_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=" Проверка доступности ")

        form = ttk.LabelFrame(tab, text="Проверить, свободен ли столик")
        form.pack(fill=tk.X, padx=8, pady=6)

        self.avail_table = self._add_combo(form, 0, "Столик")
        self.avail_start = self._add_entry(form, 1, "Начало (ГГГГ-ММ-ДД ЧЧ:ММ)")
        self.avail_duration = self._add_entry(form, 2, "Длительность, мин")

        self.avail_start.insert(0, datetime.now().strftime("%Y-%m-%d 20:00"))
        self.avail_duration.insert(0, "60")

        btns = ttk.Frame(form)
        btns.grid(row=3, column=0, columnspan=2, sticky="w", pady=6, padx=6)
        ttk.Button(btns, text="Проверить доступность", command=self.check_availability_tab).pack(
            side=tk.LEFT, padx=4
        )

        self.avail_result = tk.Text(tab, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.avail_result.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

    # ------------------------------------------------------------------
    # Нижний лог
    # ------------------------------------------------------------------
    def _build_log(self) -> None:
        frame = ttk.LabelFrame(self, text="Журнал")
        frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.log = tk.Text(frame, height=4, state=tk.DISABLED)
        self.log.pack(fill=tk.X, padx=4, pady=4)

    # ------------------------------------------------------------------
    # Вспомогательные виджеты
    # ------------------------------------------------------------------
    def _add_entry(self, parent, row: int, label: str) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=3)
        entry = ttk.Entry(parent, width=42)
        entry.grid(row=row, column=1, sticky="we", padx=6, pady=3)
        parent.columnconfigure(1, weight=1)
        return entry

    def _add_combo(self, parent, row: int, label: str) -> ttk.Combobox:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=3)
        combo = ttk.Combobox(parent, width=40, state="readonly")
        combo.grid(row=row, column=1, sticky="we", padx=6, pady=3)
        parent.columnconfigure(1, weight=1)
        return combo

    def _add_tree(self, parent, columns: list[tuple[str, int]]) -> ttk.Treeview:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        tree = ttk.Treeview(frame, columns=[c for c, _ in columns], show="headings", height=10)
        for name, width in columns:
            tree.heading(name, text=name)
            tree.column(name, width=width, anchor="w")
        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        return tree

    # ------------------------------------------------------------------
    # Утилиты
    # ------------------------------------------------------------------
    def write_log(self, message: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, f"[{datetime.now():%H:%M:%S}] {message}\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def write_availability(self, message: str) -> None:
        self.avail_result.configure(state=tk.NORMAL)
        self.avail_result.delete("1.0", tk.END)
        self.avail_result.insert(tk.END, message)
        self.avail_result.configure(state=tk.DISABLED)

    @staticmethod
    def selected_id(tree: ttk.Treeview) -> int | None:
        selection = tree.selection()
        if not selection:
            return None
        return int(tree.item(selection[0], "values")[0])

    def _fill_combo(self, combo: ttk.Combobox, items: list[tuple[str, int]]) -> None:
        values = [f"#{value} — {label}" for label, value in items]
        combo["values"] = values
        if values and not combo.get():
            combo.current(0)

    def _combo_id(self, combo: ttk.Combobox) -> int | None:
        raw = combo.get()
        if not raw:
            return None
        try:
            return int(raw.split("—")[0].strip().lstrip("#"))
        except (ValueError, IndexError):
            return None

    def _fill_tree(self, tree: ttk.Treeview, rows: list[tuple]) -> None:
        tree.delete(*tree.get_children())
        for row in rows:
            tree.insert("", tk.END, values=row)

    # ------------------------------------------------------------------
    # Обновление списков
    # ------------------------------------------------------------------
    def refresh_users(self) -> None:
        users = bk.get_all_users()
        self._fill_tree(self.users_tree, [(u.id, u.name, u.email or "", u.phone or "") for u in users])
        self._fill_combo(self.booking_user, [(u.name, u.id) for u in users])
        self.write_log(f"Загружено пользователей: {len(users)}")

    def refresh_tables(self) -> None:
        tables = bk.get_all_tables()
        self._fill_tree(
            self.tables_tree,
            [(t.id, t.number, t.seats, t.location, "да" if t.is_active else "нет") for t in tables],
        )
        labels = [(f"№{t.number} ({t.seats} мест, {t.location})", t.id) for t in tables if t.is_active]
        self._fill_combo(self.booking_table, labels)
        self._fill_combo(self.avail_table, [(f"№{t.number} ({t.location})", t.id) for t in tables])
        self.write_log(f"Загружено столиков: {len(tables)}")

    def refresh_bookings(self) -> None:
        bookings = bk.get_all_bookings()
        users = {u.id: u.name for u in bk.get_all_users()}
        tables = {t.id: f"№{t.number}" for t in bk.get_all_tables()}
        rows = [
            (
                b.id,
                users.get(b.user_id, b.user_id),
                tables.get(b.table_id, b.table_id),
                b.start_time.strftime("%Y-%m-%d %H:%M"),
                b.duration_minutes,
                b.guests_count,
                b.status,
            )
            for b in bookings
        ]
        self._fill_tree(self.bookings_tree, rows)
        self.write_log(f"Загружено бронирований: {len(bookings)}")

    def refresh_all(self) -> None:
        self.refresh_users()
        self.refresh_tables()
        self.refresh_bookings()

    # ------------------------------------------------------------------
    # Действия: пользователи
    # ------------------------------------------------------------------
    def add_user(self) -> None:
        name = self.user_name.get().strip()
        if not name:
            messagebox.showwarning("Внимание", "Укажите имя пользователя")
            return
        try:
            user = bk.create_user(name, self.user_email.get().strip(), self.user_phone.get().strip())
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc).strip())
            return
        for entry in (self.user_name, self.user_email, self.user_phone):
            entry.delete(0, tk.END)
        self.write_log(f"Создан пользователь: {user}")
        self.refresh_all()

    def delete_user(self) -> None:
        user_id = self.selected_id(self.users_tree)
        if user_id is None:
            messagebox.showwarning("Внимание", "Выберите пользователя в списке")
            return
        if not messagebox.askyesno("Подтверждение", f"Удалить пользователя #{user_id}?"):
            return
        bk.delete_user(user_id)
        self.write_log(f"Удалён пользователь #{user_id}")
        self.refresh_all()

    # ------------------------------------------------------------------
    # Действия: столики
    # ------------------------------------------------------------------
    def add_table(self) -> None:
        try:
            number = int(self.table_number.get().strip())
            seats = int(self.table_seats.get().strip() or 2)
        except ValueError:
            messagebox.showwarning("Внимание", "Номер и мест должны быть целыми числами")
            return
        location = self.table_location.get().strip() or "hall"
        try:
            table = bk.create_table(number, seats, location)
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc).strip())
            return
        for entry in (self.table_number, self.table_seats, self.table_location):
            entry.delete(0, tk.END)
        self.write_log(f"Создан столик: {table}")
        self.refresh_all()

    def delete_table(self) -> None:
        table_id = self.selected_id(self.tables_tree)
        if table_id is None:
            messagebox.showwarning("Внимание", "Выберите столик в списке")
            return
        if not messagebox.askyesno("Подтверждение", f"Удалить столик #{table_id}?"):
            return
        try:
            bk.delete_table(table_id)
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc).strip())
            return
        self.write_log(f"Удалён столик #{table_id}")
        self.refresh_all()

    # ------------------------------------------------------------------
    # Действия: бронирования
    # ------------------------------------------------------------------
    def _booking_form_data(self) -> tuple[int, int, datetime, int, int]:
        user_id = self._combo_id(self.booking_user)
        table_id = self._combo_id(self.booking_table)
        if user_id is None:
            raise ValueError("Выберите клиента")
        if table_id is None:
            raise ValueError("Выберите столик")
        start = parse_datetime(self.booking_start.get())
        duration = int(self.booking_duration.get().strip() or 60)
        guests = int(self.booking_guests.get().strip() or 1)
        return user_id, table_id, start, duration, guests

    def add_booking(self) -> None:
        try:
            user_id, table_id, start, duration, guests = self._booking_form_data()
            booking = bk.create_booking(user_id, table_id, start, duration, guests)
        except BookingConflictError as exc:
            messagebox.showerror("Конфликт бронирований", str(exc))
            self.write_log(f"Конфликт: {exc}")
            return
        except ValueError as exc:
            messagebox.showwarning("Внимание", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc).strip())
            return
        self.write_log(f"Создано бронирование: {booking}")
        messagebox.showinfo("Готово", f"Бронирование #{booking.id} создано")
        self.refresh_all()

    def check_availability_from_booking(self) -> None:
        try:
            _, table_id, start, duration, _ = self._booking_form_data()
        except ValueError as exc:
            messagebox.showwarning("Внимание", str(exc))
            return
        self._show_availability(table_id, start, duration)
        self.notebook.select(3)

    def check_availability_tab(self) -> None:
        table_id = self._combo_id(self.avail_table)
        if table_id is None:
            messagebox.showwarning("Внимание", "Выберите столик")
            return
        try:
            start = parse_datetime(self.avail_start.get())
            duration = int(self.avail_duration.get().strip() or 60)
        except ValueError as exc:
            messagebox.showwarning("Внимание", str(exc))
            return
        self._show_availability(table_id, start, duration)

    def _show_availability(self, table_id: int, start: datetime, duration: int) -> None:
        table = bk.get_table(table_id)
        label = f"№{table.number}" if table else f"#{table_id}"
        end = start + timedelta(minutes=duration)
        conflicts = bk.get_conflicting_bookings(table_id, start, duration)
        lines = [
            f"Столик {label}: интервал {start:%Y-%m-%d %H:%M} — {end:%Y-%m-%d %H:%M} "
            f"({duration} мин)",
            "",
        ]
        if not conflicts:
            lines.append("РЕЗУЛЬТАТ: СВОБОДЕН — бронирование возможно.")
        else:
            lines.append(f"РЕЗУЛЬТАТ: ЗАНЯТ — пересекающихся бронирований: {len(conflicts)}")
            for b in conflicts:
                lines.append(
                    f"  • бронь #{b.id}: {b.start_time:%Y-%m-%d %H:%M} — {b.end_time:%Y-%m-%d %H:%M}"
                )
        text = "\n".join(lines)
        self.write_availability(text)
        self.write_log(text.replace("\n", " | "))

    def cancel_booking(self) -> None:
        booking_id = self.selected_id(self.bookings_tree)
        if booking_id is None:
            messagebox.showwarning("Внимание", "Выберите бронирование в списке")
            return
        if not messagebox.askyesno("Подтверждение", f"Отменить бронирование #{booking_id}?"):
            return
        bk.cancel_booking(booking_id)
        self.write_log(f"Бронирование #{booking_id} отменено")
        self.refresh_all()


def main() -> None:
    try:
        bk.setup_database(seed=True)
    except Exception as exc:
        messagebox.showerror(
            "Ошибка подключения",
            "Не удалось подключиться к PostgreSQL.\n"
            "Проверьте параметры в файле .env.\n\n"
            f"{exc}",
        )
        return
    app = BookingApp()
    app.write_log("База данных инициализирована, тестовые данные загружены")
    app.mainloop()


if __name__ == "__main__":
    main()
