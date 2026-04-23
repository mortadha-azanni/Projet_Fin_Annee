# Comprehensive Task Checklist (Pipeline Alignment)

Based on the newly established 12-Stage `CHAT_FLOWCHART.md`, the platform roadmap has been thoroughly restructured to enforce the new pipeline.

## Phase 1: Real-Time Foundation (Stages 0, 1, 2, 11, 12)
- [ ] **NGINX Setup**: Implement rate limiting and WSS upgrade routing (Stage 1).
- [ ] **WS Auth & Mapping**: Update `gateway_node` to handle JWT checking on WS handshake and reject invalid tokens (Stage 2).
- [ ] **Redis Registration**: Track user-socket mapping and conversation sessions reliably in Redis (Stage 2).
- [ ] **Pub/Sub Delivery System**: Build universal Redis pub/sub listener in `gateway_node` to push Ranker/LLM outputs directly to subscribed clients (Stage 11).
- [ ] **Offline Storage Fallback**: If a WS disconnects mid-processing, store the response in Redis for delivery upon reconnect (Stage 11).

## Phase 2: Context & Intent Routing (Stages 3, 4)
- [ ] **Session & History Manager**: Build `session_manager.py` to load Postgres/Redis conversation context dynamically (Stage 3).
- [ ] **Context Summarization**: Implement LLM-based truncation/summarization when context tokens exceed limits (Stage 3).
- [ ] **Advanced LLM Classifier**: Refactor `LLM_Judje/main.py` to detect nuanced intents (`chitchat`, `clarify`, `comparison`, `constrained`, `search`) and extract constraints natively (Stage 4).
- [ ] **Direct Replies**: Configure routing so `chitchat` and `clarify` intents bypass the Ranker entirely and publish directly back to the client via Redis (Stage 4).

## Phase 3: Enrichment & Search Core (Stages 5, 6, 7)
- [ ] **Semantic Cache Layer**: Implement SHA-256 caching of queries + constraints in Redis to intercept identical searches before hitting the NER/Ranker (Stage 5).
- [ ] **NER & Query Expansion**: Set up a semantic pipeline (e.g., spaCy) to extract constraints (price, location, brands) and expand semantic synonyms (Stage 6).
- [ ] **Hybrid Search Execution**: Implement parallel execution of Vector Search (pgvector) and Keyword Search (Postgres FTS) (Stage 7).
- [ ] **Reciprocal Rank Fusion**: Combine both parallel search results and apply hard constraint filters and tenant-level isolation filters (Stage 7).
- [ ] **Fallback Relaxer**: If constraints yield 0 results, implement an automatic constraint drop/relax strategy before giving up entirely (Stage 7).

## Phase 4: Re-Ranking & Synthesis (Stages 8, 9, 10)
- [ ] **Cross-Encoder Re-Ranking**: Implement a discrete Cross-Encoder step to fine-tune the combined RRF results for ultimate relevancy (Stage 8).
- [ ] **Diversity Filter**: Enforce limits to prevent an overwhelming sequence of items from identical sellers/sources (Stage 8).
- [ ] **Synthesis Router**: Setup LLM response builder to output specific formats (lists, comparison tables, short constrained sets) based on the Classifier's identified mode (Stage 9).
- [ ] **Streaming Generator**: Enable LLM streaming chunks back to the client via the Redis Pub/Sub tunnel (Stage 9).
- [ ] **Cache Persistence**: Ensure the final results and user turns are logged into Postgres and updated in Redis cache for the next query (Stage 10).

## Phase 5: Observability & Unification (Cross-cutting)
- [ ] **ETL Unification (Legacy Requirement)**: Ensure the ETL pipeline correctly supports `scraped`, `client_post`, and `business_shop` entries to populate pgvector correctly.
- [ ] **OpenTelemetry**: Integrate OpenTelemetry spans into Gateway, Classifier, and Ranker tracing Latency, Token Counts, Cache Hit/Miss, and Intent class (Obs).
- [ ] **Grafana Dashboard**: Connect OTel collector to Grafana for live monitoring.
