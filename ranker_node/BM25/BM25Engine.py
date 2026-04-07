from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]

class BM25Engine:
    def __init__(self, documents, k1=1.5, b=0.75, avg_doc_length=100, text_key="name"):
        self.documents = documents
        self.text_key = text_key
        
        # Extract and pre-tokenize documents using standard split (or any custom tokenizer)
        tokenized_corpus = []
        for doc in self.documents:
            doc_text = doc.get(self.text_key, '')
            tokens = doc_text.lower().split() if doc_text else []
            tokenized_corpus.append(tokens)
            
        # Initialize C-optimized Okapi BM25 implementation from rank-bm25
        self.bm25 = BM25Okapi(tokenized_corpus, k1=k1, b=b)
    
    def search(self, query, top_k=5):
        query_terms = query.lower().split()
        
        # Automatically score all documents via vectorized lookup
        scores = self.bm25.get_scores(query_terms)
        
        # Attach scores to documents
        results = [{"score": float(scores[i]), "document": doc} for i, doc in enumerate(self.documents)]
            
        # Sort documents by score and return top_k results
        results.sort(reverse=True, key=lambda x: x["score"])
        return results[:top_k]

    


