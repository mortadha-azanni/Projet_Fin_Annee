import os
import httpx
from pydantic import BaseModel
from typing import Literal, Optional, List

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "your-openrouter-key")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Stage 4 dictates a fast/cheap model
MODEL = "meta-llama/llama-3-8b-instruct:free"

class ExtractedConstraints(BaseModel):
    n_results: Optional[int]
    max_price: Optional[float]
    location: Optional[str]
    open_now: Optional[bool]
    filters: Optional[List[str]]

class ClassifierDecision(BaseModel):
    intent: Literal["chitchat", "ambiguous", "comparison", "constrained", "search"]
    constraints: Optional[ExtractedConstraints]
    clarification_question: Optional[str]
    direct_reply: Optional[str]

async def classify_intent(query: str, context: list) -> dict:
    """
    Stage 4: LLM Role 1 - Query Classifier
    Routes the query and extracts structured constraints.
    """
    system_prompt = """
    You are Stage 4 of the Search Pipeline. Classify the user's intent.
    Intents:
    - 'chitchat': Greetings, thanks, or non-search conversation.
    - 'ambiguous': Search is too vague. Needs clarification.
    - 'comparison': Asking 'X vs Y' or 'which is better'.
    - 'constrained': Seeking items with strict parameters (e.g., 'under $50', 'near me').
    - 'search': Standard product or business lookup.

    If 'chitchat' or 'ambiguous', provide 'direct_reply' or 'clarification_question'.
    If 'comparison', 'constrained', or 'search', fill 'constraints' if any are explicitly mentioned.
    """

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {context}\\nQuery: {query}"}
        ],
        "response_format": {"type": "json_object"} # Assuming model supports JSON mode
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(OPENROUTER_URL, headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}, json=payload)
            response.raise_for_status()
            import json
            return json.loads(response.json()["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"[Stage 4 Error] {e}")
        return {"intent": "search"} # Fail-safe Fallback

