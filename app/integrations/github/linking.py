from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Protocol

from sqlalchemy.orm import Session

from app.models.commit import Commit
from app.models.github_branch import GithubBranch
from app.models.project import Project
from app.models.pull_request import PullRequest
from app.models.story import Story
from app.models.task import Task


class Linkable(Protocol):
    jira_keys: list[str]
    task_id: uuid.UUID | None
    story_id: uuid.UUID | None


class WorkItemIndex:
    """Jira key -> task/story lookup for one project."""

    def __init__(self, db: Session, project: Project, keys: Iterable[str] | None = None):
        task_query = db.query(Task.external_key, Task.id, Task.story_id).filter(
            Task.project_id == project.id, Task.external_key.isnot(None)
        )
        story_query = db.query(Story.external_key, Story.id).filter(
            Story.project_id == project.id, Story.external_key.isnot(None)
        )
        if keys is not None:
            key_list = list(keys)
            task_query = task_query.filter(Task.external_key.in_(key_list))
            story_query = story_query.filter(Story.external_key.in_(key_list))
        self._tasks = {key: (task_id, story_id) for key, task_id, story_id in task_query}
        self._stories = {key: story_id for key, story_id in story_query}

    def resolve(self, keys: list[str]) -> tuple[uuid.UUID | None, uuid.UUID | None]:
        """First key matching a task wins; first key matching a story wins, else the task's parent story."""
        task = next((self._tasks[k] for k in keys if k in self._tasks), None)
        story_id = next((self._stories[k] for k in keys if k in self._stories), None)
        if story_id is None and task is not None:
            story_id = task[1]
        return (task[0] if task else None), story_id


def resolve_work_items(
    db: Session,
    project: Project,
    keys: list[str],
) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    if not keys:
        return None, None
    return WorkItemIndex(db, project, keys).resolve(keys)


def apply_links(db: Session, project: Project, obj: Linkable) -> None:
    obj.task_id, obj.story_id = resolve_work_items(db, project, list(obj.jira_keys or []))


def relink_key(db: Session, project: Project, key: str) -> None:
    """Recompute task/story links for GitHub items in the project that reference one Jira key."""
    db.flush()
    for model in (PullRequest, GithubBranch, Commit):
        for obj in db.query(model).filter(model.project_id == project.id, model.jira_keys.any(key)):
            apply_links(db, project, obj)
    db.flush()


def relink_project(db: Session, project: Project) -> None:
    """Recompute task/story links for every GitHub item in the project from stored jira_keys."""
    index = WorkItemIndex(db, project)
    for model in (PullRequest, GithubBranch, Commit):
        for obj in db.query(model).filter(model.project_id == project.id):
            obj.task_id, obj.story_id = index.resolve(list(obj.jira_keys or []))
    db.flush()
