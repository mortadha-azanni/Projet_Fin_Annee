# PFA Architecture Implementation Checklist

This task list serves as a roadmap to execute the newly defined system architecture for the PFA project.

## Phase 1: Database Schema & Authentication Gateway
- [ ] Add `business_owner` capabilities and `AccountRequest` tables for Admin approvals in the database schema.
- [ ] Refactor JWT generation and validation to support specific scopes (`user`, `business`, `admin`).
- [ ] Scaffold the basic React UI shell for **Client Product Posting**.
- [ ] Scaffold the basic React UI shell for **Business Dashboard**.

## Phase 2: Unifying the ETL Pipeline
- [ ] Decouple the embedding/normalization formatting from `scraper_node` into a shared utility function/module.
- [ ] **Implement the missing LLM-based parsing step inside the ETL utility to correctly populate the `dictionary` field for semantic expansion.**
- [ ] Update `scraper.py` to use the decoupled ETL utility.
- [ ] Create a new endpoint in `gateway_node` to trigger synchronous or asynchronous embeddings for manual product additions (Client C2C and Business CRUD).
- [ ] Update PostgreSQL product schemas to include `source_type` (`scraped`, `business_shop`, `client_post`).

## Phase 3: Ranker Context Expansion
- [ ] Update BM25 and pgvector queries in `Search.py` to allow filtering by `source_type`.
- [ ] Connect frontend search controls (checkboxes) to the new filtering parameters in the `/search` API endpoint.
- [ ] Ensure Reciprocal Rank Fusion (RRF) algorithm correctly handles the new parameters.

## Phase 4: Componentizing the BI Layer (Cube.js)
- [ ] Deploy or configure Cube.js instance attached to the PostgreSQL database.
- [ ] Define the Semantic Layer (Schemas & Cubes) for the overall cluster data.
- [ ] Implement Row-Level Security (RLS) in the Data Schemas to scope BI data to a specific `shop_id`.
- [ ] Build BI Frontend views using Cube.js client libraries or via standard REST calls in the React Application.
