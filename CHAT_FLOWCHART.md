'''
flowchart TD

    %% ─────────────────────────────────────────
    %%  STAGE 0 — CLIENT SIDE
    %% ─────────────────────────────────────────
    subgraph CLIENT ["💬 Stage 0 — Client Side"]
        UserTypes["User Types Message\nin ChatUI"]
        WSExists{"Active WebSocket\nConnection?"}
        WSHandshake["Initiate WSS Handshake\n+ send JWT in header"]
        WSReuse["Reuse Existing\nWS Connection"]
        SendPayload["Send Message Payload\n{ message, session_id,\n  conversation_id, timestamp }"]
    end

    %% ─────────────────────────────────────────
    %%  STAGE 1 — NGINX
    %% ─────────────────────────────────────────
    subgraph NGINX_STAGE ["① NGINX — Stage 1"]
        RateCheck{"Rate Limit\n Exceeded?"}
        RateReject["❌ 429 Too Many Requests\n Return to Client"]
        WSUpgrade["WebSocket Upgrade\n HTTP → WSS"]
        RouteGW["Route to\n Gateway Instance"]
    end

    %% ─────────────────────────────────────────
    %%  STAGE 2 — GATEWAY AUTH
    %% ─────────────────────────────────────────
    subgraph GATEWAY ["🔐 Stage 2 — Gateway / Auth"]
        JWTCheck{"JWT\n Valid?"}
        JWTReject["❌ 401 Unauthorized \n Close WS Connection"]
        ExtractClaims["Extract Claims \n user_id · tenant_id \n role · session_id"]
        SessionCheck{"Session \n Exists?"}
        NewSession["Create New Session \n + conversation_id in Redis"]
        LoadSession["Load Existing Session \n from Redis"]
        RegisterWS["Register WS Connection \n user_id → socket mapping \n in Redis"]
        AckClient["⚡ Send ACK to Client \n { status: processing, \n  conversation_id }"]
    end

    %% ─────────────────────────────────────────
    %%  STAGE 3 — CONVERSATION CONTEXT
    %% ─────────────────────────────────────────
    subgraph CONTEXT ["📜 Stage 3 — Conversation Context"]
        LoadHistory["Load Conversation History\n(last N turns from Redis\nor Postgres if cold)"]
        BuildContext["Build Context Window\n[ system prompt,\n  history turns,\n  new user message ]"]
        ContextTooLong{"Context exceeds\ntoken limit?"}
        SummarizeHistory["Summarize Older Turns\nwith LLM (compression)"]
        ContextReady["Context Ready\n→ pass to Classifier"]
    end

    %% ─────────────────────────────────────────
    %%  STAGE 4 — LLM ROLE 1: QUERY CLASSIFIER
    %% ─────────────────────────────────────────
    subgraph CLASSIFIER ["🤖 Stage 4 — LLM Role 1: Query Classifier"]
        LLMClassify["LLM Classifies Intent\n(fast / cheap model e.g. GPT-4o-mini)"]
        IntentRouter{"Detected\nIntent?"}

        IntentChitchat["💬 Chitchat\n'hi', 'thanks', 'lol'"]
        IntentClarify["❓ Ambiguous\nneeds clarification"]
        IntentComparison["⚖️ Comparison\n'X vs Y' · 'which is better'"]
        IntentConstraint["🎯 Constrained Search\n'only 3' · 'under $50'\n'near me' · 'open now'"]
        IntentSearch["🔍 Full Search\nstandard product / business lookup"]

        ExtractConstraints["Extract Constraint Params\n{ n_results, max_price,\n  location, open_now,\n  sort_by, filters[] }"]

        ChitchatReply["Generate Chitchat Reply\ndirectly (no ranker needed)"]
        ClarifyReply["Generate Clarification Question\n→ return to client, await response"]

        PublishDirect["Publish Direct Reply\nto Redis channel:user_id"]
    end

    %% ─────────────────────────────────────────
    %%  STAGE 5 — CACHE CHECK
    %% ─────────────────────────────────────────
    subgraph CACHE ["⚡ Stage 5 — Cache Check"]
        BuildCacheKey["Build Cache Key\nSHA-256(normalized_query\n+ tenant_id + constraints)"]
        CacheHit{"Cache Hit\nin Redis?"}
        CacheFresh[s168]
        ServeCached["Serve Cached Results\n→ skip to Synthesis"]
        CacheMiss["Cache Miss\n→ proceed to Ranker"]
    end

    %% ─────────────────────────────────────────
    %%  STAGE 6 — NER & QUERY ENRICHMENT
    %% ─────────────────────────────────────────
    subgraph NER_STAGE ["🏷️ Stage 6 — NER & Query Enrichment"]
        NERModel["NER Model\n(spaCy / fine-tuned)"]
        ExtractEntities["Extract Entities\nlocation · brand · category\nprice · product name · date"]
        QueryExpansion["Query Expansion\nsynonyms · related terms\n(e.g. 'pizza' → 'pizzeria', 'Italian')"]
        BuildStructuredQuery["Build Structured Query Object\n{\n  raw_text: '...',\n  entities: {...},\n  expanded_terms: [...],\n  constraints: {...},\n  intent_mode: 'comparison|search|constrained',\n  tenant_id: '...'\n}"]
    end

    %% ─────────────────────────────────────────
    %%  STAGE 7 — HYBRID SEARCH
    %% ─────────────────────────────────────────
    subgraph HYBRID ["🔎 Stage 7 — Hybrid Search Engine"]
        EmbedQuery["Embed User Query\n(same model as ETL embedder)"]
        
        subgraph PARALLEL ["Run in Parallel"]
            VectorSearch["Vector Search\npgvector — cosine similarity\nANN via HNSW index\n→ Top K semantic results"]
            KeywordSearch["Keyword Search\nPostgres Full-Text Search\ntsvector · tsquery\n→ Top K lexical results"]
        end

        FusionStrategy["Reciprocal Rank Fusion\n(RRF)\nmerge + score both result sets"]
        TenantFilter["Apply Tenant Filter\n(only show records\nfor this tenant_id)"]
        ConstraintFilter["Apply Hard Filters\nprice · location · open_now\ncategory · date range"]
        
        SearchEmpty{"Any results\nafter filtering?"}
        FallbackSearch["Fallback: Relax Constraints\n(drop 1 filter at a time)"]
        NoResultsReply["Generate 'No Results'\nresponse → skip to Synthesis"]
    end

    %% ─────────────────────────────────────────
    %%  STAGE 8 — RE-RANKING
    %% ─────────────────────────────────────────
    subgraph RERANK ["📊 Stage 8 — Re-Ranking & Filtering"]
        CrossEncoder["Cross-Encoder Re-Ranker\n(query × each result)\nfine-grained relevance score"]
        ApplyNResults["Apply n_results Constraint\n(trim to requested count)"]
        DiversityFilter["Diversity Filter\n(avoid returning 5 identical items\nfrom same source)"]
        FinalResultSet["Final Result Set\n[\n  { record, score,\n    source, chunk_text },\n  ...\n]"]
    end

    %% ─────────────────────────────────────────
    %%  STAGE 9 — LLM ROLE 2: SYNTHESIS
    %% ─────────────────────────────────────────
    subgraph SYNTHESIS ["✍️ Stage 9 — LLM Role 2: Response Synthesis"]
        BuildSynthPrompt["Build Synthesis Prompt\n{\n  system: persona + tone rules,\n  history: conversation context,\n  results: final result set,\n  intent_mode: comparison|list|search,\n  constraints: user preferences\n}"]
        LLMSynth["LLM Synthesizer\n(GPT-4o / Claude / local)\nGenerates natural language response"]
        LLMFail{"LLM\nSucceeded?"}
        LLMRetry["↩ Retry LLM Call\n(backoff)"]
        LLMFallback["Fallback: Return Structured\nJSON results without prose"]

        FormatRouter{"Intent\nMode?"}
        FormatList["📋 Format as List\n(standard search)"]
        FormatComparison["⚖️ Format as\nComparison Table"]
        FormatConstrained["🎯 Format as\nFiltered Short List"]

        StreamTokens[s168]
        StreamChunks["Stream response chunks\nas they generate\n(SSE-like over WS)"]
        FullResponse["Wait for full response\nthen send at once"]
    end

    %% ─────────────────────────────────────────
    %%  STAGE 10 — CACHE WRITE & PERSIST
    %% ─────────────────────────────────────────
    subgraph PERSIST ["💾 Stage 10 — Cache Write & Persistence"]
        CacheWrite["Write Results to Redis Cache\nkey: SHA-256(query+tenant)\nTTL: configured per source type"]
        SaveTurn["Save Conversation Turn\nto Postgres\n{ user_msg, assistant_msg,\n  intent, results_snapshot,\n  latency_ms, timestamp }"]
        UpdateHistory["Update Redis Session\nAppend new turn to history"]
    end

    %% ─────────────────────────────────────────
    %%  STAGE 11 — REDIS PUB/SUB
    %% ─────────────────────────────────────────
    subgraph PUBSUB ["📡 Stage 11 — Redis Pub/Sub Delivery"]
        PublishResult["Publish to Redis Channel\nchannel: result:{user_id}:{conversation_id}\npayload: { response, results,\n           intent, latency_ms }"]
        WSSubscribed{"WS Manager\nstill subscribed?"}
        StoreOffline["Store in Redis\noffline:{user_id}\n(deliver on reconnect)"]
        WSManagerReceive["WS Manager\nInstantly receives published event\n(no polling)"]
        PushToClient["Push Response\nto Client over WSS"]
    end

    %% ─────────────────────────────────────────
    %%  STAGE 12 — CLIENT RECEIVES
    %% ─────────────────────────────────────────
    subgraph RECEIVE ["✅ Stage 12 — Client Side Receipt"]
        ClientReceive["ChatUI receives\nWS message"]
        RenderResponse["Render Response\n(markdown · table · list)"]
        UpdateConvUI["Update Conversation UI\n+ scroll to latest message"]
        FeedbackPrompt["Optional: Show Feedback UI\n👍 👎 (for ranking improvement)"]
        FeedbackCollect{"User gives\nfeedback?"}
        StoreFeedback["Store Feedback\n→ Postgres\n(future fine-tuning signal)"]
    end

    %% ─────────────────────────────────────────
    %%  OBSERVABILITY
    %% ─────────────────────────────────────────
    subgraph OBS ["📊 Observability — Cross-cutting"]
        TraceSpan["OpenTelemetry Trace Span\nper stage with:\n· latency · token count\n· cache hit/miss · result count\n· intent classified · errors"]
        OTelCollector["OTel Collector"]
        Grafana["Grafana\nMetrics · Logs · Traces"]
    end

    %% ─────────────────────────────────────────
    %%  ERROR HANDLING
    %% ─────────────────────────────────────────
    subgraph ERRS ["💀 Error Handling"]
        ErrTimeout["⏱ Ranker Timeout\n→ keyword-only fallback"]
        ErrDBDown["🗄️ DB Unavailable\n→ serve from cache if exists"]
        ErrWSDisconnect["🔌 WS Disconnected\n→ store result offline"]
        ErrLLMDown["🤖 LLM Unavailable\n→ return raw structured results"]
    end

    %% ══════════════════════════════════════════
    %%  CONNECTIONS
    %% ══════════════════════════════════════════

    %% Stage 0
    UserTypes --> WSExists
    WSExists -->|"No"| WSHandshake
    WSExists -->|"Yes"| WSReuse
    WSHandshake --> SendPayload
    WSReuse --> SendPayload

    %% Stage 1 - NGINX
    SendPayload --> RateCheck
    RateCheck -->|"Yes"| RateReject
    RateCheck -->|"No"| WSUpgrade
    WSUpgrade --> RouteGW

    %% Stage 2 - Gateway
    RouteGW --> JWTCheck
    JWTCheck -->|"Invalid"| JWTReject
    JWTCheck -->|"Valid"| ExtractClaims
    ExtractClaims --> SessionCheck
    SessionCheck -->|"New"| NewSession
    SessionCheck -->|"Existing"| LoadSession
    NewSession & LoadSession --> RegisterWS
    RegisterWS --> AckClient
    AckClient --> LoadHistory

    %% Stage 3 - Context
    LoadHistory --> BuildContext
    BuildContext --> ContextTooLong
    ContextTooLong -->|"Yes"| SummarizeHistory
    ContextTooLong -->|"No"| ContextReady
    SummarizeHistory --> ContextReady

    %% Stage 4 - Classifier
    ContextReady --> LLMClassify
    LLMClassify --> IntentRouter
    IntentRouter -->|"chitchat"| IntentChitchat
    IntentRouter -->|"ambiguous"| IntentClarify
    IntentRouter -->|"comparison"| IntentComparison
    IntentRouter -->|"constrained"| IntentConstraint
    IntentRouter -->|"search"| IntentSearch

    IntentChitchat --> ChitchatReply
    IntentClarify --> ClarifyReply
    ChitchatReply --> PublishDirect
    ClarifyReply --> PublishDirect

    IntentComparison --> ExtractConstraints
    IntentConstraint --> ExtractConstraints
    IntentSearch --> ExtractConstraints

    %% Stage 5 - Cache
    ExtractConstraints --> BuildCacheKey
    BuildCacheKey --> CacheHit
    CacheHit -->|"Yes"| CacheFresh
    CacheHit -->|"No"| CacheMiss
    CacheFresh -->|"Yes"| ServeCached
    CacheFresh -->|"No"| CacheMiss
    ServeCached --> BuildSynthPrompt
    CacheMiss --> NERModel

    %% Stage 6 - NER
    NERModel --> ExtractEntities
    ExtractEntities --> QueryExpansion
    QueryExpansion --> BuildStructuredQuery

    %% Stage 7 - Hybrid Search
    BuildStructuredQuery --> EmbedQuery
    EmbedQuery --> VectorSearch & KeywordSearch
    VectorSearch & KeywordSearch --> FusionStrategy
    FusionStrategy --> TenantFilter
    TenantFilter --> ConstraintFilter
    ConstraintFilter --> SearchEmpty
    SearchEmpty -->|"No results"| FallbackSearch
    FallbackSearch -->|"still empty"| NoResultsReply
    FallbackSearch -->|"results found"| CrossEncoder
    SearchEmpty -->|"Has results"| CrossEncoder
    NoResultsReply --> BuildSynthPrompt

    %% Stage 8 - Re-ranking
    CrossEncoder --> ApplyNResults
    ApplyNResults --> DiversityFilter
    DiversityFilter --> FinalResultSet

    %% Stage 9 - Synthesis
    FinalResultSet --> BuildSynthPrompt
    BuildSynthPrompt --> LLMSynth
    LLMSynth --> LLMFail
    LLMFail -->|"No"| LLMRetry
    LLMRetry -->|"retries < max"| LLMSynth
    LLMRetry -->|"retries = max"| LLMFallback
    LLMFail -->|"Yes"| FormatRouter
    LLMFallback --> PublishResult

    FormatRouter -->|"list"| FormatList
    FormatRouter -->|"comparison"| FormatComparison
    FormatRouter -->|"constrained"| FormatConstrained

    FormatList & FormatComparison & FormatConstrained --> StreamTokens
    StreamTokens -->|"Yes"| StreamChunks
    StreamTokens -->|"No"| FullResponse

    %% Stage 10 - Persist
    StreamChunks & FullResponse --> CacheWrite
    CacheWrite --> SaveTurn
    SaveTurn --> UpdateHistory

    %% Stage 11 - Pub/Sub
    UpdateHistory --> PublishResult
    PublishDirect --> WSSubscribed
    PublishResult --> WSSubscribed
    WSSubscribed -->|"No — disconnected"| StoreOffline
    WSSubscribed -->|"Yes"| WSManagerReceive
    WSManagerReceive --> PushToClient

    %% Stage 12 - Client
    PushToClient --> ClientReceive
    ClientReceive --> RenderResponse
    RenderResponse --> UpdateConvUI
    UpdateConvUI --> FeedbackPrompt
    FeedbackPrompt --> FeedbackCollect
    FeedbackCollect -->|"Yes"| StoreFeedback

    %% Errors
    ErrTimeout -.->|"fallback"| KeywordSearch
    ErrDBDown -.->|"fallback"| ServeCached
    ErrWSDisconnect -.->|"store"| StoreOffline
    ErrLLMDown -.->|"fallback"| LLMFallback

    %% Observability
    GATEWAY & CLASSIFIER & NER_STAGE & HYBRID & RERANK & SYNTHESIS --> TraceSpan
    TraceSpan --> OTelCollector --> Grafana

    %% Styling
    classDef client fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef nginx fill:#E8A838,stroke:#B07820,color:#fff
    classDef gateway fill:#7B68EE,stroke:#4B3BAA,color:#fff
    classDef context fill:#20B2AA,stroke:#148080,color:#fff
    classDef classifier fill:#FF8C00,stroke:#CC6600,color:#fff
    classDef cache fill:#32CD32,stroke:#1E8020,color:#fff
    classDef ner fill:#9370DB,stroke:#6A3FAA,color:#fff
    classDef hybrid fill:#20B2AA,stroke:#148080,color:#fff
    classDef rerank fill:#4682B4,stroke:#2C5280,color:#fff
    classDef synth fill:#FF6347,stroke:#CC3D25,color:#fff
    classDef persist fill:#3CB371,stroke:#1E6B40,color:#fff
    classDef pubsub fill:#FFD700,stroke:#B8860B,color:#000
    classDef receive fill:#4A90D9,stroke:#2C5F8A,color:#fff
    classDef error fill:#DC143C,stroke:#8B0000,color:#fff
    classDef obs fill:#708090,stroke:#4A5560,color:#fff

    class UserTypes,WSExists,WSHandshake,WSReuse,SendPayload client
    class RateCheck,RateReject,WSUpgrade,RouteGW nginx
    class JWTCheck,JWTReject,ExtractClaims,SessionCheck,NewSession,LoadSession,RegisterWS,AckClient gateway
    class LoadHistory,BuildContext,ContextTooLong,SummarizeHistory,ContextReady context
    class LLMClassify,IntentRouter,IntentChitchat,IntentClarify,IntentComparison,IntentConstraint,IntentSearch,ExtractConstraints,ChitchatReply,ClarifyReply,PublishDirect classifier
    class BuildCacheKey,CacheHit,CacheFresh,ServeCached,CacheMiss cache
    class NERModel,ExtractEntities,QueryExpansion,BuildStructuredQuery ner
    class EmbedQuery,VectorSearch,KeywordSearch,FusionStrategy,TenantFilter,ConstraintFilter,SearchEmpty,FallbackSearch,NoResultsReply hybrid
    class CrossEncoder,ApplyNResults,DiversityFilter,FinalResultSet rerank
    class BuildSynthPrompt,LLMSynth,LLMFail,LLMRetry,LLMFallback,FormatRouter,FormatList,FormatComparison,FormatConstrained,StreamTokens,StreamChunks,FullResponse synth
    class CacheWrite,SaveTurn,UpdateHistory persist
    class PublishResult,WSSubscribed,StoreOffline,WSManagerReceive,PushToClient pubsub
    class ClientReceive,RenderResponse,UpdateConvUI,FeedbackPrompt,FeedbackCollect,StoreFeedback receive
    class ErrTimeout,ErrDBDown,ErrWSDisconnect,ErrLLMDown error
    class TraceSpan,OTelCollector,Grafana obs
'''