import numpy as np
from sentence_transformers import SentenceTransformer
from SementicSearch.utils import embed, load_and_generate_embeddings, print_embedding_stats
from dotenv import load_dotenv
import os

dotenv = load_dotenv()

# Initialize the all-MiniLM model
print("[Semantic] Loading all-MiniLM-L6-v2 model...")
MODEL = SentenceTransformer(os.getenv("MODEL") or "all-MiniLM-L6-v2")
print("[Semantic] Model loaded successfully.")
dims_env = os.getenv("DIMS")
DIMS = int(dims_env) if dims_env is not None else 384

class SementicEngine:
    
    def __init__(self, documents, text_key="search_text", generate_missing=True):
        """
        Initialize Semantic Engine with pgvector embeddings support.
        
        Args:
            documents: List of documents with pgvector embeddings
            text_key: Field name for document text (for on-the-fly embedding generation)
            generate_missing: Whether to generate embeddings for documents without them
        """
        self.documents = documents
        self.text_key = text_key
        
        # Load or generate embeddings for all documents
        self.embeddings, counts_dict = load_and_generate_embeddings(
            self.documents, 
            MODEL, 
            DIMS, 
            text_key=self.text_key, 
            generate_missing=generate_missing
        )
        
        # Process and store as continuous matrix
        self.embeddings = np.array(self.embeddings, dtype=np.float32)
        
        # Print embedding statistics
        print_embedding_stats(counts_dict)
    
    def search(self, query: str):
        """Search documents using semantic similarity."""
        query_embedding = embed(query, MODEL, DIMS)
        query_embedding = np.array(query_embedding, dtype=np.float32)
        
        # Vectorized cosine similarity
        doc_norms = np.linalg.norm(self.embeddings, axis=1)
        query_norm = np.linalg.norm(query_embedding)
        
        # Avoid division by zero
        doc_norms = np.where(doc_norms == 0, 1.0, doc_norms)
        if query_norm == 0:
            query_norm = np.float32(1.0)
            
        scores = np.dot(self.embeddings, query_embedding) / (doc_norms * query_norm)
        
        ranked_indices = np.argsort(scores)[::-1]
        return [{"score": float(scores[idx]), "document": self.documents[idx]} for idx in ranked_indices]

