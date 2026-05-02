"""
Generation layer — builds prompts and calls OpenAI for final answers.
Routes between GPT-5.4 nano (simple) and GPT-5.4 mini (synthesis).
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import (
    MODEL_NANO, MODEL_MINI, OPENAI_API_KEY,
    MAX_TOKENS_NANO, MAX_TOKENS_MINI, TEMPERATURE
)

SYSTEM_PROMPT = """You are a helpful Boston parking regulations assistant. 
You answer questions about Boston parking rules, fines, street cleaning schedules, 
and resident permit programs based strictly on the provided context.

Rules:
- Answer based ONLY on the provided context. Do not invent rules or fines.
- If the context does not contain enough information to answer, say so clearly.
- Be specific: include exact dollar amounts, times, and dates when available.
- When citing street cleaning schedules, always mention the specific days and hours.
- For violation fines, always mention both the base fine AND the late penalty.
- If a rule has exceptions, mention them.
- Keep answers concise but complete — a driver should be able to act on your answer.
- Always end with a note to verify against posted street signs for street cleaning questions.

Format:
- Use plain prose for simple questions
- Use a short bulleted list only when comparing multiple violations or rules
- Do not use headers or markdown formatting"""


def build_prompt(query: str, chunks: list[dict]) -> str:
    """Assembles the user message with retrieved context."""
    context_parts = []
    for i, chunk in enumerate(chunks):
        source = chunk.get("metadata", {}).get("source_name", "Boston Parking Regulations")
        context_parts.append(f"[Source {i+1}: {source}]\n{chunk['text']}")

    context = "\n\n---\n\n".join(context_parts)

    return f"""Context from Boston parking regulations:

{context}

---

Question: {query}

Answer based on the context above:"""


def classify_complexity(query: str, chunks: list[dict]) -> str:
    """
    Route to nano vs mini based on query + chunk complexity.
    Mini for: multi-source synthesis, regulatory conflicts, edge cases.
    Nano for: single-fact lookups, schedule queries, simple fine lookups.
    """
    domains = set(c.get("metadata", {}).get("domain", "") for c in chunks)
    multi_domain = len(domains) > 1

    complexity_signals = [
        "even though", "but i have", "does that mean", "still need to",
        "exempt", "exception", "override", "apply to", "unless",
        "what if", "can i still", "does this affect",
    ]
    is_complex = any(sig in query.lower() for sig in complexity_signals)

    if multi_domain or is_complex:
        return MODEL_MINI
    return MODEL_NANO


def generate_answer(
    query: str,
    chunks: list[dict],
    conversation_history: list[dict] = None,
) -> dict:
    """
    Generates a final answer from retrieved chunks.
    Returns dict with answer, model used, and sources cited.
    """
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    model = classify_complexity(query, chunks)
    max_tokens = MAX_TOKENS_MINI if model == MODEL_MINI else MAX_TOKENS_NANO

    user_message = build_prompt(query, chunks)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Include conversation history for multi-turn support
    if conversation_history:
        messages.extend(conversation_history[-6:])  # last 3 turns

    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_completion_tokens=max_tokens,
        temperature=TEMPERATURE,
    )

    answer = response.choices[0].message.content.strip()

    # Collect unique sources cited
    sources = list({
        c.get("metadata", {}).get("source_name", "Boston Parking Regulations")
        for c in chunks
    })

    return {
        "answer": answer,
        "model_used": model,
        "sources": sources,
        "chunks_used": len(chunks),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
    }