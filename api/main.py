"""
FastAPI application — Boston Parking RAG chatbot API.

Endpoints:
  POST /chat       — main query endpoint
  GET  /health     — health check
  GET  /sources    — list indexed sources
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from api.models import ChatRequest, ChatResponse, HealthResponse, SourcesResponse, SourceInfo
from api.middleware import RequestLoggingMiddleware, RateLimitMiddleware, ErrorHandlingMiddleware
from retrieval.hybrid_retriever import hybrid_search
from retrieval.metadata_filter import classify_query
from retrieval.query_decomposer import decompose_query
from generation.generator import generate_answer
from generation.response_formatter import format_response, format_no_results_response
from config.settings import TOP_K_FINAL, SOURCES

app = FastAPI(
    title="Boston Parking RAG",
    description="AI-powered Boston parking regulations assistant",
    version="1.0.0",
)

# ── Middleware ──────────────────────────────────────────────────────────────
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=30, window_seconds=60)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Core RAG Pipeline ───────────────────────────────────────────────────────

def run_rag_pipeline(
    query: str,
    conversation_history: list = None,
    top_k: int = TOP_K_FINAL,
) -> dict:
    # 1. Classify intent
    intent = classify_query(query)

    # 2. Decompose if multi-part
    sub_queries = decompose_query(query) if intent.is_multi_part else [query]

    # 3. Retrieve chunks for each sub-query, deduplicate
    all_chunks = []
    seen_ids = set()

    for sub_q in sub_queries:
        sub_intent = classify_query(sub_q)
        chunks = hybrid_search(
            query=sub_q,
            domain_filter=sub_intent.domain_filter,
            top_k=top_k,
        )
        for chunk in chunks:
            if chunk["id"] not in seen_ids:
                seen_ids.add(chunk["id"])
                all_chunks.append(chunk)

    # Cap total context
    final_chunks = all_chunks[:top_k * 2]

    if not final_chunks:
        return format_no_results_response(intent.query_type, sub_queries)

    # 4. Generate answer
    result = generate_answer(query, final_chunks, conversation_history)

    # 5. Format response
    return format_response(
        answer=result["answer"],
        chunks=final_chunks,
        model_used=result["model_used"],
        sub_queries=sub_queries,
        query_type=intent.query_type,
        usage=result["usage"],
    )


# ── Endpoints ───────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    result = run_rag_pipeline(
        query=request.query.strip(),
        conversation_history=request.conversation_history,
        top_k=request.top_k,
    )
    return ChatResponse(**result)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="Boston Parking RAG")


@app.get("/sources", response_model=SourcesResponse)
async def sources():
    return SourcesResponse(
        sources=[
            SourceInfo(
                name=key,
                domain=val["domain"],
                url=val["url"],
                refresh_days=val["refresh_days"],
            )
            for key, val in SOURCES.items()
        ]
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)