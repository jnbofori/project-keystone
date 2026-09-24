from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.organization import (
    Organization,
    OrganizationMember,
    OrganizationRole,
)
from app.models.user import User
from app.organizations.dependencies import get_user_org_membership, require_org_member
from app.schemas.organization import (
    OrganizationMemberResponse,
    OrganizationMemberRoleUpdate,
    OrganizationResponse,
    generate_invite_code,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _to_org_response(
    organization: Organization,
    membership: OrganizationMember,
    *,
    include_invite_code: bool,
) -> OrganizationResponse:
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        invite_code=organization.invite_code if include_invite_code else None,
        created_by=organization.created_by,
        created_at=organization.created_at,
        current_user_role=membership.role,
    )


@router.get("/me", response_model=OrganizationResponse)
def get_my_organization(
    org_bundle: Annotated[
        tuple[Organization, OrganizationMember],
        Depends(get_user_org_membership),
    ],
) -> OrganizationResponse:
    organization, membership = org_bundle
    show_code = membership.role in (OrganizationRole.owner, OrganizationRole.admin)
    return _to_org_response(organization, membership, include_invite_code=show_code)


@router.get("/me/members", response_model=list[OrganizationMemberResponse])
def list_org_members(
    org_bundle: Annotated[
        tuple[Organization, OrganizationMember],
        Depends(get_user_org_membership),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> list[OrganizationMemberResponse]:
    organization, _ = org_bundle
    rows = (
        db.query(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .filter(OrganizationMember.organization_id == organization.id)
        .order_by(OrganizationMember.created_at.asc())
        .all()
    )
    return [
        OrganizationMemberResponse(
            id=member.id,
            user_id=member.user_id,
            email=user.email,
            role=member.role,
            created_at=member.created_at,
        )
        for member, user in rows
    ]


@router.post("/me/invite-code/rotate", response_model=OrganizationResponse)
def rotate_invite_code(
    org_bundle: Annotated[
        tuple[Organization, OrganizationMember],
        Depends(require_org_member(OrganizationRole.admin)),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> OrganizationResponse:
    organization, membership = org_bundle
    organization.invite_code = generate_invite_code()
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return _to_org_response(organization, membership, include_invite_code=True)


@router.patch("/me/members/{user_id}", response_model=OrganizationMemberResponse)
def update_org_member_role(
    user_id: UUID,
    payload: OrganizationMemberRoleUpdate,
    org_bundle: Annotated[
        tuple[Organization, OrganizationMember],
        Depends(require_org_member(OrganizationRole.admin)),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> OrganizationMemberResponse:
    organization, actor = org_bundle

    target = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization.id,
            OrganizationMember.user_id == user_id,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization member not found")

    if target.role == OrganizationRole.owner and payload.role != OrganizationRole.owner:
        owner_count = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization.id,
                OrganizationMember.role == OrganizationRole.owner,
            )
            .count()
        )
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last organization owner",
            )

    if payload.role == OrganizationRole.owner and actor.role != OrganizationRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an organization owner can promote another owner",
        )

    target.role = payload.role
    db.add(target)
    db.commit()
    db.refresh(target)

    user = db.get(User, target.user_id)
    return OrganizationMemberResponse(
        id=target.id,
        user_id=target.user_id,
        email=user.email if user else "",
        role=target.role,
        created_at=target.created_at,
    )
