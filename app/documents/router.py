import shutil
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, get_db
from app.models.document import Document, DocumentStatus
from app.models.project import Project, ProjectMember, ProjectRole
from app.projects.dependencies import require_project_member
from app.rag.ingestion import SUPPORTED_EXTENSIONS, ingest_document
from app.rag.qdrant_store import delete_document_vectors
from app.schemas.document import DocumentResponse

router = APIRouter(tags=["documents"])
settings = get_settings()


def _run_ingestion(document_id: UUID) -> None:
    db = SessionLocal()
    try:
        ingest_document(db, document_id)
    finally:
        db.close()


@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    project_membership: Annotated[
        tuple[Project, ProjectMember], Depends(require_project_member(ProjectRole.member))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> Document:
    project, membership = project_membership
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    document = Document(
        project_id=project.id,
        filename=file.filename,
        storage_path="",
        status=DocumentStatus.pending,
        uploaded_by=membership.user_id,
    )
    db.add(document)
    db.flush()

    upload_dir = Path(settings.upload_dir) / str(project.id) / str(document.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    storage_path = upload_dir / file.filename

    content = await file.read()
    storage_path.write_bytes(content)

    document.storage_path = str(storage_path)
    db.commit()
    db.refresh(document)

    background_tasks.add_task(_run_ingestion, document.id)
    return document


@router.get("/projects/{project_id}/documents", response_model=list[DocumentResponse])
def list_documents(
    project_membership: Annotated[tuple[Project, ProjectMember], Depends(require_project_member())],
    db: Annotated[Session, Depends(get_db)],
) -> list[Document]:
    project, _ = project_membership
    return (
        db.query(Document)
        .filter(Document.project_id == project.id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.delete("/projects/{project_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    project_id: UUID,
    document_id: UUID,
    project_membership: Annotated[tuple[Project, ProjectMember], Depends(require_project_member(ProjectRole.admin))],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    project, _ = project_membership
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.project_id == project.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    delete_document_vectors(str(document.id))

    storage_path = Path(document.storage_path)
    if storage_path.exists():
        if storage_path.is_file():
            storage_path.unlink()
        else:
            shutil.rmtree(storage_path.parent, ignore_errors=True)
    elif storage_path.parent.exists():
        shutil.rmtree(storage_path.parent, ignore_errors=True)

    db.delete(document)
    db.commit()
