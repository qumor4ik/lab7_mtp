"""Модуль работы с СУБД SQLite3 (Средняя 2, Средняя 4, Средняя 7)."""

from contextlib import contextmanager
from dataclasses import dataclass
import logging
import math
import sqlite3
from typing import Any, Iterator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DepartmentRecord:
    """Модель записи таблицы подразделений (departments)."""

    id: int
    name: str
    location: str


@dataclass(frozen=True)
class EmployeeRecord:
    """Модель записи таблицы сотрудников (employees)."""

    id: int
    full_name: str
    position: str
    salary: float
    department_id: int
    department_name: str | None = None


def validate_non_empty_str(value: Any, field_name: str) -> str:
    """Проверяет, что значение является непустой строкой."""
    if not isinstance(value, str):
        raise TypeError(f"Поле '{field_name}' должно быть строкой")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"Поле '{field_name}' не может быть пустым")
    return cleaned


def validate_positive_int(value: Any, field_name: str) -> int:
    """Проверяет, что значение — положительное целое число (не bool)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"Поле '{field_name}' должно быть целым числом")
    if value <= 0:
        raise ValueError(
            f"Поле '{field_name}' должно быть положительным числом"
        )
    return value


def validate_positive_float(value: Any, field_name: str) -> float:
    """Проверяет, что значение — положительное конечное число (не bool)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"Поле '{field_name}' должно быть числом")
    numeric = float(value)
    if math.isnan(numeric) or math.isinf(numeric) or numeric <= 0:
        raise ValueError(
            f"Поле '{field_name}' должно быть конечным числом больше нуля"
        )
    return round(numeric, 2)


