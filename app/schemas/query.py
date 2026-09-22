import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class QueryCreate(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class SourceCitation(BaseModel):
    document_id: str | None = None
    filename: str | None = None
    text: str
    score: float | None = None


class QueryResponse(BaseModel):
    id: uuid.UUID
    question: str
    answer: str
    sources: list[SourceCitation]
    created_at: datetime

    model_config = {"from_attributes": True}
