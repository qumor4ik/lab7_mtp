# Лабораторная работа №7: Работа с различными СУБД в Python
**Выполнил:** Нестеров Вадим Сергеевич  
**Группа:** 221141  
**Вариант:** 2
## Описание заданий (Вариант 2)
В проекте реализована работа с реляционными базами данных через встроенный модуль `sqlite3`, ORM `SQLAlchemy 2.0` и драйвер `psycopg2` для `PostgreSQL`:
- **Средняя 2 (Задание №1 в варианте):** Вставка данных в связанные таблицы `departments` и `employees` с параметризованными запросами (`SQLiteCompanyRepository.insert_department`, `insert_employee`).
- **Средняя 4 (Задание №2 в варианте):** Обновление записи сотрудника с предварительной проверкой существования через `SELECT` (`SQLiteCompanyRepository.update_employee`).
- **Средняя 7 (Задание №3 в варианте):** Создание нескольких таблиц (`departments` и `employees`) со связью `FOREIGN KEY ... ON DELETE CASCADE` и включённым режимом `PRAGMA foreign_keys = ON` (`SQLiteCompanyRepository.create_tables`).
- **Повышенная 2 (Задание №4 в варианте):** Полный цикл операций CRUD (`Create`, `Read`, `Update`, `Delete`) через `SQLAlchemy ORM` для моделей `ProjectORM` и `ProjectTaskORM` (`SQLAlchemyCrudRepository`).
- **Повышенная 6 (Задание №5 в варианте):** Работа с `PostgreSQL` через `psycopg2` с использованием параметризованных запросов `%s`, конструкции `RETURNING` и управления транзакциями `commit`/`rollback` (`PostgresAccountRepository`).
## Структура проекта
- `sqlite_repo.py` — работа с `sqlite3`: создание таблиц, вставка, обновление, выборка с `JOIN` и валидация данных.
- `orm_crud.py` — декларативные модели `SQLAlchemy ORM` и репозиторий с поддержкой всех операций CRUD.
- `pg_repo.py` — репозиторий для работы с `PostgreSQL` через драйвер `psycopg2`.
- `tests.py` — модульные автотесты на базе `unittest.TestCase`.
- `main.py` — точка входа с поддержкой CLI-параметров (`--test`, `--pg-dsn`).
- `requirements.txt` — зависимости проекта (`sqlalchemy`, `psycopg2-binary`).
- `.gitignore` — правила игнорирования служебных файлов Python и локальных файлов БД.
- `README.md` — документация проекта и инструкции по запуску.
## Установка и запуск проекта
Установка зависимостей:
```bash
pip install -r requirements.txt
```
Запуск полного цикла (автотесты + демонстрация всех 5 заданий):
```bash
python main.py
```
Запуск только модульных тестов (`unittest`):
```bash
python main.py --test
```
Запуск с явным указанием DSN живого сервера PostgreSQL:
```bash
python main.py --pg-dsn "postgresql://postgres:postgres@localhost:5432/lab7_db"
```
## Пример вывода в консоли
```text
.......
----------------------------------------------------------------------
Ran 7 tests in 0.085s
OK
[TESTS] Все unittest-проверки лабораторной №7 пройдены!
=== Лабораторная работа №7 (Вариант 2) ===
Таблицы 'departments' и 'employees' инициализированы
Вставлен отдел в SQLite: id=1, name='Отдел проектирования СУБД'
Вставлен сотрудник в SQLite: id=1, name='Нестеров Вадим Сергеевич'
[Средняя 2 и 7] Добавлен сотрудник: EmployeeRecord(id=1, full_name='Нестеров Вадим Сергеевич', position='Архитектор БД', salary=160000.0, department_id=1, department_name='Отдел проектирования СУБД')
Обновлена запись сотрудника id=1: position='Ведущий архитектор БД', salary=195000.00
[Средняя 4] Обновлена запись сотрудника: EmployeeRecord(id=1, full_name='Нестеров Вадим Сергеевич', position='Ведущий архитектор БД', salary=195000.0, department_id=1, department_name='Отдел проектирования СУБД')
[ORM CREATE] Создан проект: id=1, title='Лабораторная №7 ORM'
[ORM CREATE] Создана задача: id=1, project_id=1
[ORM UPDATE] Задача id=1 -> is_completed=True
[ORM UPDATE] Обновлён бюджет проекта id=1 -> 350000.00
[Повышенная 2] Проекты в ORM: [ProjectDTO(id=1, title='Лабораторная №7 ORM', budget=350000.0, task_count=1)] | Задачи: [ProjectTaskDTO(id=1, title='Реализовать CRUD через SQLAlchemy', is_completed=True, project_id=1)]
[ORM DELETE] Удалена задача id=1
[ORM DELETE] Удалён проект id=1
[Повышенная 6] Счёт в PostgreSQL после обновления: PostgresAccountRecord(id=1, owner_name='Нестеров Вадим Сергеевич', email='nesterov.v@university.ru', balance=75500.0)
```
