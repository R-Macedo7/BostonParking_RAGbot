"""
Query decomposer — splits multi-part queries into focused sub-queries.
Uses GPT-5.4 nano (fast + cheap, this is a lightweight routing task).
"""

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import MODEL_NANO, OPENAI_API_KEY, MAX_TOKENS_NANO


DECOMPOSE_SYSTEM_PROMPT = """You are a query decomposer for a Boston parking regulations chatbot.

Your job: given a complex user question, break it into 2-4 focused sub-questions 
that can each be answered independently by searching a parking regulations database.

Rules:
- Only decompose if the question is genuinely multi-part
- If the question is simple and single-topic, return it as-is in a list of 1
- Keep sub-questions short and specific
- Focus each sub-question on ONE of: violation fines, permit rules, street cleaning schedules, or general regulations
- Preserve important context (street names, violation types, neighborhoods) in each sub-question

Respond ONLY with a JSON array of strings. No explanation, no markdown.
Example: ["What is the fine for double parking in Zone A?", "What is the late penalty if unpaid?"]"""


def decompose_query(query: str) -> list[str]:
    """
    Decomposes a query into sub-queries if multi-part.
    Returns a list of 1 item for simple queries, 2-4 for complex ones.
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model=MODEL_NANO,
            messages=[
                {"role": "system", "content": DECOMPOSE_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            max_completion_tokens=MAX_TOKENS_NANO,
            temperature=0.0,
        )

        content = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        sub_queries = json.loads(content)

        if not isinstance(sub_queries, list) or not sub_queries:
            return [query]

        # Sanity check — cap at 4 sub-queries
        return [str(q) for q in sub_queries[:4]]

    except Exception as e:
        # Fallback: return original query unchanged
        print(f"[decomposer] Warning: decomposition failed ({e}), using original query")
        return [query]