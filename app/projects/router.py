from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.database import get_db
from app.models.organization import OrganizationMember
from app.models.project import Project, ProjectMember, ProjectRole
from app.models.user import User
from app.organizations.dependencies import get_user_org_membership
from app.projects.dependencies import require_project_member
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectResponse,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_project_response(project: Project, membership: ProjectMember) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        jira_project_key=project.jira_project_key,
        jira_project_id=project.jira_project_id,
        created_by=project.created_by,
        created_at=project.created_at,
        current_user_role=membership.role,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    org_bundle: Annotated[tuple, Depends(get_user_org_membership)],
) -> ProjectResponse:
    organization, _ = org_bundle
    project = Project(
        name=payload.name,
        description=payload.description,
        created_by=current_user.id,
        organization_id=organization.id,
    )
    db.add(project)
    db.flush()

    membership = ProjectMember(user_id=current_user.id, project_id=project.id, role=ProjectRole.owner)
    db.add(membership)
    db.commit()
    db.refresh(project)
    db.refresh(membership)
    return _to_project_response(project, membership)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ProjectResponse]:
    rows = (
        db.query(Project, ProjectMember)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .filter(ProjectMember.user_id == current_user.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return [_to_project_response(project, membership) for project, membership in rows]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_membership: Annotated[tuple[Project, ProjectMember], Depends(require_project_member())],
) -> ProjectResponse:
    project, membership = project_membership
    return _to_project_response(project, membership)


@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
def list_members(
    project_membership: Annotated[tuple[Project, ProjectMember], Depends(require_project_member())],
    db: Annotated[Session, Depends(get_db)],
) -> list[ProjectMemberResponse]:
    project, _ = project_membership
    members = (
        db.query(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .filter(ProjectMember.project_id == project.id)
        .order_by(ProjectMember.created_at.asc())
        .all()
    )
    return [
        ProjectMemberResponse(
            id=member.id,
            user_id=member.user_id,
            email=user.email,
            role=member.role,
            created_at=member.created_at,
        )
        for member, user in members
    ]


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    project_id: UUID,
    payload: ProjectMemberCreate,
    project_membership: Annotated[tuple[Project, ProjectMember], Depends(require_project_member(ProjectRole.admin))],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectMemberResponse:
    project, _membership = project_membership

    if payload.role == ProjectRole.owner:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot assign owner role")

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    org_member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user.id,
            OrganizationMember.organization_id == project.organization_id,
        )
        .first()
    )
    if not org_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of this organization",
        )

    existing = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a member")

    member = ProjectMember(user_id=user.id, project_id=project.id, role=payload.role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return ProjectMemberResponse(
        id=member.id,
        user_id=member.user_id,
        email=user.email,
        role=member.role,
        created_at=member.created_at,
    )


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    project_id: UUID,
    user_id: UUID,
    project_membership: Annotated[tuple[Project, ProjectMember], Depends(require_project_member(ProjectRole.admin))],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    project, membership = project_membership
    target = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if target.role == ProjectRole.owner:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove project owner")

    if membership.role == ProjectRole.admin and target.role == ProjectRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins cannot remove other admins")

    db.delete(target)
    db.commit()
