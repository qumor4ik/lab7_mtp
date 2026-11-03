"""Модульные тесты (unittest) для лабораторной работы №7 (Вариант 2)."""

import logging
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

import psycopg2

from orm_crud import SQLAlchemyCrudRepository
from pg_repo import PostgresAccountRepository
from sqlite_repo import SQLiteCompanyRepository

logger = logging.getLogger(__name__)


class TestSQLiteTasks(unittest.TestCase):
    """Тесты для заданий Средняя 2, Средняя 4 и Средняя 7 (sqlite3)."""

    def setUp(self) -> None:
        self.fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.fd)
        self.repo = SQLiteCompanyRepository(db_path=self.db_path)

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_create_multiple_tables_and_insert_data(self) -> None:
        """Проверка создания таблиц (Ср. 7) и вставки записей (Ср. 2)."""
        dept_it = self.repo.insert_department("Разработка ПО", "Тула")
        dept_qa = self.repo.insert_department("Тестирование", "Москва")
        self.assertEqual(len(self.repo.list_departments()), 2)

        emp = self.repo.insert_employee(
            full_name="Нестеров Вадим Сергеевич",
            position="Backend-разработчик",
            salary=145000.0,
            department_id=dept_it.id,
        )
        self.assertEqual(emp.id, 1)
        self.assertEqual(emp.department_name, "Разработка ПО")

        all_emps = self.repo.list_employees()
        self.assertEqual(len(all_emps), 1)
        self.assertEqual(dept_qa.name, "Тестирование")

    def test_update_record_and_non_existent_handling(self) -> None:
        """Проверка обновления записи (Средняя 4) и проверки существования."""
        dept = self.repo.insert_department("Аналитика", "Тула")
        emp = self.repo.insert_employee(
            full_name="Иванов Алексей",
            position="Младший аналитик",
            salary=80000,
            department_id=dept.id,
        )

        updated = self.repo.update_employee(
            employee_id=emp.id,
            new_position="Старший аналитик",
            new_salary=125000.50,
        )
        self.assertIsNotNone(updated)
        if updated is not None:
            self.assertEqual(updated.position, "Старший аналитик")
            self.assertEqual(updated.salary, 125000.50)

        missing = self.repo.update_employee(
            employee_id=999,
            new_salary=100000,
        )
        self.assertIsNone(missing)

    def test_sqlite_validation_and_foreign_key(self) -> None:
        """Проверка валидации входных данных и внешних ключей."""
        with self.assertRaises(ValueError):
            self.repo.insert_department("   ", "Тула")

        with self.assertRaises(ValueError):
            self.repo.insert_employee("Петров П.П.", "Инженер", 90000, 999)

        dept = self.repo.insert_department("DevOps", "Казань")
        with self.assertRaises(TypeError):
            self.repo.insert_employee("Петров П.П.", "SRE", True, dept.id)

        with self.assertRaises(ValueError):
            self.repo.insert_employee("Петров П.П.", "SRE", -500, dept.id)


class TestSQLAlchemyORMCrud(unittest.TestCase):
    """Тесты для задания Повышенная 2 (CRUD через SQLAlchemy ORM)."""

    def setUp(self) -> None:
        self.fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.fd)
        self.orm_repo = SQLAlchemyCrudRepository(
            db_url=f"sqlite:///{self.db_path}"
        )

    def tearDown(self) -> None:
        self.orm_repo.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_full_orm_crud_lifecycle(self) -> None:
        """Проверка CREATE, READ, UPDATE, DELETE через SQLAlchemy ORM."""
        project = self.orm_repo.create_project("Система Доступ-БД", 450000)
        self.assertEqual(project.id, 1)
        self.assertEqual(project.budget, 450000.0)

        task1 = self.orm_repo.create_task(project.id, "Спроектировать схему")
        task2 = self.orm_repo.create_task(project.id, "Написать ORM-модели")
        self.assertFalse(task1.is_completed)
        self.assertEqual(len(self.orm_repo.list_tasks(project.id)), 2)

        updated_proj = self.orm_repo.update_project_budget(
            project.id, 520000.0
        )
        self.assertIsNotNone(updated_proj)
        if updated_proj is not None:
            self.assertEqual(updated_proj.budget, 520000.0)
            self.assertEqual(updated_proj.task_count, 2)

        updated_task = self.orm_repo.update_task_status(task1.id, True)
        self.assertIsNotNone(updated_task)
        if updated_task is not None:
            self.assertTrue(updated_task.is_completed)

        self.assertTrue(self.orm_repo.delete_task(task2.id))
        self.assertFalse(self.orm_repo.delete_task(task2.id))

        self.assertTrue(self.orm_repo.delete_project(project.id))
        self.assertIsNone(self.orm_repo.get_project(project.id))
        self.assertEqual(len(self.orm_repo.list_tasks()), 0)

    def test_orm_validation_errors(self) -> None:
        """Проверка защиты ORM-репозитория от некорректных типов."""
        with self.assertRaises(TypeError):
            self.orm_repo.create_project("Проект", True)
        with self.assertRaises(ValueError):
            self.orm_repo.create_task(999, "Задача без проекта")


