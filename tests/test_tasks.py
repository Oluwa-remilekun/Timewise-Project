from datetime import date

import pytest

from timewise.errors import ValidationError
from timewise.repositories import tasks

TODAY = date(2026, 11, 14)
TOMORROW = date(2026, 11, 15)


def test_add_task_starts_incomplete(user):
    task = tasks.add_task(user.id, " Lab report ", "School", TODAY, " due at noon ")
    assert task.title == "Lab report"
    assert task.description == "due at noon"
    assert task.is_completed is False
    assert tasks.list_tasks(user.id) == [task]


def test_list_tasks_orders_open_first_then_by_due_date(user):
    later = tasks.add_task(user.id, "Later", "Work", TOMORROW)
    sooner = tasks.add_task(user.id, "Sooner", "Work", TODAY)
    finished = tasks.add_task(user.id, "Finished", "Life", TODAY)
    tasks.set_task_completion(user.id, finished.id, True)

    titles = [task.title for task in tasks.list_tasks(user.id)]

    assert titles == [sooner.title, later.title, finished.title]


def test_list_tasks_due_on_filters_by_date(user):
    tasks.add_task(user.id, "Today", "School", TODAY)
    tasks.add_task(user.id, "Tomorrow", "School", TOMORROW)
    assert [task.title for task in tasks.list_tasks_due_on(user.id, TODAY)] == ["Today"]


def test_completion_can_be_toggled_and_persists(user):
    task = tasks.add_task(user.id, "Laundry", "Life", TODAY)

    tasks.set_task_completion(user.id, task.id, True)
    assert tasks.list_tasks(user.id)[0].is_completed is True

    tasks.set_task_completion(user.id, task.id, False)
    assert tasks.list_tasks(user.id)[0].is_completed is False


def test_other_users_cannot_change_or_delete_a_task(user):
    task = tasks.add_task(user.id, "Laundry", "Life", TODAY)

    tasks.set_task_completion("someone-else", task.id, True)
    tasks.delete_task("someone-else", task.id)

    assert tasks.list_tasks(user.id) == [task]


def test_delete_task(user):
    task = tasks.add_task(user.id, "Laundry", "Life", TODAY)
    tasks.delete_task(user.id, task.id)
    assert tasks.list_tasks(user.id) == []


@pytest.mark.parametrize(("title", "category"), [("", "School"), ("Essay", "Chores")])
def test_add_task_rejects_invalid_input(user, title, category):
    with pytest.raises(ValidationError):
        tasks.add_task(user.id, title, category, TODAY)
