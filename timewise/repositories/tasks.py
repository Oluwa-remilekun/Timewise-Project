"""To-do task storage."""

from datetime import date

from timewise.clock import utc_now
from timewise.constants import TASK_CATEGORIES
from timewise.database import get_database
from timewise.models import Task
from timewise.repositories import new_id
from timewise.validation import clean_title, require_choice

_COLUMNS = "id, title, description, category, due_date, is_completed"


def add_task(
    user_id: str, title: str, category: str, due_date: date, description: str = ""
) -> Task:
    title = clean_title(title, "Task title")
    require_choice(category, TASK_CATEGORIES, "Category")

    task = Task(new_id(), title, (description or "").strip(), category, due_date, False)
    db = get_database()
    db.execute(
        f"""
        INSERT INTO {db.table("tasks")}
            (id, user_id, title, description, category, due_date, is_completed, created_at)
        VALUES
            (@id, @user_id, @title, @description, @category, @due_date, @is_completed,
             @created_at)
        """,
        {
            "id": task.id,
            "user_id": user_id,
            "title": task.title,
            "description": task.description,
            "category": task.category,
            "due_date": task.due_date,
            "is_completed": task.is_completed,
            "created_at": utc_now(),
        },
    )
    return task


def list_tasks(user_id: str) -> list[Task]:
    db = get_database()
    rows = db.query(
        f"""
        SELECT {_COLUMNS}
        FROM {db.table("tasks")}
        WHERE user_id = @user_id
        ORDER BY is_completed, due_date, title
        """,
        {"user_id": user_id},
    )
    return [Task(**row) for row in rows]


def list_tasks_due_on(user_id: str, due_date: date) -> list[Task]:
    db = get_database()
    rows = db.query(
        f"""
        SELECT {_COLUMNS}
        FROM {db.table("tasks")}
        WHERE user_id = @user_id AND due_date = @due_date
        ORDER BY is_completed, title
        """,
        {"user_id": user_id, "due_date": due_date},
    )
    return [Task(**row) for row in rows]


def set_task_completion(user_id: str, task_id: str, is_completed: bool) -> None:
    db = get_database()
    db.execute(
        f"""
        UPDATE {db.table("tasks")}
        SET is_completed = @is_completed
        WHERE id = @id AND user_id = @user_id
        """,
        {"id": task_id, "user_id": user_id, "is_completed": is_completed},
    )


def delete_task(user_id: str, task_id: str) -> None:
    db = get_database()
    db.execute(
        f"DELETE FROM {db.table('tasks')} WHERE id = @id AND user_id = @user_id",
        {"id": task_id, "user_id": user_id},
    )
