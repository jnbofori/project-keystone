from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.enums import (
    EpicStatus,
    ProjectEventType,
    SprintStatus,
    StoryStatus,
    TaskPriority,
    TaskStatus,
)

_PRIORITY_MAP = {
    "highest": TaskPriority.highest,
    "high": TaskPriority.high,
    "medium": TaskPriority.medium,
    "low": TaskPriority.low,
    "lowest": TaskPriority.lowest,
}


def adf_to_text(value: Any) -> str | None:
    """Best-effort plain text from Atlassian Document Format or a plain string."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return str(value)

    parts: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "text" and isinstance(node.get("text"), str):
                parts.append(node["text"])
            for child in node.get("content") or []:
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    text = "\n".join(p for p in parts if p).strip()
    return text or None


def map_task_priority(priority: dict[str, Any] | None) -> TaskPriority:
    if not priority:
        return TaskPriority.medium
    name = (priority.get("name") or "").strip().lower()
    return _PRIORITY_MAP.get(name, TaskPriority.medium)


def map_task_status(status: dict[str, Any] | None) -> TaskStatus:
    if not status:
        return TaskStatus.backlog
    name = (status.get("name") or "").strip().lower().replace(" ", "_")
    category = ((status.get("statusCategory") or {}).get("key") or "").strip().lower()

    aliases = {
        "backlog": TaskStatus.backlog,
        "to_do": TaskStatus.todo,
        "todo": TaskStatus.todo,
        "open": TaskStatus.todo,
        "in_progress": TaskStatus.in_progress,
        "inprogress": TaskStatus.in_progress,
        "blocked": TaskStatus.blocked,
        "in_review": TaskStatus.in_review,
        "review": TaskStatus.in_review,
        "done": TaskStatus.done,
        "closed": TaskStatus.done,
        "resolved": TaskStatus.done,
        "cancelled": TaskStatus.cancelled,
        "canceled": TaskStatus.cancelled,
    }
    if name in aliases:
        return aliases[name]
    if category == "done":
        return TaskStatus.done
    if category == "indeterminate":
        return TaskStatus.in_progress
    if category == "new":
        return TaskStatus.todo
    return TaskStatus.backlog


def map_epic_or_story_status(status: dict[str, Any] | None) -> EpicStatus:
    task_status = map_task_status(status)
    if task_status in (TaskStatus.done,):
        return EpicStatus.done
    if task_status == TaskStatus.cancelled:
        return EpicStatus.cancelled
    if task_status in (TaskStatus.in_progress, TaskStatus.blocked, TaskStatus.in_review):
        return EpicStatus.in_progress
    return EpicStatus.todo


def map_story_status(status: dict[str, Any] | None) -> StoryStatus:
    epic_status = map_epic_or_story_status(status)
    return StoryStatus(epic_status.value)


def map_sprint_status(state: str | None) -> SprintStatus:
    value = (state or "").strip().lower()
    if value == "active":
        return SprintStatus.active
    if value in ("closed", "complete", "completed"):
        return SprintStatus.completed
    return SprintStatus.planned


def parse_jira_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    # Jira sometimes uses +0000 without colon
    if len(text) >= 5 and (text[-5] in "+-") and text[-3] != ":":
        text = text[:-2] + ":" + text[-2:]
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def issue_type_name(issue: dict[str, Any]) -> str:
    fields = issue.get("fields") or {}
    issuetype = fields.get("issuetype") or {}
    return (issuetype.get("name") or "").strip()


def classify_issue(issue: dict[str, Any]) -> str:
    """Return 'epic' | 'story' | 'task'."""
    name = issue_type_name(issue).lower()
    if name == "epic":
        return "epic"
    if name in ("story", "user story"):
        return "story"
    hierarchy = ((issue.get("fields") or {}).get("issuetype") or {}).get("hierarchyLevel")
    if hierarchy == 1:
        return "epic"
    if hierarchy == 0 and name in ("story", "user story"):
        return "story"
    return "task"


def _value_has_impediment(value: Any) -> bool:
    if value is None:
        return False
    candidates = value if isinstance(value, list) else [value]
    for item in candidates:
        if isinstance(item, dict):
            label = (item.get("value") or item.get("name") or "").strip().lower()
            if label == "impediment":
                return True
        elif isinstance(item, str) and item.strip().lower() == "impediment":
            return True
    return False


def is_flagged_impediment(fields: dict[str, Any], flagged_field: str | None = None) -> bool:
    """True when Jira Flagged field contains Impediment."""
    if flagged_field:
        return _value_has_impediment(fields.get(flagged_field))
    for key, value in fields.items():
        if not key.startswith("customfield_"):
            continue
        if _value_has_impediment(value):
            return True
    return False


def extract_sprint_ids(fields: dict[str, Any]) -> list[str]:
    """Collect sprint ids from common sprint field shapes."""
    ids: list[str] = []
    for key, value in fields.items():
        if not key.startswith("customfield_") and key != "sprint":
            continue
        candidates = value if isinstance(value, list) else [value]
        for item in candidates:
            if isinstance(item, dict) and item.get("id") is not None:
                # Agile sprint objects
                if "state" in item or "boardId" in item or "name" in item:
                    ids.append(str(item["id"]))
            elif isinstance(item, str) and "id=" in item:
                # Legacy stringified sprint
                for part in item.split(","):
                    part = part.strip()
                    if part.startswith("id="):
                        ids.append(part.split("=", 1)[1])
    # Prefer last (active/current) sprint when multiple
    return ids


def extract_epic_key(fields: dict[str, Any]) -> str | None:
    parent = fields.get("parent") or {}
    parent_type = ((parent.get("fields") or {}).get("issuetype") or {}).get("name") or ""
    if parent.get("key") and parent_type.lower() == "epic":
        return parent["key"]

    for key in ("epic", "epicKey"):
        value = fields.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, dict) and value.get("key"):
            return value["key"]

    for key, value in fields.items():
        if not key.startswith("customfield_"):
            continue
        if isinstance(value, str) and value.count("-") == 1 and value.split("-", 1)[0].isalpha():
            # Likely an epic link key like PROJ-1
            if value.upper() == value or value[0].isalpha():
                # Heuristic only — prefer known epic object shapes
                pass
        if isinstance(value, dict) and value.get("key") and (
            (value.get("type") or "").lower() == "epic"
            or (value.get("name") and "epic" in str(value.get("name")).lower())
        ):
            return value["key"]
        # Classic Epic Link is often a bare issue key string on a custom field
        if isinstance(value, str) and "-" in value and len(value) < 32:
            left, _, right = value.partition("-")
            if left.isalpha() and right.isdigit():
                # Could be epic link; caller may validate against known epics
                return value
    return None


def extract_parent_key(fields: dict[str, Any]) -> str | None:
    parent = fields.get("parent") or {}
    key = parent.get("key")
    return key if isinstance(key, str) else None


def map_changelog_item(
    field: str,
    from_string: str | None,
    to_string: str | None,
) -> ProjectEventType | None:
    field_l = field.strip().lower()
    if field_l == "status":
        to_l = (to_string or "").strip().lower()
        if to_l in ("done", "closed", "resolved"):
            return ProjectEventType.TaskCompleted
        if to_l in ("to do", "todo", "open", "reopened") and (from_string or "").strip().lower() in (
            "done",
            "closed",
            "resolved",
        ):
            return ProjectEventType.TaskReopened
        return ProjectEventType.TaskMoved
    if field_l in ("assignee",):
        return ProjectEventType.AssigneeChanged
    if field_l in ("story points", "story point estimate"):
        return ProjectEventType.StoryPointsChanged
    if field_l in ("duedate", "due date"):
        return ProjectEventType.DeadlineChanged
    if field_l in ("sprint",):
        return ProjectEventType.ScopeChanged
    return None
