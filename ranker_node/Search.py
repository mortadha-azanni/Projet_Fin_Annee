from BM25.BM25Engine import BM25Engine
from BM25.database import getCategoriesPath, getProductByCategory, getProductByCategoryTree
from BM25.utils import getAVGDocLength

from SementicSearch.SementicEngine import SementicEngine
from Hybrid.fusion import reciprocal_rank_fusion

from NER.entity_extractor import EntityExtractor
from NER.utils import normalize
from LLM.LLM import query_gemini
from LLM.FLLM import MarkdownDescription
from celery_app import celery_app


_SMALL_TALK_PHRASES = {
    "hi",
    "hello",
    "hey",
    "yo",
    "bonjour",
    "salut",
    "thanks",
    "thank you",
    "sup",
    "what now",
    "now what",
}


def _normalize_query_text(query: str) -> str:
    lowered = (query or "").strip().lower()
    if not lowered:
        return ""

    punctuation = ",.!?;:-_()[]{}'\""
    cleaned = lowered.translate(str.maketrans("", "", punctuation))
    return " ".join(cleaned.split())


def _is_product_search_query(query: str) -> bool:
    normalized = _normalize_query_text(query)
    if len(normalized) < 3:
        return False

    if normalized in _SMALL_TALK_PHRASES:
        return False

    return True


def _strip_embedding(document: dict) -> dict:
    if not isinstance(document, dict):
        return document
    return {key: value for key, value in document.items() if key != "embedding"}


def _sanitize_ranked_results(results: list[dict]) -> list[dict]:
    sanitized = []
    for item in results:
        if not isinstance(item, dict):
            sanitized.append(item)
            continue
        new_item = dict(item)
        new_item["document"] = _strip_embedding(item.get("document", {}))
        sanitized.append(new_item)
    return sanitized

