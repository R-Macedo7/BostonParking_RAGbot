"""
Pydantic request/response models for the Boston Parking RAG API.
Keeping these separate from main.py makes them importable by tests.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="User's parking question")
    conversation_history: Optional[list[dict]] = Field(
        default=None,
        description="Previous turns for multi-turn support. Each dict: {role, content}"
    )
    top_k: Optional[int] = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is the fine for parking near a fire hydrant in Boston?",
                "conversation_history": None,
                "top_k": 5,
            }
        }


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Generated answer from the RAG pipeline")
    model_used: str = Field(..., description="OpenAI model that generated the answer")
    sources: list[str] = Field(..., description="Source documents cited in the answer")
    chunks_used: int = Field(..., description="Number of retrieved chunks passed to generation")
    sub_queries: list[str] = Field(..., description="Sub-queries after decomposition")
    query_type: str = Field(..., description="Detected domain: violations | permits | street_cleaning | regulations | general")
    usage: dict = Field(..., description="Token usage from OpenAI API")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "The fine for parking within 10 feet of a fire hydrant in Boston is $100. If unpaid after 21 days, a late penalty of $33 is added.",
                "model_used": "gpt-5.4-nano-2026-03-17",
                "sources": ["Boston Parking Ticket Fines and Codes"],
                "chunks_used": 3,
                "sub_queries": ["What is the fine for parking near a fire hydrant in Boston?"],
                "query_type": "violations",
                "usage": {"prompt_tokens": 450, "completion_tokens": 60, "total_tokens": 510}
            }
        }


class HealthResponse(BaseModel):
    status: str
    service: str


class SourceInfo(BaseModel):
    name: str
    domain: str
    url: str
    refresh_days: int


class SourcesResponse(BaseModel):
    sources: list[SourceInfo]