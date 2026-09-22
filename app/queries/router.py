from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.project import Project, ProjectMember, ProjectRole
from app.models.query_log import QueryLog
from app.projects.dependencies import require_project_member
from app.rag.query import ask_project_question
from app.schemas.query import QueryCreate, QueryResponse, SourceCitation

router = APIRouter(tags=["queries"])


@router.post("/projects/{project_id}/queries", response_model=QueryResponse)
def ask_question(
    payload: QueryCreate,
    project_membership: Annotated[tuple[Project, ProjectMember], Depends(require_project_member())],
    db: Annotated[Session, Depends(get_db)],
) -> QueryResponse:
    project, membership = project_membership

    ready_count = (
        db.query(Document)
        .filter(Document.project_id == project.id, Document.status == DocumentStatus.ready)
        .count()
    )
    if ready_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No processed documents available for this project",
        )

    answer, sources = ask_project_question(project.id, payload.question)

    query_log = QueryLog(
        project_id=project.id,
        user_id=membership.user_id,
        question=payload.question,
        answer=answer,
        sources=sources,
    )
    db.add(query_log)
    db.commit()
    db.refresh(query_log)

    return QueryResponse(
        id=query_log.id,
        question=query_log.question,
        answer=query_log.answer,
        sources=[SourceCitation(**s) for s in (query_log.sources or [])],
        created_at=query_log.created_at,
    )


@router.get("/projects/{project_id}/queries", response_model=list[QueryResponse])
def list_queries(
    project_membership: Annotated[tuple[Project, ProjectMember], Depends(require_project_member(ProjectRole.member))],
    db: Annotated[Session, Depends(get_db)],
) -> list[QueryResponse]:
    project, _ = project_membership
    logs = (
        db.query(QueryLog)
        .filter(QueryLog.project_id == project.id)
        .order_by(QueryLog.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        QueryResponse(
            id=log.id,
            question=log.question,
            answer=log.answer,
            sources=[SourceCitation(**s) for s in (log.sources or [])],
            created_at=log.created_at,
        )
        for log in logs
    ]