@celery_app.task(bind=True)
def perform_search(self, user_query_str: str):
    cleaned_query = (user_query_str or "").strip()

    if not _is_product_search_query(cleaned_query):
        if self:
            self.update_state(
                state='PROGRESS',
                meta={'status': 'I can help with product searches. Tell me what item, brand, or budget you want.'}
            )
        return {
            "results": [],
            "final_response": "I can help with product searches. Tell me what item, brand, or budget you want, and I’ll look it up.",
            "message": "No product search detected.",
            "cache_key": None,
        }

    # ============================================================================
    # Query Normalization & Expansion
    # ============================================================================
    if self:
        self.update_state(state='PROGRESS', meta={'status': 'Normalizing query and extracting entities...'})
    
    extractor = EntityExtractor()
    normalized_query = extractor.extract(user_query_str)
    
    if self:
        self.update_state(state='PROGRESS', meta={'status': 'Fetching and ranking categories...'})

    # ============================================================================
    # MAIN SEARCH LOGIC
    # ============================================================================
    # Stage 1: Fetch and rank categories
    try:
        category_path_docs = getCategoriesPath()
    except Exception as exc:
        print(f"Failed to fetch categories Paths : {exc}")
        return {"error": f"Failed to connect to database: {exc}"}

    if not category_path_docs:
        print("No categories paths found in database.")
        return {"error": "No categories found in database."}

    search_query: str = user_query_str
    price_min, price_max = None, None 

    category_search = SementicEngine(
        documents=category_path_docs,
        text_key="path",
        generate_missing=False
    )

    all_category_paths_results = category_search.search(search_query)
    top_category_paths_results = all_category_paths_results[:3]

    if not top_category_paths_results:
        print("No matching categories paths found.")
        return {"error": "No matching categories found."}

    print(f"\n[Categories Selected] Top 3 categories:")
    for i, res in enumerate(top_category_paths_results, 1):
        print(f"  {i}. [Score: {res['score']:.4f}] {res['document']['path']} (ID: {res['document']['category_id']})")

    # Stage 2.25: LLM Call for the top category and the price range (if founded)
    ner_entities = normalized_query.get("brand", []) + normalized_query.get("model", []) + normalized_query.get("spec", [])
    price_constraints = normalized_query.get("price", [])

    category_snippets = [
        f"ID: {res['document']['category_id']} | Path: {res['document']['path']}" 
        for res in top_category_paths_results
    ]

    print("\n[LLM] Querying Gemini to parse prices and select the strongest category...")
    if self:
        self.update_state(state='PROGRESS', meta={'status': 'Consulting LLM for category and price selection...'})
    
    llm_results = query_gemini(
        user_query=user_query_str,
        ner_entities=ner_entities,
        category_dictionaries=category_snippets,
        price_constraints=price_constraints
    )

    price_min = llm_results.get("price", {}).get("min_price")
    price_max = llm_results.get("price", {}).get("max_price")
    selected_category_id = llm_results.get("selected_category_id")
    expand_to_children = llm_results.get("expand_to_children", False)

    if not selected_category_id:
        # Fallback to the first category if the LLM fails to return one
        print("[WARN] LLM failed to return a selected_category_id, logging fallback.")
        selected_category_id = top_category_paths_results[0]["document"]["category_id"]
        expand_to_children = True  # Default to expanding for fallback

    print(f"[Price Filter] {f'${price_min} - ${price_max}' if price_min or price_max else 'No price filter'}")
    print(f"[Selected Category ID] {selected_category_id} (expand_to_children: {expand_to_children})\n")

    # Extract search queries for downstream engines
    bm25_search_query = " ".join(llm_results.get("bm25_keywords", []))
    if not bm25_search_query.strip():
        bm25_search_query = user_query_str

    semantic_search_query = llm_results.get("semantic_blob", user_query_str)

    # Generate embedding for the semantic query downstream using the existing embed logic
    from SementicSearch.utils import embed
    from SementicSearch.SementicEngine import MODEL, DIMS
    query_embedding = embed(semantic_search_query, MODEL, DIMS)

    if self:
        mode_str = "tree" if expand_to_children else "exact"
        self.update_state(state='PROGRESS', meta={'status': f'Fetching products for category {selected_category_id} ({mode_str})...'})

    # Stage 2.5: Fetch products with hierarchical expansion
    if expand_to_children:
        print(f"\n[Fetching Products] Fetching ALL products in category tree {selected_category_id}")
        fetch_func = getProductByCategoryTree
    else:
        print(f"\n[Fetching Products] Fetching EXACT products for category {selected_category_id}")
        fetch_func = getProductByCategory

    try:
        product_docs = fetch_func(
            selected_category_id,
            price_min=price_min,
            price_max=price_max,
            query_embedding=query_embedding,
            limit=200
        )
    except Exception as exc:
        print(f"    [ERROR] Failed to fetch products: {exc}")
        return {"error": f"Database fetch error: {exc}"}

    if not product_docs and (price_min is not None or price_max is not None):
        print(f"\n[Fallback] No products found with price range. Retrying without price constraints...")
        price_min, price_max = None, None
        try:
            product_docs = fetch_func(
                selected_category_id,
                price_min=None,
                price_max=None,
                query_embedding=query_embedding,
                limit=200
            )
        except Exception as exc:
            print(f"    [ERROR] Failed to fetch products: {exc}")

    if not product_docs:
        print(f"\n[Fallback] No products found in category {selected_category_id}. Trying other categories...")
        price_min, price_max = None, None
        for cat_res in top_category_paths_results:
            fallback_cat_id = cat_res["document"]["category_id"]
            if fallback_cat_id != selected_category_id:
                try:
                    # Try tree expansion for fallback categories too
                    product_docs = getProductByCategoryTree(
                        fallback_cat_id,
                        price_min=None,
                        price_max=None,
                        query_embedding=query_embedding,
                        limit=200
                    )
                    if product_docs:
                        print(f"    [Fallback Success] Found {len(product_docs)} products in category tree {fallback_cat_id}")
                        break
                except Exception as exc:
                    pass

    if not product_docs:
        print(f"\n[Final Failure] No products found in any related category.")
        return {
            "results": [],
            "final_response": "I couldn’t find matching products for that query. Try adding a brand, category, model, or budget.",
            "message": "No products found for the given criteria.",
            "cache_key": None,
        }

    print(f"\n[Products Found] {len(product_docs)} total top pgvector products retrieved")

    # Since they are pulled from DB sorted by cosine distance natively, map them as semantic results!
    semantic_results = []
    # Approximate scores using reverse ranks since PGVector ordered them without strictly returning the calculation
    # For robust RRF, the explicit semantic score matters less than relative ranking
    for i, doc in enumerate(product_docs):
        semantic_results.append({"score": 1.0 / (i + 1), "document": doc})

    # Stage 3: Complete BM25 ranking over semantic candidates (Re-ranking via RRF)
    product_bm25 = BM25Engine(
        documents=product_docs,
        k1=1.5,
        b=0.6,
        avg_doc_length=getAVGDocLength(product_docs, text_key="search_text") if product_docs else 100,
        text_key="search_text"
    )

    print("\nBM25 Product Search Results (Re-ranked over pgvector subset):")
    bm25_results = product_bm25.search(bm25_search_query, top_k=200)

    if self:
        self.update_state(state='PROGRESS', meta={'status': 'Applying Reciprocal Rank Fusion (RRF) for final ranking...'})

    # Stage 4: Fusion using RRF
    print("\n[Hybrid Search] Applying Reciprocal Rank Fusion (RRF)...")
    rrf_results = reciprocal_rank_fusion(
        bm25_results=bm25_results,
        semantic_results=semantic_results,
        k=60
    )

    print("\nFinal RRF Results (Hybrid BM25 + Semantic):")
    for i, result in enumerate(rrf_results[:10], 1):
        doc = result["document"]
        price = doc.get('price', 'N/A')
        print(f"  {i}. [RRF: {result['rrf_score']:.6f}] [BM25: {result['bm25_score']:.4f}] [Semantic Rank: {result['semantic_score']:.4f}] {doc['description'][:45]}... | Price: ${price}")

    # ============================================================================
    # Caching Phase: Store Top 20, Return Top 5
    # ============================================================================
    if self:
        self.update_state(state='PROGRESS', meta={'status': 'Caching top 20 results and finalizing...'})

    top_20 = _sanitize_ranked_results(rrf_results[:20])
    top_5 = _sanitize_ranked_results(rrf_results[:5])
    top_5_documents = [result["document"] for result in top_5]

    final_response = MarkdownDescription(top_5_documents).generate() if top_5_documents else ""

    try:
        import redis
        import json
        import os
        
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        # Using db=1 to keep cache separate from Celery broker (db=0)
        r = redis.Redis(host=redis_host, port=redis_port, db=1) 
        
        task_id = self.request.id if self and hasattr(self, 'request') and self.request.id else "local_test"
        cache_key = f"search_results:{task_id}"
        
        # Serialize with default=str to handle UUIDs, Decimals, or Datetimes effortlessly
        r.setex(cache_key, 3600, json.dumps(top_20, default=str)) 
        print(f"\n[Cache] Stored top 20 results in Redis under key: {cache_key}")
    except Exception as e:
        print(f"\n[Cache Error] Failed to store results in Redis: {e}")

    return {
        "results": top_5,
        "final_response": final_response,
        "cache_key": f"search_results:{task_id}" if 'task_id' in locals() else None,
    }

if __name__ == '__main__':
    user_q = normalize("i want a good machine for playing under 3000dt")
    perform_search(user_q)
