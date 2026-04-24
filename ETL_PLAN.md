## Plan: ETL Pipeline Rebuild

Deliver a stage-based ETL pipeline for scraper_node with clear contracts, progress reporting, and control-plane integration, while keeping current scraping functionality stable. The approach is to formalize each stage (scrape, dedup, normalize, chunk, embed, persist), wire the pipeline runner into the Celery task, and add structured progress + metrics so the gateway/admin UI can track each stage.

**Steps**
1. Define ETL contracts and stage interfaces using the existing scaffolding in scraper_node/src/etl to ensure each stage receives and returns a PipelineContext with data and metadata. *depends on none*
2. Implement control-plane hooks: integrate Redis control checks between stages and standardize progress payloads (state, message, stage, counters, timestamps). *depends on 1*
3. Implement stage logic:
   - Scrape stage wraps the current MyTek/Tunisianet scraping and produces raw product records.
   - Dedup stage introduces deterministic fingerprinting (source + normalized name + URL) and removes duplicates.
   - Normalize stage cleans fields, applies category normalization, and standardizes price/brand fields.
   - Chunk stage creates summary/feature chunks (or no-op with placeholders if not needed yet).
   - Embed stage generates or prepares embeddings (via existing saveProductsToDB or separate embedding builder).
   - Persist stage handles DB writes + JSON snapshot and emits final summary.
   *depends on 1*
4. Wire run_pipeline into scraper_node/scraper.py, replacing the monolithic flow with ordered stage execution while preserving current output and side effects. *depends on 2, 3*
5. Update scraper_node/main.py to include stage-level progress in websocket broadcasts and status endpoints for UI visibility. *depends on 2, 4*
6. Add minimal tests or smoke checks for each stage contract and pipeline orchestration, focusing on shape validation and control-state enforcement. *depends on 3, 4*

**Relevant files**
- /home/mortadha/Documents/PFA_Working_DIR/PFA/scraper_node/scraper.py — replace monolithic flow with stage runner and control hooks
- /home/mortadha/Documents/PFA_Working_DIR/PFA/scraper_node/main.py — expand status/progress reporting with stage metadata
- /home/mortadha/Documents/PFA_Working_DIR/PFA/scraper_node/src/etl/pipeline.py — orchestrate stage sequence
- /home/mortadha/Documents/PFA_Working_DIR/PFA/scraper_node/src/etl/contracts.py — define PipelineContext shape and stage metadata fields
- /home/mortadha/Documents/PFA_Working_DIR/PFA/scraper_node/src/etl/stages/*.py — implement stage logic
- /home/mortadha/Documents/PFA_Working_DIR/PFA/scraper_node/src/core/control.py — Redis control keys and helper checks

**Verification**
1. Run scraper locally, observe stage-by-stage progress messages and final status payload shape in /scrape/status and WS.
2. Trigger pause/resume mid-pipeline and confirm stage transitions respect the control state.
3. Validate that DB persistence still occurs and product counts match previous runs.

**Decisions**
- Keep current scrapers and DB persistence intact while refactoring into explicit pipeline stages.
- Emit stage-level progress in Redis Pub/Sub for admin UI and observability.

**Further Considerations**
1. Dedup fingerprint scheme: URL-based vs. normalized name + source. Recommendation: composite fingerprint with source + normalized name + normalized URL.
2. Embedding placement: compute embeddings in persist stage vs. dedicated embed stage. Recommendation: dedicated embed stage to allow future vector-store expansion.
3. Chunking: no-op for now vs. precompute feature chunks for summarization. Recommendation: implement placeholder chunk stage with clear extension points.

---

## Report: What’s Missing + What Will Be Added

**Missing right now**
- No explicit stage boundaries (pipeline is still monolithic in the task).
- No dedup stage or fingerprinting.
- Normalization exists but is scattered, not enforced as a stage.
- Chunking is not defined.
- Embedding is mixed into DB persistence, not a separable stage.
- No stage-level progress metrics in admin status.

**Will be added**
- A formal PipelineContext with data + meta shared across stages.
- A defined stage order (scrape → dedup → normalize → chunk → embed → persist).
- Stage-level progress events (state, stage name, counts, timestamps).
- Deterministic dedup with fingerprint strategy.
- Clear extension points for chunking + embeddings.

**How it will be added**
- Refactor runScrapers() to call the new pipeline runner.
- Implement each stage in scraper_node/src/etl/stages/.
- Emit consistent progress and status updates through Redis pub/sub.
