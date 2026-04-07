import numpy as np

def _encode(text_or_texts, MODEL):
    """Compatibility wrapper for sentence-transformers encode kwargs across versions."""
    try:
        return MODEL.encode(text_or_texts, convert_to_numpy=True, show_progress_bar=False)
    except TypeError:
        # Older/newer variants may expose a different progress keyword.
        return MODEL.encode(text_or_texts, convert_to_numpy=True)

def embed(text: str, MODEL, DIMS: int) -> np.ndarray:
    """
    Produce embedding using all-MiniLM-L6-v2.
    
    Args:
        text: The text to embed.
        MODEL: SentenceTransformer model instance
        DIMS: Expected embedding dimension (usually 384)
        
    Returns:
        A DIMS-dimensional numpy array representing the semantic embedding.
    """
    if not text or not text.strip():
        return np.zeros(DIMS, dtype=np.float32)

    embedding = _encode(text, MODEL)
    return np.array(embedding, dtype=np.float32)


def generate_missing_embeddings(documents, embeddings_list, missing_indices, MODEL, DIMS, text_key="search_text"):
    """
    Generate embeddings on-the-fly for documents that don't have them.
    
    Args:
        documents: List of all documents
        embeddings_list: List of embeddings (with None for missing ones)
        missing_indices: Indices of documents with missing embeddings
        MODEL: SentenceTransformer model instance
        DIMS: Embedding dimension
        text_key: Key in document dict to use for generating embedding
        
    Returns:
        Updated embeddings_list with generated embeddings filled in
    """
    if not missing_indices:
        return embeddings_list
    
    print(f"[Semantic] Generating embeddings for {len(missing_indices)} documents...")
    
    # Batch encode all missing texts for efficiency
    texts_to_encode = []
    idx_mapping = []
    
    for idx in missing_indices:
        doc = documents[idx]
        text = doc.get(text_key, "")
        if text and text.strip():
            texts_to_encode.append(text)
            idx_mapping.append(idx)
    
    if texts_to_encode:
        # Batch encode for efficiency
        generated_embeddings = _encode(texts_to_encode, MODEL)
        
        # Fill in the embeddings
        for i, original_idx in enumerate(idx_mapping):
            if isinstance(generated_embeddings, np.ndarray) and generated_embeddings.ndim > 1:
                embeddings_list[original_idx] = np.array(generated_embeddings[i], dtype=np.float32)
            else:
                embeddings_list[original_idx] = np.array(generated_embeddings, dtype=np.float32)
    
    print(f"[Semantic] Generated {len(idx_mapping)} embeddings")
    return embeddings_list
def load_and_generate_embeddings(documents, MODEL, DIMS, text_key="search_text", generate_missing=True):
    """Load pgvector embeddings or generate them on-the-fly if missing."""
    import json
    embeddings_list = []
    missing_indices = []
    counts_dict = {"total": len(documents), "with_embedding": 0, "generated": 0, "zero_vector": 0}
    
    for idx, doc in enumerate(documents):
        embedding = doc.get("embedding")
        
        # Handle stringified embeddings from PostgreSQL
        if isinstance(embedding, str):
            try:
                embedding = json.loads(embedding)
            except Exception:
                embedding = None
        
        # pgvector from DB comes as list/array, not string
        if embedding is not None and len(embedding) == DIMS:
            # Valid pgvector embedding
            embeddings_list.append(np.array(embedding, dtype=np.float32))
            counts_dict["with_embedding"] += 1
        else:
            # Missing or invalid embedding
            missing_indices.append(idx)
            if generate_missing and text_key in doc and doc[text_key]:
                # Placeholder will be replaced with actual embeddings
                embeddings_list.append(None)
            else:
                # Use zero vector as fallback
                embeddings_list.append(np.zeros(DIMS, dtype=np.float32))
                counts_dict["zero_vector"] += 1
    
    # Generate embeddings for missing ones if requested
    if generate_missing and missing_indices:
        embeddings_list = generate_missing_embeddings(
            documents,
            embeddings_list,
            missing_indices,
            MODEL,
            DIMS,
            text_key=text_key
        )
        counts_dict["generated"] = len(missing_indices)
    
    # Store as a neat 2D matrix
    return np.array(embeddings_list, dtype=np.float32), counts_dict

def print_embedding_stats(counts_dict):
    """Print embedding statistics for debugging."""
    total = counts_dict.get("total", 0)
    with_emb = counts_dict.get("with_embedding", 0)
    generated = counts_dict.get("generated", 0)
    zero = counts_dict.get("zero_vector", 0)
    
    print(f"[Semantic] Embedding Statistics:")
    print(f"  Total documents: {total}")
    print(f"  From pgvector: {with_emb}")
    print(f"  Generated on-the-fly: {generated}")
    print(f"  Using zero vectors: {zero}")
