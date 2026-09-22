import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    status: DocumentStatus
    uploaded_by: uuid.UUID
    chunk_count: int
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
