# PFA_BM25: Advanced Hybrid E-Commerce Search Pipeline

An enterprise-grade hybrid search engine that fuses Lexical Search (BM25), Semantic Search (pgvector + Dense Vectors), and Generative AI (LLM-based Query Expansion) to deliver exact-match precision and deep contextual understanding.

## 🏗 Architecture / Search Pipeline

The search pipeline is orchestrated in `main.py` and operates in 6 distinct stages:

1. **Query Normalization & NER**: Extracts entities (brand, model, spec) from the raw user query using GLiNER.
2. **Category Candidate Retrieval**: Uses Semantic Search to fetch the top 3 most relevant category paths from the database based on the user's intent.
3. **LLM Query Expansion (HyDE)**: Passes the intent, entities, and candidate categories to **Google Gemini**. Gemini isolates the single best category ID, parses strict price constraints, generates technical BM25 keywords, and writes a "Hypothetical Document Embeddings" (HyDE) semantic formulation.
4. **Database-Native Semantic Search (`pgvector`)**: Fetches the top 200 products via a PostgreSQL query heavily optimized with the `<=>` cosine distance operator against the semantic blob, strictly applying the LLM-parsed price bounds and category ID.
5. **Lexical Re-ranking (BM25)**: Evaluates the fetched top 200 semantic candidates using `rank_bm25` (a C-optimized BM25Okapi implementation) to ensure critical specifications and keywords are strictly matched.
6. **Reciprocal Rank Fusion (RRF)**: Intelligently merges the DB-native semantic rank and the BM25 score into a single, highly accurate hybrid scoring list using lightning-fast $O(1)$ Hash Map lookups.

## 🛠️ Technology Stack

- **Python 3.10+** (managed via `uv`)
- **PostgreSQL + pgvector** (Blazing fast in-database cosine distance operations)
- **Google GenAI API (Gemini)** (Query expansion, intent parsing, strict JSON via Pydantic)
- **GLiNER** (Zero-shot Named Entity Recognition)
- **Sentence-Transformers** (HuggingFace `all-MiniLM-L6-v2` for generating embeddings)
- **rank-bm25** (Highly optimized BM25 lexical ranking algorithm)
- **Pydantic** (Strict schema validation for AI outputs to prevent hallucinations/crashes)

## 🚀 Setup & Installation

1. **Install dependencies using uv:**
   ```bash
   uv sync
   ```

2. **Activate the virtual environment:**
   ```bash
   source .venv/bin/activate
   ```

3. **Configure Environment:** 
   Ensure your `.env` file is properly configured:
   ```env
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=postgres
   API_KEY=your_gemini_api_key
   LLM_MODEL=gemini-2.5-flash
   MODEL=all-MiniLM-L6-v2
   DIMS=384
   ```

## 💻 Usage

Run the main pipeline script. The search logic safely handles LLM rate limits and translates directly to web API architectures.

```bash
uv run main.py
```

## 📂 Project Structure

- **`main.py`**: The core orchestrator managing the 6-stage pipeline natively and safely.
- **`BM25/`**: `BM25Engine.py` (Lexical scoring via rank_bm25) & `database.py` (PostgreSQL connections & pgvector logic).
- **`LLM/`**: `LLM.py` (Gemini API integration with Exponential Backoff and Pydantic schema constraints).
- **`NER/`**: Entity extraction and query normalization using GLiNER.
- **`SementicSearch/`**: In-memory dense vector operations, SentenceTransformer embeddings, and local utility handlers.
- **`Hybrid/`**: High-performance Reciprocal Rank Fusion implementation (`fusion.py`).
