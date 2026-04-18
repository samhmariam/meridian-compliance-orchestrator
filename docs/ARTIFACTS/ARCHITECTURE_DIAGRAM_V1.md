# ARCHITECTURE_DIAGRAM_V1

## Final D05 Architecture - Meridian Compliance Orchestrator

This artifact documents the final architecture approved at the Day 05 Architecture Review Board.

```mermaid
flowchart TD
    %% Define Boundaries
    subgraph UserBoundary["User Boundary (Entra ID)"]
        CO[Compliance Officer]
        Admin[Platform Admin]
    end

    subgraph ACAEnvironment["Azure Container Apps Environment"]
        subgraph WebBoundary["Review Web API Boundary"]
            UI[React/Vite Review UI]
            WebAPI[Review Web Backend API]
        end

        subgraph CoreLogic["Graph Orchestrator Boundary"]
            Graph[mi-meridian-graph]
        end

        subgraph ExecBoundary["Execution Boundary"]
            ERP_Act[mi-meridian-erp-activator]
        end
    end

    subgraph DataBoundary["Data & State Boundary"]
        PG[(PostgreSQL Flexible Server)]
        Index[(Azure AI Search)]
        Mem[(Azure Cache for Redis)]
    end

    subgraph Ext_AI["Azure AI / External APIs"]
        AOAI[Azure OpenAI GPT-4o]
        Sanctions[Sanctions API Simulator]
        ERP[ERP Mock Stub]
    end

    subgraph Telemetry["Observability"]
        AzMon[Azure Monitor]
        LangSmith[LangSmith Tracing]
    end

    %% Authentication & Requests
    CO -- Authenticates (Entra ID) --> UI
    UI -- Approval HTTP Request --> WebAPI
    WebAPI -- Triggers Resume --> Graph

    %% Orchestrator Operations
    Graph -- State Checkpoints (Entra Token / Scoped DB Role) --> PG
    Graph -- RAG Retrieval --> Index
    Graph -- Caching / Semantic Hit --> Mem
    Graph -- Inference --> AOAI
    Graph -- Validation Checks --> Sanctions

    %% Execution Phase
    Graph -- Secure Signal Payload --> ERP_Act
    ERP_Act -- Write Operation --> ERP

    %% Telemetry Output
    Graph -. Metrics/Traces .-> AzMon
    Graph -. Semantic Traces .-> LangSmith
    ERP_Act -. Audit Logs .-> AzMon
    WebAPI -. Access Logs .-> AzMon

    %% Admin Access
    Admin -. Diagnostic Access .-> AzMon
```
![alt text](image.png)

### Architecture Key Notes:
1. **PostgreSQL Checkpointing**: Based on ADR-002, Azure Database for PostgreSQL Flexible Server is used for LangGraph checkpointing relying on Entra ID for database connections instead of long-lived passwords. A dedicated bootstrap admin exists only to create constrained database roles; the graph runtime is not a server administrator.
2. **Review Web API Boundary**: Based on D05 Risk Matrix upgrades, the human CO does not speak directly to the graph payload webhook but interacts through a tightly-secured UI/API boundary enforcing idempotency and preventing API impersonation (R11).
3. **Execution Separation**: The Graph logic (`mi-meridian-graph`) is distinctly decoupled from the ERP invocation (`mi-meridian-erp-activator`), adhering to the core principle that the LLM engine does not bear ERP or server-level database administration scopes.
4. **Dual-Stack Observability**: Based on ADR-005, Azure Monitor collects the SLA infrastructural metrics (latency, crash rates, PII-bound audit boundaries) while LangSmith ingests transient semantic traces for ZT06 prompt evaluation.
