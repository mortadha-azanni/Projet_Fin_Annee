from BM25.BM25Engine import BM25Engine
from BM25.database import getCategoriesPath, getProductByCategory, getProductByCategoryTree
from BM25.utils import getAVGDocLength

from SementicSearch.SementicEngine import SementicEngine
from Hybrid.fusion import reciprocal_rank_fusion

from NER.entity_extractor import EntityExtractor
from NER.utils import normalize
from LLM.LLM import query_gemini
from LLM.FLLM import MarkdownDescription
from celery_app import celery_app, pubsub_redis
import json
from typing import Any, Dict, Optional
from core.sanitization import sanitize_text, validate_and_sanitize_input


def push_event(task, task_state, status_msg, user_id=None, extra_payload=None):
    if task:
        task.update_state(state=task_state, meta={"status": status_msg})
        
    if user_id and task:
        task_id = task.request.id
        channel = f"client-events:{user_id}"
        
        event_type = "status"
        if task_state == "FAILURE":
            event_type = "error"
            
        payload = {
            "type": event_type,
            "task_id": task_id,
            "payload": {
                "status": status_msg
            }
        }
        
        if task_state == "FAILURE":
            payload["payload"] = {"message": status_msg}
            
        if extra_payload:
            payload.update(extra_payload)
            
        try:
            pubsub_redis.publish(channel, json.dumps(payload, default=str))
        except Exception as e:
            print(f"[Redis Publish Error] {e}")

