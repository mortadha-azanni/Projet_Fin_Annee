def reciprocal_rank_fusion(bm25_results, semantic_results, k=60):
    """
    Combine BM25 and Semantic results using Reciprocal Rank Fusion (RRF).
    Formula: RRF(d) = Σ (1 / (k + rank(d)))
    
    Args:
        bm25_results: List of BM25 results with scores and document
        semantic_results: List of semantic results with scores and document
        k: RRF parameter (default 60)
        
    Returns:
        List of fused results sorted by RRF score
    """
    rrf_scores = {}
    doc_metadata = {}
    bm25_scores = {}
    semantic_scores = {}
    
    # Add BM25 scores
    for rank, result in enumerate(bm25_results, 1):
        doc = result["document"]
        doc_id = doc.get("id")
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank)
        doc_metadata[doc_id] = doc
        bm25_scores[doc_id] = result["score"]
    
    # Add Semantic scores
    for rank, result in enumerate(semantic_results, 1):
        doc = result["document"]
        doc_id = doc.get("id")
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank)
        doc_metadata[doc_id] = doc
        semantic_scores[doc_id] = result["score"]
    
    # Create combined results ordered by RRF score
    combined_results = []
    
    # Sort descending by RRF score using items
    for doc_id, rrf_score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
        combined_results.append({
            "document": doc_metadata[doc_id],
            "rrf_score": rrf_score,
            "bm25_score": bm25_scores.get(doc_id, 0.0),
            "semantic_score": semantic_scores.get(doc_id, 0.0)
        })
    
    return combined_results
