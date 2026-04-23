# Deep Technical Audit: Proposed Architecture vs. Codebase Reality

This document provides a comprehensive audit of the proposed `architecture_plan.md` against the actual source code present in the `gateway_node`, `ranker_node`, and `scraper_node` directories. 

The goal of this audit is to validate the feasibility of the proposed plan, identify technical debt, and pinpoint the exact files that require modification during the execution phases.

## 1. Architectural Alignment Assessment

The overall microservices architecture (Gateway -> Redis -> Celery Workers) is implemented cleanly. The proposed implementation plan aligns **perfectly** with the current system constraints. 

### Gateway Node Validation (`gateway_node`)
- **Current State**: The `gateway_node` handles Authentication, Proxying, and WebSockets flawlessly using FastAPI and `asyncpg`. 
- **Audit Finding**: The authentication logic currently hardcodes checking the `users` and `admins` tables separately (e.g., in `auth/router.py` and `routers/users.py`).
- **Confirmation of Plan (Phase 1)**: The plan to introduce a `business_owner` role is highly viable. We will need to update the `auth` models and the JWT `decode_token` logic in `core/security.py` to recognize the `business` scope natively.

### Ranker Node Validation (`ranker_node`)
- **Current State**: `Search.py` executes a complex, well-structured Hybrid Search pipeline: Query Normalization -> Category Semantic Search -> LLM Parsing -> pgvector Product Fetch (`getProductByCategory`) -> BM25 Reranking -> RRF Fusion.
- **Audit Finding**: The Ranker is natively querying PostgreSQL for embeddings and relational data. 
- **Confirmation of Plan (Phase 3)**: Implementing source filtration (`client_post`, `business_shop`) is straightforward. We only need to modify the SQL payload inside `BM25/database.py:getProductByCategory` to accept a `source_type` parameter, which the LLM or frontend filters can supply.

## 2. Critical Findings & Technical Debt

> [!WARNING]
> The audit uncovered two significant pieces of technical debt that must be addressed during Phase 2 to ensure system stability.

### Technical Debt 1: Tightly Coupled & Incomplete ETL Logic
In `scraper_node/scraper.py`, the `runScrapers()` Celery task is monolithic. It manually invokes `TunisianetScraper` and `MyTekScraper`, and if successful, immediately runs the normalization and database injection (`enrichProductsWithCategoryIds` and `saveProductsToDB`). 
- **The Issue (Coupling)**: Because they are baked into one function, we cannot reuse the "Enrichment & DB injection" logic independently when a Client or Business Owner uploads a single product manually.
- **The Issue (Missing Logic - The Dictionary Field)**: The crucial step of interpreting the scraped unstructured content via an LLM and populating the **"dictionary"** field (used for semantic query expansion and categorization) is currently **not implemented**. 
- **The Fix**: We must extract lines 64-70 in `scraper.py` into a separate, callable Celery task (e.g., `process_and_load_products(product_list, source_type)`). This new task must be expanded to include the missing LLM-call that dynamically generates and fills the product's dictionary metadata before pgvector embedding and DB insertion.

### Technical Debt 2: FAISS vs. pgvector Divergence
- **The Issue**: The `ranker_node` is correctly utilizing PostgreSQL (via `pgvector`) to fetch semantically similar products dynamically. However, the `scraper_node` contains a `vectors.py` script and a `retrieve.py` script that builds and queries a standalone **FAISS index** on disk (`index.faiss`).
- **The Audit Conclusion**: The FAISS implementation in the `scraper_node` appears to be legacy code or an alternative pathway that is no longer aligned with the primary `ranker_node` architecture. To prevent data desynchronization (where the DB has data but the FAISS index does not, or vice-versa), the standalone FAISS code should be deprecated, ensuring all embeddings live solely inside PostgreSQL.

## 3. Specific File Integration Points

When executing the `task.md` checklist, the following files will be the primary targets for modification:

| Phase | Target File | Required Action |
| :--- | :--- | :--- |
| **Phase 1** | `gateway_node/auth/router.py` | Add `/business/register` endpoint handling `AccountRequest` logic. |
| **Phase 1** | `gateway_node/core/security.py` | Validate new `business` JWT role assignment. |
| **Phase 2** | `scraper_node/scraper.py` | Refactor `runScrapers` to call a dedicated transform/load function. |
| **Phase 2** | `gateway_node/routers/etl.py` | Add endpoint `/ingest/manual` for Gateway to send Client/Biz products to the decoupled loader. |
| **Phase 3** | `ranker_node/BM25/database.py` | Update `getProductByCategory` to accept `source_type_filter`. |
| **Phase 4** | `gateway_node/docker-compose.yml` | Attach the Cube.js Docker image and configure it to read from PostgreSQL. |

## 4. Final Verdict

The proposed architecture is structurally sound, and the codebase is mature enough to support the new features without requiring a total rewrite. 

The primary friction point will be normalizing the ETL pipeline (Phase 2) to treat manual user uploads and automated scrapes as identical data structures before they hit the database. Once that decoupling is achieved, the rest of the features (Client ad-boards, Business Dashboards) are fundamentally standard CRUD operations sitting alongside the advanced AI pipeline.
