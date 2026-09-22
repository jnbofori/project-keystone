import logging
import uuid
from pathlib import Path
from uuid import UUID

from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.document import Document, DocumentStatus
from app.rag.qdrant_store import get_qdrant_client

logger = logging.getLogger(__name__)
settings = get_settings()

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


def _iter_block_items(parent):
    from docx.document import Document as DocxDocumentType
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    if isinstance(parent, DocxDocumentType):
        parent_elm = parent.element.body
    else:
        parent_elm = parent._tc

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _table_to_text(table) -> str:
    rows = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            cell_parts = []
            for block in _iter_block_items(cell):
                if hasattr(block, "rows"):
                    nested = _table_to_text(block)
                    if nested:
                        cell_parts.append(nested)
                elif block.text.strip():
                    cell_parts.append(block.text.strip())
            cell_text = " ".join(cell_parts).strip()
            if cell_text:
                cells.append(cell_text)
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _load_docx(file_path: Path) -> str:
    from docx import Document as DocxDocument
    from docx.table import Table

    doc = DocxDocument(str(file_path))
    parts = []
    for block in _iter_block_items(doc):
        if isinstance(block, Table):
            text = _table_to_text(block)
        elif block.text.strip():
            text = block.text.strip()
        else:
            text = ""
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def _format_pdf_table(table: list[list]) -> str:
    rows = []
    for row in table:
        cells = [str(cell).strip() if cell is not None else "" for cell in row]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _load_pdf(file_path: Path) -> str:
    import pdfplumber

    parts = []
    with pdfplumber.open(str(file_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                parts.append(text.strip())

            for table in page.extract_tables() or []:
                print("table", table)
                table_text = _format_pdf_table(table)
                if table_text:
                    parts.append(table_text)

    print("parts", parts)

    return "\n\n".join(parts)


def _load_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        return _load_pdf(file_path)

    if suffix == ".docx":
        return _load_docx(file_path)

    raise ValueError(f"Unsupported file type: {suffix}")


def ingest_document(db: Session, document_id: UUID) -> None:
    document = db.get(Document, document_id)
    if not document:
        logger.error("Document %s not found for ingestion", document_id)
        return

    document.status = DocumentStatus.processing
    document.error_message = None
    db.commit()

    try:
        file_path = Path(document.storage_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {suffix}")

        text = _load_text(file_path)
        if not text.strip():
            raise ValueError("Document contains no extractable text")

        llama_doc = LlamaDocument(
            id_=str(document.id),
            text=text,
            metadata={
                "project_id": str(document.project_id),
                "document_id": str(document.id),
                "filename": document.filename,
            },
        )

        splitter = SentenceSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
        nodes = splitter.get_nodes_from_documents([llama_doc])

        embed_model = OpenAIEmbedding(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )

        vector_store = QdrantVectorStore(
            client=get_qdrant_client(),
            collection_name=settings.qdrant_collection,
        )

        for index, node in enumerate(nodes):
            if isinstance(node, TextNode):
                # Qdrant only accepts unsigned integers or valid UUIDs as point IDs.
                node.id_ = str(uuid.uuid5(document.id, str(index)))
                node.embedding = embed_model.get_text_embedding(node.get_content())

        vector_store.add(nodes)

        document.status = DocumentStatus.ready
        document.chunk_count = len(nodes)
        document.error_message = None
        db.commit()
        logger.info("Ingested document %s with %d chunks", document_id, len(nodes))

    except Exception as exc:
        logger.exception("Failed to ingest document %s", document_id)
        document.status = DocumentStatus.failed
        document.error_message = str(exc)
        db.commit()
