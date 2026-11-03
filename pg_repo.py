"""Модуль работы с СУБД PostgreSQL через драйвер psycopg2 (Повышенная 6)."""

from contextlib import contextmanager
from dataclasses import dataclass
import logging
import math
from typing import Any, Callable, Iterator

import psycopg2

from sqlite_repo import validate_non_empty_str, validate_positive_int

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PostgresAccountRecord:
    """Модель записи банковского счёта клиента в PostgreSQL."""

    id: int
    owner_name: str
    email: str
    balance: float


def validate_non_negative_float(value: Any, field_name: str) -> float:
    """Проверяет, что значение — неотрицательное конечное число (не bool)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"Поле '{field_name}' должно быть числом")
    numeric = float(value)
    if math.isnan(numeric) or math.isinf(numeric) or numeric < 0:
        raise ValueError(
            f"Поле '{field_name}' должно быть неотрицательным числом"
        )
    return round(numeric, 2)


class PostgresAccountRepository:
    """Повышенная 6: Репозиторий для работы с PostgreSQL через psycopg2."""

    DEFAULT_DSN = "postgresql://postgres:postgres@localhost:5432/lab7_db"

    def __init__(
        self,
        dsn: str = DEFAULT_DSN,
        connection_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.dsn = validate_non_empty_str(dsn, "dsn")
        self._connect_fn = connection_factory or psycopg2.connect

    @contextmanager
    def _connection(self) -> Iterator[Any]:
        """Управляет соединением и транзакцией PostgreSQL (psycopg2)."""
        conn = self._connect_fn(self.dsn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Создаёт таблицу accounts в базе данных PostgreSQL."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS accounts (
            id SERIAL PRIMARY KEY,
            owner_name VARCHAR(120) NOT NULL,
            email VARCHAR(150) NOT NULL UNIQUE,
            balance NUMERIC(12, 2) NOT NULL DEFAULT 0.00
        );
        """
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_sql)
        logger.info("[PostgreSQL] Таблица 'accounts' инициализирована")

    def create_account(
        self,
        owner_name: str,
        email: str,
        balance: float | int = 0.0,
    ) -> PostgresAccountRecord:
        """Вставляет новую запись в PostgreSQL с использованием RETURNING."""
        clean_owner = validate_non_empty_str(owner_name, "owner_name")
        clean_email = validate_non_empty_str(email, "email")
        if "@" not in clean_email:
            raise ValueError("Некорректный формат email")
        valid_balance = validate_non_negative_float(balance, "balance")

        insert_sql = """
        INSERT INTO accounts (owner_name, email, balance)
        VALUES (%s, %s, %s)
        RETURNING id, owner_name, email, balance;
        """
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    insert_sql,
                    (clean_owner, clean_email, valid_balance),
                )
                row = cur.fetchone()

        record = self._row_to_record(row)
        logger.info(
            "[PostgreSQL] Создан счёт id=%d для '%s'",
            record.id,
            record.owner_name,
        )
        return record

    def get_account(self, account_id: int) -> PostgresAccountRecord | None:
        """Выбирает запись счёта по ID из PostgreSQL."""
        valid_id = validate_positive_int(account_id, "account_id")
        select_sql = """
        SELECT id, owner_name, email, balance
        FROM accounts
        WHERE id = %s;
        """
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(select_sql, (valid_id,))
                row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def update_balance(
        self,
        account_id: int,
        new_balance: float | int,
    ) -> PostgresAccountRecord | None:
        """Обновляет баланс счёта в PostgreSQL с проверкой существования."""
        valid_id = validate_positive_int(account_id, "account_id")
        valid_balance = validate_non_negative_float(
            new_balance, "new_balance"
        )

        existing = self.get_account(valid_id)
        if existing is None:
            return None

        update_sql = """
        UPDATE accounts
        SET balance = %s
        WHERE id = %s
        RETURNING id, owner_name, email, balance;
        """
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(update_sql, (valid_balance, valid_id))
                row = cur.fetchone()

        if row is None:
            return None
        record = self._row_to_record(row)
        logger.info(
            "[PostgreSQL] Обновлён баланс счёта id=%d -> %.2f",
            record.id,
            record.balance,
        )
        return record

    def list_accounts(self) -> list[PostgresAccountRecord]:
        """Возвращает все счета из таблицы accounts PostgreSQL."""
        select_all_sql = """
        SELECT id, owner_name, email, balance
        FROM accounts
        ORDER BY id ASC;
        """
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(select_all_sql)
                rows = cur.fetchall()
        return [self._row_to_record(row) for row in rows]

    def delete_account(self, account_id: int) -> bool:
        """Удаляет счёт по ID из PostgreSQL."""
        valid_id = validate_positive_int(account_id, "account_id")
        existing = self.get_account(valid_id)
        if existing is None:
            return False

        delete_sql = "DELETE FROM accounts WHERE id = %s;"
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(delete_sql, (valid_id,))

        logger.info("[PostgreSQL] Удалён счёт id=%d", valid_id)
        return True

    @staticmethod
    def _row_to_record(row: tuple[Any, ...]) -> PostgresAccountRecord:
        return PostgresAccountRecord(
            id=int(row[0]),
            owner_name=str(row[1]),
            email=str(row[2]),
            balance=float(row[3]),
        )
