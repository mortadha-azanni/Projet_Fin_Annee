# PFA Distributed E-commerce Platform: Architecture & Implementation Plan

This document serves as the high-level roadmap and architectural synthesis for the completion of the PFA Distributed E-commerce Platform. It incorporates the existing microservices architecture while designing the pathways to integrate the newly requested `business_owner`, `client`-posting functions, and enhancements to the **ETL**, **Ranker**, and **BI** modules.

---

## 1. System Architecture (Mermaid Diagram)

```mermaid
flowchart TD
    %% Define User Personas
    Admin((Admin/Superuser))
    SysClient((Client))
    BizOwner((Business Owner))

    %% Frontend App
    subgraph Frontend [React / Vite Frontend (SEARCHILY)]
        ChatUI[Chat & Search Interface]
        AdminDash[Admin Dashboard]
        BizDash[Business Dashboard - Shop & CRUD]
        ClientPost[Client Post UI]
        BIDash[BI Dashboards]
    end

    %% API Gateway Layer
    subgraph Gateway [Gateway Node :8000]
        AuthProxy[Auth / Proxy Manager]
        WSChat[WebSocket Chat]
        ApprovalFlow[Business Approval / Registration]
    end

    %% Search and Ranking Pipeline
    subgraph Ranker [Ranker Node]
        RankerWorker[Celery Ranker Worker]
        Hybrid[Hybrid Search Engine]
        LLMSynth[LLM Result Synthesis]
        NER[NER & Query Intent]
    end

    %% Data Acquisition / ETL
    subgraph ETL [Scraper Node / Unified ETL Pipeline]
        ScraperWorker[Celery ETL Worker]
        AutoScraper[Web Automation / Scraper]
        ManualIngestion[Manual Upload Ingestion Process]
        Embeddings[Vector Embedding / Normalization]
    end

    %% BI Layer
    subgraph BI [Business Intelligence]
        CubeJS[Semantic Layer / BI Engine]
    end

    %% Data Stores
    subgraph Databases [Data Persistence]
        Redis[(Redis - Task Queue / Cache)]
        Postgres[(PostgreSQL + pgvector)]
    end

    %% Connections
    SysClient --> ChatUI
    SysClient --> ClientPost
    BizOwner --> BizDash
    Admin --> AdminDash
    BizOwner & Admin --> BIDash

    Frontend -->|HTTP/REST| Gateway
    Frontend -->|WebSocket| Gateway

    AuthProxy -->|Async Jobs / Tasks| Redis
    WSChat -->|Poll Status| Redis

    Redis <--> RankerWorker
    Redis <--> ScraperWorker

    RankerWorker --> Hybrid
    Hybrid --> LLMSynth
    LLMSynth --> Postgres

    ScraperWorker --> AutoScraper
    ScraperWorker --> ManualIngestion
    AutoScraper --> Embeddings
    ManualIngestion --> Embeddings
    Embeddings --> Postgres

    CubeJS --> Postgres
    BIDash --> CubeJS
```

---

## 2. Current State vs. Future State Analysis

### 2.1. What is DONE (Current State)
- **Containerized Network Layer**: Gateway handling Auth/Proxy, Scraper, and Ranker as separate processes. 
- **Asynchronous Task Queue**: Celery & Redis are in place orchestrating background jobs without blocking the main event loops.
- **Data Ingestion (External)**: Baseline ETL processes fetching data from specific predefined commercial domains (e.g., Tunisianet, Mytek) via `scraper_node`.
- **Retrieval System**: A hybrid search process (BM25 + Vector Semantic Search) operating on `ranker_node`.
- **Frontend Skeleton**: Chatbot surface and standard admin controls available. 

### 2.2. What Needs to be ADDED (New Work)
- **Role-Based Access Control (RBAC) Expansion**:
  - `business_owner` Role: Standard users that request an enterprise tier.
  - `Admin` Business Control: Verification logic where Admin reviews, accepts, or rejects potential Business Owners.
- **Business Owner Ecosystem**:
  - A 2-page localized dashboard targeting only the owner's metrics.
  - An isolated "Shop" management view providing CRUD operations so they can manage their own product listings.
