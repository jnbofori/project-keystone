from __future__ import annotations

import enum


class IntegrationSource(str, enum.Enum):
    jira = "jira"
    github = "github"
    slack = "slack"
    ci = "ci"
    manual = "manual"
    system = "system"


class SprintStatus(str, enum.Enum):
    planned = "planned"
    active = "active"
    completed = "completed"


class EpicStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"
    cancelled = "cancelled"


class StoryStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"
    cancelled = "cancelled"


class TaskStatus(str, enum.Enum):
    backlog = "backlog"
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    in_review = "in_review"
    done = "done"
    cancelled = "cancelled"


class TaskPriority(str, enum.Enum):
    lowest = "lowest"
    low = "low"
    medium = "medium"
    high = "high"
    highest = "highest"


class PullRequestStatus(str, enum.Enum):
    open = "open"
    merged = "merged"
    closed = "closed"


class RiskSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RiskStatus(str, enum.Enum):
    open = "open"
    mitigating = "mitigating"
    resolved = "resolved"
    accepted = "accepted"


class ProjectEventType(str, enum.Enum):
    TaskCreated = "TaskCreated"
    TaskMoved = "TaskMoved"
    TaskCompleted = "TaskCompleted"
    TaskReopened = "TaskReopened"
    StoryPointsChanged = "StoryPointsChanged"
    DeadlineChanged = "DeadlineChanged"
    AssigneeChanged = "AssigneeChanged"
    DependencyAdded = "DependencyAdded"
    SprintStarted = "SprintStarted"
    SprintCompleted = "SprintCompleted"
    EpicCreated = "EpicCreated"
    StoryCreated = "StoryCreated"
    PullRequestOpened = "PullRequestOpened"
    PullRequestMerged = "PullRequestMerged"
    PullRequestClosed = "PullRequestClosed"
    BuildFailed = "BuildFailed"
    BuildSucceeded = "BuildSucceeded"
    CommitPushed = "CommitPushed"
    RequirementAdded = "RequirementAdded"
    ScopeChanged = "ScopeChanged"
    SlackRiskMentioned = "SlackRiskMentioned"
    RiskOpened = "RiskOpened"
    RiskResolved = "RiskResolved"
    DiscussionPosted = "DiscussionPosted"


class EntityType(str, enum.Enum):
    task = "task"
    sprint = "sprint"
    epic = "epic"
    story = "story"
    pull_request = "pull_request"
    commit = "commit"
    discussion = "discussion"
    risk = "risk"
    team_member = "team_member"
    project = "project"
