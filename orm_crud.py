"""Модуль реализации CRUD-операций через SQLAlchemy ORM (Повышенная 2)."""

from dataclasses import dataclass
import logging

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, select
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.orm import relationship, sessionmaker

from sqlite_repo import (
    validate_non_empty_str,
    validate_positive_float,
    validate_positive_int,
)

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Базовый декларативный класс моделей SQLAlchemy."""


class ProjectORM(Base):
    """ORM-модель проекта (таблица projects)."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    title: Mapped[str] = mapped_column(
        String(120), nullable=False, unique=True
    )
    budget: Mapped[float] = mapped_column(Float, nullable=False)

    tasks: Mapped[list["ProjectTaskORM"]] = relationship(
        "ProjectTaskORM",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectTaskORM(Base):
    """ORM-модель задачи внутри проекта (таблица project_tasks)."""

    __tablename__ = "project_tasks"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    is_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    project: Mapped[ProjectORM] = relationship(
        "ProjectORM",
        back_populates="tasks",
    )


@dataclass(frozen=True)
class ProjectDTO:
    """DTO-представление проекта для безопасной передачи вне сессии ORM."""

    id: int
    title: str
    budget: float
    task_count: int


@dataclass(frozen=True)
class ProjectTaskDTO:
    """DTO-представление задачи проекта."""

    id: int
    title: str
    is_completed: bool
    project_id: int


class SQLAlchemyCrudRepository:
    """Повышенная 2: Полный набор операций CRUD через SQLAlchemy ORM."""

    def __init__(self, db_url: str = "sqlite:///orm_projects.db") -> None:
        clean_url = validate_non_empty_str(db_url, "db_url")
        self.engine = create_engine(clean_url, future=True)
        Base.metadata.create_all(self.engine)
        self._session_factory = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )

    def dispose(self) -> None:
        """Закрывает пул соединений движка SQLAlchemy."""
        self.engine.dispose()

    def create_project(
        self,
        title: str,
        budget: float | int,
    ) -> ProjectDTO:
        """CREATE: Создаёт новый проект через сессию SQLAlchemy ORM."""
        clean_title = validate_non_empty_str(title, "title")
        valid_budget = validate_positive_float(budget, "budget")

        with self._session_factory() as session:
            project = ProjectORM(title=clean_title, budget=valid_budget)
            session.add(project)
            session.commit()
            session.refresh(project)
            dto = ProjectDTO(
                id=project.id,
                title=project.title,
                budget=project.budget,
                task_count=0,
            )

        logger.info(
            "[ORM CREATE] Создан проект: id=%d, title='%s'",
            dto.id,
            dto.title,
        )
        return dto

    def create_task(
        self,
        project_id: int,
        title: str,
        is_completed: bool = False,
    ) -> ProjectTaskDTO:
        """CREATE: Создаёт задачу, привязанную к проекту через ORM."""
        valid_proj_id = validate_positive_int(project_id, "project_id")
        clean_title = validate_non_empty_str(title, "title")
        if not isinstance(is_completed, bool):
            raise TypeError("Поле 'is_completed' должно быть типа bool")

        with self._session_factory() as session:
            project = session.get(ProjectORM, valid_proj_id)
            if project is None:
                raise ValueError(f"Проект с id={valid_proj_id} не найден")

            task = ProjectTaskORM(
                title=clean_title,
                is_completed=is_completed,
                project_id=valid_proj_id,
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            dto = ProjectTaskDTO(
                id=task.id,
                title=task.title,
                is_completed=task.is_completed,
                project_id=task.project_id,
            )

        logger.info(
            "[ORM CREATE] Создана задача: id=%d, project_id=%d",
            dto.id,
            dto.project_id,
        )
        return dto

    def get_project(self, project_id: int) -> ProjectDTO | None:
        """READ: Получает проект по первичному ключу через ORM."""
        valid_id = validate_positive_int(project_id, "project_id")
        with self._session_factory() as session:
            project = session.get(ProjectORM, valid_id)
            if project is None:
                return None
            return self._to_project_dto(session, project)

    def list_projects(self) -> list[ProjectDTO]:
        """READ: Возвращает список всех проектов через ORM select()."""
        with self._session_factory() as session:
            stmt = select(ProjectORM).order_by(ProjectORM.id.asc())
            projects = list(session.scalars(stmt).all())
            return [self._to_project_dto(session, proj) for proj in projects]

    def list_tasks(
        self,
        project_id: int | None = None,
    ) -> list[ProjectTaskDTO]:
        """READ: Возвращает список задач (всех или по конкретному проекту)."""
        with self._session_factory() as session:
            stmt = select(ProjectTaskORM).order_by(ProjectTaskORM.id.asc())
            if project_id is not None:
                valid_proj_id = validate_positive_int(
                    project_id, "project_id"
                )
                stmt = stmt.where(ProjectTaskORM.project_id == valid_proj_id)
            tasks = list(session.scalars(stmt).all())
            return [
                ProjectTaskDTO(
                    id=t.id,
                    title=t.title,
                    is_completed=t.is_completed,
                    project_id=t.project_id,
                )
                for t in tasks
            ]

    def update_project_budget(
        self,
        project_id: int,
        new_budget: float | int,
    ) -> ProjectDTO | None:
        """UPDATE: Обновляет бюджет проекта через ORM-модель."""
        valid_id = validate_positive_int(project_id, "project_id")
        valid_budget = validate_positive_float(new_budget, "new_budget")

        with self._session_factory() as session:
            project = session.get(ProjectORM, valid_id)
            if project is None:
                return None
            project.budget = valid_budget
            session.commit()
            session.refresh(project)
            dto = self._to_project_dto(session, project)

        logger.info(
            "[ORM UPDATE] Обновлён бюджет проекта id=%d -> %.2f",
            valid_id,
            valid_budget,
        )
        return dto

    def update_task_status(
        self,
        task_id: int,
        is_completed: bool,
    ) -> ProjectTaskDTO | None:
        """UPDATE: Обновляет статус выполнения задачи через ORM."""
        valid_id = validate_positive_int(task_id, "task_id")
        if not isinstance(is_completed, bool):
            raise TypeError("Поле 'is_completed' должно быть типа bool")

        with self._session_factory() as session:
            task = session.get(ProjectTaskORM, valid_id)
            if task is None:
                return None
            task.is_completed = is_completed
            session.commit()
            session.refresh(task)
            dto = ProjectTaskDTO(
                id=task.id,
                title=task.title,
                is_completed=task.is_completed,
                project_id=task.project_id,
            )

        logger.info(
            "[ORM UPDATE] Задача id=%d -> is_completed=%s",
            valid_id,
            is_completed,
        )
        return dto

    def delete_project(self, project_id: int) -> bool:
        """DELETE: Удаляет проект (и каскадно его задачи) через ORM."""
        valid_id = validate_positive_int(project_id, "project_id")
        with self._session_factory() as session:
            project = session.get(ProjectORM, valid_id)
            if project is None:
                return False
            session.delete(project)
            session.commit()

        logger.info("[ORM DELETE] Удалён проект id=%d", valid_id)
        return True

    def delete_task(self, task_id: int) -> bool:
        """DELETE: Удаляет отдельную задачу по ID через ORM."""
        valid_id = validate_positive_int(task_id, "task_id")
        with self._session_factory() as session:
            task = session.get(ProjectTaskORM, valid_id)
            if task is None:
                return False
            session.delete(task)
            session.commit()

        logger.info("[ORM DELETE] Удалена задача id=%d", valid_id)
        return True

    @staticmethod
    def _to_project_dto(
        session: Session,
        project: ProjectORM,
    ) -> ProjectDTO:
        stmt = select(ProjectTaskORM).where(
            ProjectTaskORM.project_id == project.id
        )
        count = len(list(session.scalars(stmt).all()))
        return ProjectDTO(
            id=project.id,
            title=project.title,
            budget=project.budget,
            task_count=count,
        )