- **Client C2C Listings**: 
  - A new React page for standard `client` users to upload/sell a single product to the platform. This function operates as an **ad-board** (classifieds style) where buyers contact the seller directly, without on-platform financial checkout flows.
- **Headless BI Subsystem**: 
  - Incorporating a BI aggregator to pipe metrics back to the Admin and Business Owner dashboards cleanly.

### 2.3. What Needs to be REFINED & FIXED
- **Unified ETL Endpoint (Manual vs. Scraped data)**: Currently, the ETL is optimized for scraping. It needs to be refactored so that "Scraped Products," "Business Owner CRUD Products," and "Client Uploaded Products" all pass through the same normalizing and embedding stages before hitting PostgreSQL.
- **Ranker Filtration**: The search algorithm needs tuning to differentiate between C2C (Client) products, Commercial (Scraped) products, and Business Owner stores natively based on filters or metadata.

---

## 3. Deep Dive: Modifying ETL, RANKER, and BI

### 3.1. ETL (Extract, Transform, Load) Modification
**Current**: Primarily automates scraping from predefined URLs and dumps it into the database.
**Modification Required**: 
- We must convert the "Transform & Load" phases of the ETL into a reusable, standalone Celery task.
- When the `AutoScraper` fetches 1,000 products, it passes them to this module.
- When a `client` posts 1 product, the Gateway submits it directly to this same module.
- When a `business_owner` performs a Bulk Upload or CRUD operation, the changes trigger this module.
- **The unified Transform & Load step will**:
  1. Validate fields.
  2. Map to the global taxonomy via LLM.
  3. Generate pgvector embeddings.
  4. Upsert to the PostgreSQL database with correct `source_type` (`scraped`, `business_shop`, or `client_post`).

### 3.2. RANKER Modification
**Current**: Performs vector search, BM25, and uses an LLM to synthesize final chat answers based on queried features.
**Modification Required**:
- **Source Filtering**: Incorporate pre-filtering in the hybrid search (PostgreSQL where-clauses) that respects what the user is looking for. For instance, if a user wants "used items," prioritize `source_type = client_post`.
- **Data Governance**: Ensure that if a business owner deletes or hides an item via their CRUD dashboard, the Ranker instantly ignores those vectors.
- **Metadata Weighting (RRF)**: Implement Reciprocal Rank Fusion tweaks to prioritize verified `business_owner` listings slightly higher than anonymous `client_post` listings when matching relevance is identical.

### 3.3. BI (Business Intelligence) Architecture
**Current**: Non-existent or tightly coupled crude counts in the Gateway.
**Implementation Plan**:
- Deploy a semantic BI engine (**Cube.js** will be utilized as a dedicated microservice). 
- **Admin View**: The Cube.js instance aggregates total requests, system latency, scraping volume, and absolute sales/click data spanning the whole cluster.
- **Business Owner View (2-Page Dashboard)**: Implement Row-Level Security (RLS) in the Cube.js data schemas. The `business_owner` queries the BI engine but receives ONLY interactions, views, and data related to their specific `shop_id`.
- Connect the frontend `my-react-app` directly to the BI REST/GraphQL API using dedicated graphical libraries (like Recharts).

---

## 4. Work Execution Roadmap (Next Steps)

1. **Phase 1: Database Schema & Authentication Gateway**
   - Implement `AccountRequest` tables for Admin approvals.
   - Refactor JWT mapping to accept scopes: `user`, `business`, `admin`.
   - Setup basic UI shell for Client Product Posting and Business Dashboard.

2. **Phase 2: Unifying the ETL Pipeline**
   - Extract the formatting/embedding logic from `scraper_node` into a decoupled shared utility.
   - Allow `gateway_node` to trigger partial embed/index Celery tasks for real-time Client and Business CRUD modifications.

3. **Phase 3: Ranker Context Expansion**
   - Modify BM25 and Vector SQL queries to apply Hard-Filters by user-supplied checkboxes (e.g., "Show local sellers only").

4. **Phase 4: Componentizing the BI Layer**
   - Connect the BI semantic layer.
   - Design metrics definitions for Business Owners.
   - Feed metrics into the frontend dashboard views.


