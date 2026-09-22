from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.auth.router import router as auth_router
from app.config import get_settings
from app.database import engine
from app.documents.router import router as documents_router
from app.integrations.jira.router import router as jira_router
from app.projects.router import router as projects_router
from app.queries.router import router as queries_router
from app.rag.qdrant_store import check_qdrant_health, ensure_collection

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_collection()
    yield


app = FastAPI(title="Project Keystone", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(documents_router)
app.include_router(queries_router)
app.include_router(jira_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "Project Keystone", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready() -> dict[str, str | bool]:
    postgres_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        postgres_ok = True
    except Exception:
        postgres_ok = False

    qdrant_ok = check_qdrant_health()
    status_value = "ok" if postgres_ok and qdrant_ok else "degraded"
    return {"status": status_value, "postgres": postgres_ok, "qdrant": qdrant_ok}
