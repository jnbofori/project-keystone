import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    organization_name: str | None = Field(default=None, max_length=255)
    invite_code: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def exactly_one_org_path(self) -> "UserRegister":
        name = (self.organization_name or "").strip() or None
        code = (self.invite_code or "").strip() or None
        if bool(name) == bool(code):
            raise ValueError("Provide exactly one of organization_name or invite_code")
        self.organization_name = name
        self.invite_code = code
        return self


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}
