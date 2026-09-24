import secrets
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.organization import OrganizationRole


def generate_invite_code() -> str:
    return secrets.token_urlsafe(24)


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    invite_code: str | None = None
    created_by: uuid.UUID
    created_at: datetime
    current_user_role: OrganizationRole

    model_config = {"from_attributes": True}


class OrganizationMemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    role: OrganizationRole
    created_at: datetime


class OrganizationMemberRoleUpdate(BaseModel):
    role: OrganizationRole
