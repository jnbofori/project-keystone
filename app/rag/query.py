from uuid import UUID

from llama_index.core import Settings as LlamaSettings
from llama_index.core import VectorStoreIndex
from llama_index.core.vector_stores import FilterCondition, FilterOperator, MetadataFilter, MetadataFilters
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore

from app.config import get_settings
from app.rag.qdrant_store import get_qdrant_client

settings = get_settings()

RAG_PROMPT = """Answer the question based only on the following context. \
If the answer is not contained in the context, say you don't have enough information.

Context:
{context}

Question: {question}

Answer:"""


def _build_index() -> VectorStoreIndex:
    embed_model = OpenAIEmbedding(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )
    llm = OpenAI(
        model=settings.openai_llm_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )
    LlamaSettings.embed_model = embed_model
    LlamaSettings.llm = llm

    vector_store = QdrantVectorStore(
        client=get_qdrant_client(),
        collection_name=settings.qdrant_collection,
    )
    return VectorStoreIndex.from_vector_store(vector_store=vector_store, embed_model=embed_model)


def ask_project_question(project_id: UUID, question: str) -> tuple[str, list[dict]]:
    index = _build_index()
    filters = MetadataFilters(
        filters=[
            MetadataFilter(
                key="project_id",
                value=str(project_id),
                operator=FilterOperator.EQ,
            )
        ],
        condition=FilterCondition.AND,
    )

    retriever = index.as_retriever(
        similarity_top_k=settings.retrieval_top_k,
        filters=filters,
    )
    nodes = retriever.retrieve(question)

    if not nodes:
        return (
            "I don't have enough information in the project documents to answer that question.",
            [],
        )

    context = "\n\n".join(node.get_content() for node in nodes)
    prompt = RAG_PROMPT.format(context=context, question=question)

    llm = OpenAI(
        model=settings.openai_llm_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )
    response = llm.complete(prompt)
    answer = str(response)

    sources = []
    for node in nodes:
        metadata = node.metadata or {}
        sources.append(
            {
                "document_id": metadata.get("document_id"),
                "filename": metadata.get("filename"),
                "text": node.get_content(),
                "score": float(node.score) if node.score is not None else None,
            }
        )

    return answer, sources
