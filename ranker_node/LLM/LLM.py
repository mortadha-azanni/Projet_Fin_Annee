import json
from importlib import import_module
from typing import Optional, Dict, List

from dotenv import load_dotenv
import os

dotenv = load_dotenv()
API_KEY = os.getenv("API_KEY") or os.getenv("api_key")
MODEL = os.getenv("LLM_MODEL") or "gemini-2.5-flash"

from pydantic import BaseModel, Field

class PriceConstraints(BaseModel):
    min_price: Optional[float] = Field(None, description="Minimum price constraint")
    max_price: Optional[float] = Field(None, description="Maximum price constraint")

class GeminiResponseSchema(BaseModel):
    semantic_blob: str = Field(..., description="A 2-sentence technical description of the perfect product")
    bm25_keywords: List[str] = Field(..., description="List of highly relevant technical keywords and synonyms")
    negative_keywords: List[str] = Field(..., description="List of negative keywords to exclude")
    price: PriceConstraints
    selected_category_id: Optional[int] = Field(None, description="The strictly chosen category ID")
    expand_to_children: bool = Field(False, description="Whether to include all child categories under selected_category_id")

genai = import_module("google.genai")
client = genai.Client(api_key=API_KEY) if API_KEY else None
default_prompt = """You are an expert e-commerce search expansion AI. Your task is to bridge the gap between a user's natural language search query and our technical product database. 

You will be provided with the user's original query, extracted entities (brands/specs), extracted price constraints, and technical dictionary snippets for the top 3 most relevant product categories.

Using this information, you must perform a "HyDE" (Hypothetical Document Embeddings) generation. Write a hypothetical, 2-sentence technical description of the perfect product for this user, strictly using the provided category attributes.

### CATEGORY HIERARCHY ###
Categories have hierarchical paths like: "informatique.ordinateurs.pc-portable"
- Use parent categories to include ALL their children
- Use specific categories for exact matches
- Examples:
  * Select category 11 (ordinateurs) with expand_to_children=true → ALL computers/laptops/desktops
  * Select category 111 (pc-portable) with expand_to_children=false → ONLY laptops

### INPUT DATA ###
Original User Query: 
{user_query}

Extracted NER Entities (Brands/Specs):
{ner_entities}

Extracted Price Constraints:
{price_constraints}

Category Dictionary Snippets (Top 3 with ID and Path):
{category_dictionaries}

### INSTRUCTIONS ###
1. Analyze the user query to understand if they want BROAD or SPECIFIC products.
   - "laptop", "computer", "electronics" → broad → select parent category, expand_to_children=true
   - "MacBook Pro", "gaming laptop", "specific model" → specific → select specific category, expand_to_children=false
2. Select the most relevant category ID.
3. Set expand_to_children=true if user wants ANY product in that category tree (e.g., "show me all laptops").
4. Set expand_to_children=false if user wants EXACT match (e.g., "MacBook Air only").

### OUTPUT FORMAT ###
Return valid JSON:

{{
  "semantic_blob": "A 2-sentence technical description...",
  "bm25_keywords": ["keyword1", "synonym1"],
  "negative_keywords": ["conflicting_term1"],
  "price": {{"min_price": 100, "max_price": 500}},
  "selected_category_id": 11,
  "expand_to_children": true
}}
"""

def query_gemini(user_query: str, ner_entities: List[str], category_dictionaries: Optional[List[str]] = None, price_constraints: Optional[str] = None) -> Dict:
    prompt = default_prompt.format(user_query=user_query, ner_entities=", ".join(ner_entities) if ner_entities else "", category_dictionaries="\n".join(category_dictionaries) if category_dictionaries else "", price_constraints=", ".join(price_constraints) if price_constraints else "")

    try:
        import time
        GenerateContentConfig = import_module("google.genai.types").GenerateContentConfig

        if not client:
            raise ValueError("Gemini API client is not configured")
        
        max_retries = 4
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=MODEL,
                    contents=prompt,
                    config=GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json",
                        response_schema=GeminiResponseSchema,
                    )
                )
                
                # Pydantic schema enforcement eliminates the need for regex hacking.
                # GenAI SDK will strictly return JSON matching the GeminiResponseSchema.
                return json.loads(response.text or "{}")
            except Exception as e:
                # Catch temporary availability errors (503) or rate limits (429)
                error_msg = str(e)
                if ("503" in error_msg or "429" in error_msg) and attempt < max_retries - 1:
                    print(f"[Gemini] Server busy, attempt {attempt + 1}/{max_retries}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    # Throw genuine errors (or final attempt failures) to the outer try/except
                    raise e
        
        raise Exception("Max retries exceeded")
    
    except Exception as e:
        print(f"Error querying Gemini: {e}")
        return {
            "semantic_blob": "",
            "bm25_keywords": [],
            "negative_keywords": [],
            "price": {
                "min_price": None,
                "max_price": None
            },
            "selected_category_id": None,
            "expand_to_children": False
        }