from BM25.BM25Engine import BM25Engine
from BM25.database import getCategoriesPath, getProductByCategory
from BM25.utils import getAVGDocLength

from SementicSearch.SementicEngine import SementicEngine
from Hybrid.fusion import reciprocal_rank_fusion

from NER.entity_extractor import EntityExtractor
from NER.utils import normalize
from LLM.LLM import query_gemini

def perform_search(user_query_str: str):
    # ============================================================================
    # Query Normalization & Expansion
    # ============================================================================
    extractor = EntityExtractor()
    normalized_query = extractor.extract(user_query_str)
    
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
    llm_results = query_gemini(
        user_query=user_query_str,
        ner_entities=ner_entities,
        category_dictionaries=category_snippets,
        price_constraints=price_constraints
    )

    price_min = llm_results.get("price", {}).get("min_price")
    price_max = llm_results.get("price", {}).get("max_price")
    selected_category_id = llm_results.get("selected_category_id")

    if not selected_category_id:
        # Fallback to the first category if the LLM fails to return one
        print("[WARN] LLM failed to return a selected_category_id, logging fallback.")
        selected_category_id = top_category_paths_results[0]["document"]["category_id"]

    print(f"[Price Filter] {f'${price_min} - ${price_max}' if price_min or price_max else 'No price filter'}")
    print(f"[Selected Category ID] {selected_category_id}\n")

    # Extract search queries for downstream engines
    bm25_search_query = " ".join(llm_results.get("bm25_keywords", []))
    if not bm25_search_query.strip():
        bm25_search_query = user_query_str

    semantic_search_query = llm_results.get("semantic_blob", user_query_str)
    
    # Generate embedding for the semantic query downstream using the existing embed logic
    from SementicSearch.utils import embed
    from SementicSearch.SementicEngine import MODEL, DIMS
    query_embedding = embed(semantic_search_query, MODEL, DIMS)

    # Stage 2.5: Fetch products pushed entirely to PGVector using Cosine Distance (`<=>`)
    print(f"\n[Fetching Products] Fetching top products efficiently strictly using pgvector for Category ID: {selected_category_id}")
    try:
        product_docs = getProductByCategory(
            selected_category_id,
            price_min=price_min,
            price_max=price_max,
            query_embedding=query_embedding,
            limit=200
        )
    except Exception as exc:
        print(f"    [ERROR] Failed to fetch products for selected category {selected_category_id}: {exc}")
        return {"error": f"Database fetch error: {exc}"}

    if not product_docs:
        print(f"\nNo products found in the selected category with price range {price_min}-{price_max}")
        return {"results": [], "message": "No products met constraints"}

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

    return {"results": rrf_results}

if __name__ == '__main__':
    user_q = normalize("i want a good machine for playing under 3000dt")
    perform_search(user_q)
