import httpx
import json
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional

from core.config import settings  # type: ignore[import-not-found]

class ExtractedConstraints(BaseModel):
    max_price: Optional[float] = Field(default=None, description="Maximum price constraint mentioned.")
    location: Optional[str] = Field(default=None, description="City or location constraint.")
    filters: Optional[List[str]] = Field(default=None, description="Other hard filters (e.g. brand, color).")

class ExtractedEntities(BaseModel):
    products: Optional[List[str]] = Field(default=None, description="Product names or items mentioned.")
    brands: Optional[List[str]] = Field(default=None, description="Brand names mentioned.")
    categories: Optional[List[str]] = Field(default=None, description="Categories or types mentioned.")
    dates: Optional[List[str]] = Field(default=None, description="Dates or time periods mentioned.")

class ClassifierDecision(BaseModel):
    intent: Literal["chitchat", "clarify", "ambiguous", "comparison", "constrained", "search"] = Field(description="The primary intent of the user.")
    constraints: Optional[ExtractedConstraints] = Field(default=None, description="Extracted constraints if intent is constrained or search.")
    entities: Optional[ExtractedEntities] = Field(default=None, description="Extracted NER entities from the query.")
    direct_reply: Optional[str] = Field(default=None, description="If intent is chitchat, the friendly assistant reply.")
    clarification_question: Optional[str] = Field(default=None, description="If intent is clarify/ambiguous, the question to ask back.")

async def classify_intent(query: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Stage 4: LLM Role 1 - Query Classifier using Gemini 1.5
    Evaluates the intent natively and decides if Ranker should be invoked.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return {"intent": "search", "constraints": {}}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    context_str = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history[-4:]]) # Last 4 msgs
    
    system_prompt = """You are the Query Routing Engine for an e-commerce semantic search platform.
    Analyze the user's latest message and their immediate context history. 
    Classify their intent:
    - 'chitchat': Greetings, thanks, or non-search conversation. Fill 'direct_reply'.
    - 'clarify': Cannot perform a search yet. Needs more information. Fill 'clarification_question'.
    - 'comparison': Asking 'X vs Y' or 'which is better'.
    - 'constrained': Seeking items with strict parameters (e.g., 'under $50', 'near me'). Fill 'constraints'.
    - 'search': Standard product checkout or business lookup.

    Additionally, extract Named Entities (NER) from the query:
    - products: Specific product names or items.
    - brands: Brand names mentioned.
    - categories: Categories or types (e.g., electronics, clothing).
    - dates: Dates or time periods.

    Return JSON matching the schema provided exactly."""

    user_prompt = f"Context:\n{context_str}\n\nUser Query: {query}"
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "intent": {"type": "STRING", "enum": ["chitchat", "clarify", "comparison", "constrained", "search"]},
            "constraints": {
                "type": "OBJECT",
                "properties": {
                    "max_price": {"type": "NUMBER"},
                    "location": {"type": "STRING"},
                    "filters": {"type": "ARRAY", "items": {"type": "STRING"}}
                }
            },
            "entities": {
                "type": "OBJECT",
                "properties": {
                    "products": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "brands": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "categories": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "dates": {"type": "ARRAY", "items": {"type": "STRING"}}
                }
            },
            "direct_reply": {"type": "STRING"},
            "clarification_question": {"type": "STRING"}
        },
        "required": ["intent"]
    }

    payload = {
        "contents": [
            {
                "parts": [{"text": system_prompt + "\\n\\n" + user_prompt}]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema,
            "temperature": 0.0
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            
            parsed = json.loads(text)
            
            # Normalization fallback
            if parsed.get("intent") == "ambiguous":
                parsed["intent"] = "clarify"

            if parsed.get("intent") not in ["chitchat", "clarify", "comparison", "constrained", "search"]:
                parsed["intent"] = "search"
                
            return parsed
            
    except Exception as e:
        print(f"[Stage 4 Error] Gemini Classification failed: {e}")
        return {"intent": "search", "constraints": {}} # Fail-safe Fallback