class TestPostgresPsycopg2Repository(unittest.TestCase):
    """Тесты для задания Повышенная 6 (Работа с PostgreSQL через psycopg2)."""

    def setUp(self) -> None:
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value.__enter__.return_value = (
            self.mock_cursor
        )
        self.factory = MagicMock(return_value=self.mock_conn)
        self.pg_repo = PostgresAccountRepository(
            dsn="postgresql://user:pass@localhost:5432/test_db",
            connection_factory=self.factory,
        )

    def test_init_schema_and_create_account(self) -> None:
        """Проверка создания таблицы и параметризованного INSERT (%s)."""
        self.pg_repo.init_schema()
        self.mock_conn.commit.assert_called_once()
        self.mock_conn.close.assert_called_once()

        self.mock_cursor.fetchone.return_value = (
            1,
            "Нестеров Вадим",
            "vadim@example.com",
            25000.00,
        )
        created = self.pg_repo.create_account(
            owner_name="Нестеров Вадим",
            email="vadim@example.com",
            balance=25000,
        )
        self.assertEqual(created.id, 1)
        self.assertEqual(created.email, "vadim@example.com")
        self.assertEqual(created.balance, 25000.0)

        executed_sql, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("INSERT INTO accounts", executed_sql)
        self.assertIn("%s", executed_sql)
        self.assertEqual(
            params, ("Нестеров Вадим", "vadim@example.com", 25000.0)
        )

    def test_update_and_delete_account_in_postgres(self) -> None:
        """Проверка UPDATE и DELETE в PostgreSQL через psycopg2."""
        self.mock_cursor.fetchone.side_effect = [
            (1, "Нестеров Вадим", "vadim@example.com", 25000.0),
            (1, "Нестеров Вадим", "vadim@example.com", 40000.0),
            (1, "Нестеров Вадим", "vadim@example.com", 40000.0),
            None,
        ]

        updated = self.pg_repo.update_balance(1, 40000.0)
        self.assertIsNotNone(updated)
        if updated is not None:
            self.assertEqual(updated.balance, 40000.0)

        deleted = self.pg_repo.delete_account(1)
        self.assertTrue(deleted)

        deleted_again = self.pg_repo.delete_account(1)
        self.assertFalse(deleted_again)

    def test_rollback_on_psycopg2_database_error(self) -> None:
        """Проверка вызова rollback() при ошибке psycopg2.DatabaseError."""
        self.mock_cursor.execute.side_effect = psycopg2.DatabaseError(
            "Ошибка сбоя связи"
        )
        with self.assertRaises(psycopg2.DatabaseError):
            self.pg_repo.init_schema()

        self.mock_conn.rollback.assert_called_once()
        self.mock_conn.close.assert_called_once()

    def test_postgres_input_validation(self) -> None:
        """Проверка валидации email и числовых полей."""
        with self.assertRaises(ValueError):
            self.pg_repo.create_account("Вадим", "invalid-email", 100)
        with self.assertRaises(TypeError):
            self.pg_repo.create_account("Вадим", "vadim@example.com", True)
        with self.assertRaises(ValueError):
            self.pg_repo.create_account("Вадим", "vadim@example.com", -10)


def run_all_tests() -> bool:
    """Запускает набор unittest-тестов с использованием sys.modules."""
    current_module = sys.modules[__name__]
    suite = unittest.defaultTestLoader.loadTestsFromModule(current_module)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    if not result.wasSuccessful():
        raise RuntimeError("Модульные тесты завершились с ошибками")
    logger.info("[TESTS] Все unittest-проверки лабораторной №7 пройдены!")
    return True


if __name__ == "__main__":
    run_all_tests()