class SQLiteCompanyRepository:
    """Репозиторий SQLite3 для работы с несколькими таблицами."""

    def __init__(self, db_path: str = "company.db") -> None:
        self.db_path = validate_non_empty_str(db_path, "db_path")
        self.create_tables()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Открывает соединение с SQLite с поддержкой внешних ключей."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_tables(self) -> None:
        """Средняя 7: Создаёт несколько связанных таблиц в БД SQLite."""
        departments_sql = """
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            location TEXT NOT NULL
        )
        """
        employees_sql = """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            position TEXT NOT NULL,
            salary REAL NOT NULL CHECK (salary > 0),
            department_id INTEGER NOT NULL,
            FOREIGN KEY (department_id)
                REFERENCES departments (id)
                ON DELETE CASCADE
        )
        """
        with self._connect() as conn:
            conn.execute(departments_sql)
            conn.execute(employees_sql)
        logger.info("Таблицы 'departments' и 'employees' инициализированы")

    def insert_department(
        self,
        name: str,
        location: str,
    ) -> DepartmentRecord:
        """Средняя 2: Вставляет новую запись в таблицу departments."""
        clean_name = validate_non_empty_str(name, "name")
        clean_loc = validate_non_empty_str(location, "location")

        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO departments (name, location) VALUES (?, ?)",
                (clean_name, clean_loc),
            )
            dept_id = int(cursor.lastrowid or 0)

        record = DepartmentRecord(
            id=dept_id,
            name=clean_name,
            location=clean_loc,
        )
        logger.info(
            "Вставлен отдел в SQLite: id=%d, name='%s'",
            dept_id,
            clean_name,
        )
        return record

    def insert_employee(
        self,
        full_name: str,
        position: str,
        salary: float | int,
        department_id: int,
    ) -> EmployeeRecord:
        """Средняя 2: Вставляет новую запись в таблицу employees."""
        clean_name = validate_non_empty_str(full_name, "full_name")
        clean_pos = validate_non_empty_str(position, "position")
        valid_salary = validate_positive_float(salary, "salary")
        valid_dept_id = validate_positive_int(department_id, "department_id")

        with self._connect() as conn:
            dept_row = conn.execute(
                "SELECT id, name FROM departments WHERE id = ?",
                (valid_dept_id,),
            ).fetchone()
            if dept_row is None:
                raise ValueError(
                    f"Подразделение с id={valid_dept_id} не существует"
                )

            cursor = conn.execute(
                "INSERT INTO employees "
                "(full_name, position, salary, department_id) "
                "VALUES (?, ?, ?, ?)",
                (clean_name, clean_pos, valid_salary, valid_dept_id),
            )
            emp_id = int(cursor.lastrowid or 0)

        record = EmployeeRecord(
            id=emp_id,
            full_name=clean_name,
            position=clean_pos,
            salary=valid_salary,
            department_id=valid_dept_id,
            department_name=str(dept_row["name"]),
        )
        logger.info(
            "Вставлен сотрудник в SQLite: id=%d, name='%s'",
            emp_id,
            clean_name,
        )
        return record

    def get_employee(self, employee_id: int) -> EmployeeRecord | None:
        """Возвращает запись сотрудника по ID вместе с названием отдела."""
        valid_id = validate_positive_int(employee_id, "employee_id")
        query = """
        SELECT
            e.id,
            e.full_name,
            e.position,
            e.salary,
            e.department_id,
            d.name AS department_name
        FROM employees e
        JOIN departments d ON d.id = e.department_id
        WHERE e.id = ?
        """
        with self._connect() as conn:
            row = conn.execute(query, (valid_id,)).fetchone()
        if row is None:
            return None
        return EmployeeRecord(
            id=int(row["id"]),
            full_name=str(row["full_name"]),
            position=str(row["position"]),
            salary=float(row["salary"]),
            department_id=int(row["department_id"]),
            department_name=str(row["department_name"]),
        )

    def update_employee(
        self,
        employee_id: int,
        new_position: str | None = None,
        new_salary: float | int | None = None,
    ) -> EmployeeRecord | None:
        """Средняя 4: Обновляет должность и/или оклад сотрудника по ID."""
        valid_id = validate_positive_int(employee_id, "employee_id")
        if new_position is None and new_salary is None:
            raise ValueError(
                "Необходимо указать хотя бы одно поле для обновления"
            )

        existing = self.get_employee(valid_id)
        if existing is None:
            return None

        updated_pos = (
            validate_non_empty_str(new_position, "new_position")
            if new_position is not None
            else existing.position
        )
        updated_salary = (
            validate_positive_float(new_salary, "new_salary")
            if new_salary is not None
            else existing.salary
        )

        with self._connect() as conn:
            conn.execute(
                "UPDATE employees SET position = ?, salary = ? WHERE id = ?",
                (updated_pos, updated_salary, valid_id),
            )

        logger.info(
            "Обновлена запись сотрудника id=%d: position='%s', salary=%.2f",
            valid_id,
            updated_pos,
            updated_salary,
        )
        return self.get_employee(valid_id)

    def list_employees(self) -> list[EmployeeRecord]:
        """Возвращает список всех сотрудников с названиями подразделений."""
        query = """
        SELECT
            e.id,
            e.full_name,
            e.position,
            e.salary,
            e.department_id,
            d.name AS department_name
        FROM employees e
        JOIN departments d ON d.id = e.department_id
        ORDER BY e.id ASC
        """
        with self._connect() as conn:
            rows = conn.execute(query).fetchall()
        return [
            EmployeeRecord(
                id=int(row["id"]),
                full_name=str(row["full_name"]),
                position=str(row["position"]),
                salary=float(row["salary"]),
                department_id=int(row["department_id"]),
                department_name=str(row["department_name"]),
            )
            for row in rows
        ]

    def list_departments(self) -> list[DepartmentRecord]:
        """Возвращает список всех подразделений."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, name, location FROM departments ORDER BY id ASC"
            ).fetchall()
        return [
            DepartmentRecord(
                id=int(row["id"]),
                name=str(row["name"]),
                location=str(row["location"]),
            )
            for row in rows
        ]
