"""
Prompt builder — assembles system prompts and user messages
for the generation layer. Separated from generator.py so prompt
logic can be iterated independently.
"""

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


def build_context_block(chunks: list[dict]) -> str:
    """Formats retrieved chunks into a labeled context block."""
    parts = []
    for i, chunk in enumerate(chunks):
        source = chunk.get("metadata", {}).get("source_name", "Boston Parking Regulations")
        domain = chunk.get("metadata", {}).get("domain", "")
        parts.append(f"[Source {i+1} | {source} | {domain}]\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def build_user_message(query: str, chunks: list[dict]) -> str:
    """Assembles the full user message with context + question."""
    context = build_context_block(chunks)
    return (
        f"Context from Boston parking regulations:\n\n"
        f"{context}\n\n"
        f"---\n\n"
        f"Question: {query}\n\n"
        f"Answer based on the context above:"
    )


def build_messages(
    query: str,
    chunks: list[dict],
    conversation_history: list[dict] = None,
) -> list[dict]:
    """
    Builds the full messages array for the OpenAI API call.
    Includes system prompt, optional history, and user message.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if conversation_history:
        # Include last 3 turns (6 messages) for context
        messages.extend(conversation_history[-6:])

    messages.append({
        "role": "user",
        "content": build_user_message(query, chunks),
    })

    return messages