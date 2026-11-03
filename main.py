"""Точка входа для лабораторной работы №7 (Вариант 2)."""

import argparse
import logging
import os
import sys
import tempfile
from typing import Any

import psycopg2

from orm_crud import SQLAlchemyCrudRepository
from pg_repo import PostgresAccountRepository
from sqlite_repo import SQLiteCompanyRepository
from tests import run_all_tests

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


class InMemoryPsycopg2Adapter:
    """Встроенный DB-API 2.0 адаптер для автономной демонстрации psycopg2."""

    def __init__(self) -> None:
        self._storage: dict[int, tuple[int, str, str, float]] = {}
        self._seq: int = 0
        self._last_result: list[tuple[Any, ...]] = []

    def cursor(self) -> "InMemoryPsycopg2Adapter":
        return self

    def __enter__(self) -> "InMemoryPsycopg2Adapter":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def execute(
        self,
        sql: str,
        params: tuple[Any, ...] | None = None,
    ) -> None:
        normalized = " ".join(sql.strip().upper().split())
        if normalized.startswith("CREATE TABLE"):
            self._last_result = []
            return

        if normalized.startswith("INSERT INTO ACCOUNTS"):
            assert params is not None
            self._seq += 1
            row = (
                self._seq,
                str(params[0]),
                str(params[1]),
                float(params[2]),
            )
            self._storage[self._seq] = row
            self._last_result = [row]
            return

        if normalized.startswith("SELECT") and "WHERE ID = %S" in normalized:
            assert params is not None
            rec = self._storage.get(int(params[0]))
            self._last_result = [rec] if rec is not None else []
            return

        if normalized.startswith("SELECT"):
            self._last_result = [
                self._storage[k] for k in sorted(self._storage.keys())
            ]
            return

        if normalized.startswith("UPDATE ACCOUNTS"):
            assert params is not None
            new_bal = float(params[0])
            acc_id = int(params[1])
            old = self._storage[acc_id]
            updated = (old[0], old[1], old[2], new_bal)
            self._storage[acc_id] = updated
            self._last_result = [updated]
            return

        if normalized.startswith("DELETE FROM ACCOUNTS"):
            assert params is not None
            self._storage.pop(int(params[0]), None)
            self._last_result = []

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._last_result[0] if self._last_result else None

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._last_result)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


def run_postgres_demo(dsn: str) -> None:
    """Демонстрирует Повышенную 6 (PostgreSQL через psycopg2)."""
    try:
        conn = psycopg2.connect(dsn, connect_timeout=2)
        conn.close()
        pg_repo = PostgresAccountRepository(dsn=dsn)
        logger.info("[Повышенная 6] Подключено к серверу PostgreSQL.")
    except (psycopg2.Error, UnicodeDecodeError):
        adapter = InMemoryPsycopg2Adapter()
        pg_repo = PostgresAccountRepository(
            dsn=dsn,
            connection_factory=lambda _dsn: adapter,
        )
        logger.info(
            "[Повышенная 6] Локальный сервер PostgreSQL недоступен — "
            "используется автономный адаптер psycopg2 DB-API 2.0."
        )

    pg_repo.init_schema()
    acc = pg_repo.create_account(
        owner_name="Нестеров Вадим Сергеевич",
        email="nesterov.v@university.ru",
        balance=50000.0,
    )
    updated_acc = pg_repo.update_balance(acc.id, 75500.0)
    logger.info(
        "[Повышенная 6] Счёт в PostgreSQL после обновления: %s",
        updated_acc,
    )


def run_console_demo(pg_dsn: str) -> None:
    """Последовательно демонстрирует все 5 заданий варианта 2."""
    logger.info("=== Лабораторная работа №7 (Вариант 2) ===")

    fd1, sqlite_path = tempfile.mkstemp(suffix=".db")
    os.close(fd1)
    fd2, orm_path = tempfile.mkstemp(suffix=".db")
    os.close(fd2)

    try:
        # Средняя 7, Средняя 2, Средняя 4 (sqlite3)
        sqlite_repo = SQLiteCompanyRepository(db_path=sqlite_path)
        dept = sqlite_repo.insert_department(
            name="Отдел проектирования СУБД",
            location="Тула",
        )
        emp = sqlite_repo.insert_employee(
            full_name="Нестеров Вадим Сергеевич",
            position="Архитектор БД",
            salary=160000.0,
            department_id=dept.id,
        )
        logger.info("[Средняя 2 и 7] Добавлен сотрудник: %s", emp)

        updated_emp = sqlite_repo.update_employee(
            employee_id=emp.id,
            new_position="Ведущий архитектор БД",
            new_salary=195000.0,
        )
        logger.info("[Средняя 4] Обновлена запись сотрудника: %s", updated_emp)

        # Повышенная 2 (CRUD через SQLAlchemy ORM)
        orm_repo = SQLAlchemyCrudRepository(db_url=f"sqlite:///{orm_path}")
        try:
            proj = orm_repo.create_project(
                title="Лабораторная №7 ORM",
                budget=300000.0,
            )
            task = orm_repo.create_task(
                project_id=proj.id,
                title="Реализовать CRUD через SQLAlchemy",
            )
            orm_repo.update_task_status(task.id, True)
            orm_repo.update_project_budget(proj.id, 350000.0)
            logger.info(
                "[Повышенная 2] Проекты в ORM: %s | Задачи: %s",
                orm_repo.list_projects(),
                orm_repo.list_tasks(proj.id),
            )
            orm_repo.delete_task(task.id)
            orm_repo.delete_project(proj.id)
        finally:
            orm_repo.dispose()

        # Повышенная 6 (PostgreSQL через psycopg2)
        run_postgres_demo(pg_dsn)
    finally:
        for path in (sqlite_path, orm_path):
            if os.path.exists(path):
                os.remove(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разбирает аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="Лабораторная работа №7: Работа с СУБД в Python",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Запустить только модульные автотесты (unittest)",
    )
    parser.add_argument(
        "--pg-dsn",
        type=str,
        default=os.environ.get(
            "PG_DSN",
            PostgresAccountRepository.DEFAULT_DSN,
        ),
        help="Строка подключения DSN для PostgreSQL (psycopg2)",
    )
    return parser.parse_args(argv)


def main() -> None:
    """Точка входа приложения."""
    args = parse_args()
    if args.test:
        run_all_tests()
        return

    run_all_tests()
    run_console_demo(pg_dsn=args.pg_dsn)


if __name__ == "__main__":
    main()