def _normalize_query_text(query: str) -> str:
    lowered = (query or "").strip().lower()
    if not lowered:
        return ""

    punctuation = ",.!?;:-_()[]{}'\""
    cleaned = lowered.translate(str.maketrans("", "", punctuation))
    return " ".join(cleaned.split())


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
def perform_search(
    self,
    user_query_str: str,
    user_id: Optional[str] = None,
    intent: Optional[str] = None,
    constraints: Optional[Dict[str, Any]] = None,
    semantic_cache_key: Optional[str] = None,
):
    # Sanitize input parameters
    user_query_str = sanitize_text(user_query_str, 500) if user_query_str else ""
    user_id = sanitize_text(user_id, 100) if user_id else None
    intent = sanitize_text(intent, 50) if intent else "search"
    constraints = validate_and_sanitize_input(constraints) if constraints else {}
    semantic_cache_key = sanitize_text(semantic_cache_key, 200) if semantic_cache_key else None

    constraints = constraints or {}

    # Intent routing was already handled by Gateway's Classifier.
    # If the gateway explicitly sent us a "chitchat" or "ambiguous" fallback by mistake, handle it gracefully.
    if intent in ("chitchat", "clarify", "ambiguous"):
        if self:
            push_event(self, 'PROGRESS', 'I can help with product searches. Tell me what item, brand, or budget you want.', user_id)
        push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={'type': 'chunk', 'payload': {'content': 'I can help with product searches. Tell me what item, brand, or budget you want, and I’ll look it up.'}})
        push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={'type': 'end'})
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
        push_event(self, 'PROGRESS', 'Normalizing query and extracting entities...', user_id)
    
    extractor = EntityExtractor()
    normalized_query = extractor.extract(user_query_str)
    
    if self:
        push_event(self, 'PROGRESS', 'Fetching and ranking categories...', user_id)

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
    hard_max_price = constraints.get("max_price")
    hard_location = constraints.get("location")
    hard_filter_terms = constraints.get("filters") or []
    
    # Merge Gateway global intent constraints with local Ranked extraction
    extracted_prices = normalized_query.get("price", [])
    if constraints and constraints.get("max_price"):
        extracted_prices.append(f"Under {constraints['max_price']}")
    
    price_constraints = extracted_prices

    category_snippets = [
        f"ID: {res['document']['category_id']} | Path: {res['document']['path']}" 
        for res in top_category_paths_results
    ]

    print("\n[LLM] Querying Gemini to parse prices and select the strongest category...")
    if self:
        push_event(self, 'PROGRESS', 'Consulting LLM for category and price selection...', user_id)
    
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
        try:
            product_docs = getProductByCategoryTree(
                selected_category_id,
                price_min=price_min,
                price_max=price_max,
                query_embedding=query_embedding,
                limit=200,
            )
        except Exception as exc:
            print(f"    [ERROR] Failed to fetch products: {exc}")
            return {"error": f"Database fetch error: {exc}"}
    else:
        print(f"\n[Fetching Products] Fetching EXACT products for category {selected_category_id}")
        try:
            product_docs = getProductByCategory(  # type: ignore[call-arg]
                selected_category_id,
                price_min=price_min,
                price_max=price_max,
                query_embedding=query_embedding,
                limit=200,
                location=hard_location,
                filter_terms=hard_filter_terms,
            )
        except Exception as exc:
            print(f"    [ERROR] Failed to fetch products: {exc}")
            return {"error": f"Database fetch error: {exc}"}

    # Fallback Relaxer: If no products, relax hard filters one by one
    if not product_docs:
        print(f"\n[Fallback Relaxer] No products found with strict filters. Relaxing filters one by one...")
        relaxations = [
            {"location": None, "filter_terms": hard_filter_terms, "max_price": hard_max_price},
            {"location": hard_location, "filter_terms": None, "max_price": hard_max_price},
            {"location": hard_location, "filter_terms": hard_filter_terms, "max_price": None},
        ]
        for i, relaxed in enumerate(relaxations, 1):
            relaxed_location = relaxed["location"]
            relaxed_filter_terms = relaxed["filter_terms"]
            relaxed_max_price = relaxed["max_price"]
            # Adjust price_max if relaxing max_price
            adjusted_price_max = price_max if relaxed_max_price is not None else None
            try:
                product_docs = getProductByCategory(  # type: ignore[call-arg]
                    selected_category_id,
                    price_min=price_min,
                    price_max=adjusted_price_max,
                    query_embedding=query_embedding,
                    limit=200,
                    location=relaxed_location,
                    filter_terms=relaxed_filter_terms,
                )
                if product_docs:
                    print(f"    [Fallback Success] Found {len(product_docs)} products after relaxing filter set {i}")
                    break
            except Exception as exc:
                print(f"    [Fallback Error] Failed during relaxation {i}: {exc}")

    if not product_docs and (price_min is not None or price_max is not None):
        print(f"\n[Fallback] No products found with price range. Retrying without price constraints...")
        price_min, price_max = None, None
        try:
            if expand_to_children:
                product_docs = getProductByCategoryTree(
                    selected_category_id,
                    price_min=None,
                    price_max=None,
                    query_embedding=query_embedding,
                    limit=200,
                )
            else:
                product_docs = getProductByCategory(  # type: ignore[call-arg]
                    selected_category_id,
                    price_min=None,
                    price_max=None,
                    query_embedding=query_embedding,
                    limit=200,
                    location=hard_location,
                    filter_terms=hard_filter_terms,
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
                        limit=200,
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
        push_event(self, 'PROGRESS', 'Applying Reciprocal Rank Fusion (RRF) for final ranking...', user_id)

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

    # Stage 8: Diversity Filter - Limit items from identical categories/sources
    print("\n[Stage 8] Applying Diversity Filter...")
    from collections import defaultdict
    category_count: dict[str | None, int] = defaultdict(int)
    max_per_category = 3  # Limit to 3 items per category to ensure diversity
    diverse_results = []
    for result in rrf_results:
        category_id = result["document"].get("category_id")
        if category_count[category_id] < max_per_category:
            diverse_results.append(result)
            category_count[category_id] += 1
    rrf_results = diverse_results
    print(f"  Diversity applied: {len(rrf_results)} results after filtering")

    # Stage 9: Cross-Encoder Re-Ranking
    print("\n[Stage 9] Cross-Encoder Re-Ranking...")
    try:
        from sentence_transformers import CrossEncoder  # type: ignore[import-not-found]
        cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        # Prepare query-document pairs for cross-encoder
        query_doc_pairs = []
        for result in rrf_results[:20]:  # Re-rank top 20
            doc = result["document"]
            # Combine title/description for better context
            doc_text = f"{doc.get('title', '')} {doc.get('description', '')}".strip()
            query_doc_pairs.append([user_query_str, doc_text])
        
        if query_doc_pairs:
            # Get cross-encoder scores
            cross_scores = cross_encoder.predict(query_doc_pairs)
            
            # Re-rank based on cross-encoder scores
            scored_results = []
            for i, result in enumerate(rrf_results[:20]):
                new_result = dict(result)
                new_result["cross_score"] = float(cross_scores[i])
                scored_results.append(new_result)
            
            # Sort by cross-encoder score (higher is better)
            scored_results.sort(key=lambda x: x["cross_score"], reverse=True)
            
            # Update rrf_results with re-ranked order
            rrf_results = scored_results + rrf_results[20:]
            
            print(f"  Cross-encoder re-ranking completed for top {len(scored_results)} results")
        else:
            print("  Cross-encoder: No query-doc pairs to score")
            
    except ImportError as e:
        print(f"  Cross-encoder not available: {e}. Skipping re-ranking.")
    except Exception as e:
        print(f"  Cross-encoder error: {e}. Falling back to RRF order.")

    # ============================================================================
    # Caching Phase: Store Top 20, Return Top 5
    # ============================================================================
    if self:
        push_event(self, 'PROGRESS', 'Caching top 20 results and finalizing...', user_id)

    top_20 = _sanitize_ranked_results(rrf_results[:20])
    top_5 = _sanitize_ranked_results(rrf_results[:5])
    top_5_documents = [result["document"] for result in top_5]

    final_response = MarkdownDescription(top_5_documents, intent).generate() if top_5_documents else ""

    try:
        from importlib import import_module
        import json
        import os
        redis = import_module("redis")
        
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        # Using db=0 to match Gateway cache/pubsub database
        r = redis.Redis(host=redis_host, port=redis_port, db=0) 
        
        task_id = self.request.id if self and hasattr(self, 'request') and self.request.id else "local_test"
        cache_key = f"search_results:{task_id}"
        
        # Serialize with default=str to handle UUIDs, Decimals, or Datetimes effortlessly
        r.setex(cache_key, 3600, json.dumps(top_20, default=str)) 

        # Semantic cache used by gateway to short-circuit repeated queries.
        if semantic_cache_key:
            semantic_payload = {
                "results": top_20,
                "final_response": final_response,
            }
            r.setex(semantic_cache_key, 3600, json.dumps(semantic_payload, default=str))

        print(f"\n[Cache] Stored top 20 results in Redis under key: {cache_key}")
    except Exception as e:
        print(f"\n[Cache Error] Failed to store results in Redis: {e}")

    push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={'type': 'products', 'payload': {'items': top_5}})
    if final_response:
        push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={'type': 'chunk', 'payload': {'content': final_response}})
    push_event(self, 'SUCCESS', 'Search Complete', user_id, extra_payload={'type': 'end'})
    
    return {
        "results": top_5,
        "final_response": final_response,
        "cache_key": f"search_results:{task_id}" if 'task_id' in locals() else None,
    }

if __name__ == '__main__':
    user_q = normalize("i want a good machine for playing under 3000dt")
    perform_search(user_q)
