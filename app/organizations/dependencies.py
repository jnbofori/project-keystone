from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.database import get_db
from app.models.organization import (
    ORG_ROLE_RANK,
    Organization,
    OrganizationMember,
    OrganizationRole,
)
from app.models.user import User


def get_user_org_membership(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> tuple[Organization, OrganizationMember]:
    membership = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not belong to an organization",
        )
    organization = db.get(Organization, membership.organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not belong to an organization",
        )
    return organization, membership


def require_org_member(min_role: OrganizationRole = OrganizationRole.member):
    def dependency(
        org_bundle: Annotated[
            tuple[Organization, OrganizationMember],
            Depends(get_user_org_membership),
        ],
    ) -> tuple[Organization, OrganizationMember]:
        organization, membership = org_bundle
        if ORG_ROLE_RANK[membership.role] < ORG_ROLE_RANK[min_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient organization permissions",
            )
        return organization, membership

    return dependency
