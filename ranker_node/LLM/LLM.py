import json
from typing import Optional, Dict, List

from google import genai
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

client = genai.Client(api_key=API_KEY)
default_prompt = """You are an expert e-commerce search expansion AI. Your task is to bridge the gap between a user's natural language search query and our technical product database. 

You will be provided with the user's original query, extracted entities (brands/specs), extracted price constraints, and technical dictionary snippets for the top 3 most relevant product categories.

Using this information, you must perform a "HyDE" (Hypothetical Document Embeddings) generation. Write a hypothetical, 2-sentence technical description of the perfect product for this user, strictly using the provided category attributes.

### INPUT DATA ###
Original User Query: 
{user_query}

Extracted NER Entities (Brands/Specs):
{ner_entities}

Extracted Price Constraints:
{price_constraints}

Expanded Dictionary Snippets (Top 3 Category Paths):
{category_dictionaries}

### INSTRUCTIONS ###
1. Analyze the user query and extracted entities to understand the core intent.
2. Cross-reference this intent with the provided Expanded Dictionary Snippets to identify the correct technical terminology, synonyms, and specifications.
3. Generate a 2-sentence hypothetical product description (`semantic_blob`) that perfectly matches the user's intent using strict technical attributes. 
4. Extract a list of highly relevant technical keywords and synonyms (`bm25_keywords`).
5. Identify terms that might cause false positives and should be excluded (`negative_keywords`).
6. Analyze the extracted price constraints and format them into a minimum and maximum numerical value. Use `null` if a bound is not specified.
7. Select the single most relevant category ID from the provided Expanded Dictionary Snippets that best matches the user's intent.

### OUTPUT FORMAT ###
You must output your response STRICTLY as a valid JSON object matching the following structure. Do not include markdown formatting, explanations, or any text outside the JSON object.

{{
  "semantic_blob": "A 2-sentence technical description of the perfect product for this user, strictly using the provided category attributes.",
  "bm25_keywords": ["keyword1", "synonym1", "tech_spec1", "attribute1"],
  "negative_keywords": ["conflicting_term1", "irrelevant_category1"],
  "price": {{
    "min_price": 100,
    "max_price": 500
  }},
  "selected_category_id": 123
}}
"""

def query_gemini(user_query: str, ner_entities: List[str], category_dictionaries: Optional[List[str]] = None, price_constraints: Optional[str] = None) -> Dict:
    prompt = default_prompt.format(user_query=user_query, ner_entities=", ".join(ner_entities) if ner_entities else "", category_dictionaries="\n".join(category_dictionaries) if category_dictionaries else "", price_constraints=", ".join(price_constraints) if price_constraints else "")

    try:
        import time
        from google.genai.types import GenerateContentConfig
        
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
            "selected_category_id": None
        }