# 17_ARCHITECTURE_DECISION_RECORD

## Role in the programme

- **Primary module:** Cross-cutting
- **First due:** Starts D02, maintained throughout
- **Capstone anchor:** `meridian-compliance-orchestrator`

## Purpose

Record major decisions, alternatives, and consequences across the full build.

## How to use this template

Complete every section with Meridian-specific content. Do not submit a generic framework answer. Where a section does not apply, explain why it does not apply in the capstone rather than leaving it blank.

## Required sections

### 1. ADR metadata

**ID:** ADR-001  
**Title:** Autonomous Read vs Human-Gated Write Orchestration Boundary  
**Date:** 2026-04-17  
**Status:** Accepted (D02)  
**Owners:** FDE Team

### 2. Context

What problem or tension required a decision?
The Meridian compliance workflow culminates in a supplier activation event within the enterprise ERP. While we want to maximize throughput and agentic autonomy, we face regulatory and security consequences if a false-negative sanctions check or a hallucinated REACH analysis causes an illegal supplier to be activated autonomously without human sign-off.

### 3. Options considered

1. **Fully Autonomous (No Human Gate):** Provide the LLM with `activate_supplier_in_erp` tool access natively. System activates suppliers when it synthesizes a "Clear" status.
2. **Explicit Human Gate via `interrupt_before`:** Isolate the entire orchestrator into "Read/Synthesize" phases, and halt the StateGraph before any "Write/Execute" phase for human review.
3. **Out-of-Band Integration:** LLM never executes the ERP write. It generates an email or ticket, and the compliance officer clicks "Activate" directly inside the ERP system itself, completely disconnected from this project.

### 4. Decision

We choose **Option 2: Explicit Human Gate via `interrupt_before`**.

### 5. Rationale

To comply with regulatory non-repudiation limits while achieving our throughput targets, the agentic components must be authorized to synthesize the "Evidence Packet" rapidly, but explicitly deprived of final autonomous execution authority. Using LangGraph's `interrupt_before` semantic natively embeds the human approval inside the StateGraph loop, ensuring state is durably checkpointed and that the execution tool `activate_supplier_in_erp` strictly shares the same audit lineage as the data retrieval process (unlike Option 3, which snaps the audit trail in half).
**Rejected Option 1:** Failed the risk matrix (Tier 1 regulatory penalty risk on false negative bindings).
**Rejected Option 3:** Degrades the operator experience and fractures the telemetry/audit correlation between the decision boundary and the execution boundary.

### 6. Consequences

- **Trade-offs:** We must implement a persistent Checkpoint backend (e.g. PostgreSQL) because processes will be put to sleep and resumed across hours/days as they wait for human interaction. 
- **New Risks:** If the human reviewer gets fatigued by reading memos, they will rubber stamp inputs, converting our human oversight into a psychological false security.
- **Follow-up actions:** We must implement strict validation loops to construct rich evidence packets to maximize human trust and comprehension.

### 7. Status updates

**Status:** Accepted (Active)

---

### 1. ADR metadata

**ID:** ADR-002  
**Title:** State Persistence and Checkpointing Backend Selection  
**Date:** 2026-04-17  
**Status:** Deferred (D02)  
**Owners:** Architecture Team

### 2. Context

What problem or tension required a decision?
LangGraph requires a checkpoint store for durable state persistence to support our `interrupt_before` human gate (ADR-001). We need a production-grade database to store long-running threads that is compliant with Azure hosting infrastructure constraints.

### 3. Options considered

1. **Azure Database for PostgreSQL.**
2. **Azure Cosmos DB (NoSQL).**
3. **Azure Blob Storage (custom saver implementation).**

### 4. Decision

**Deferred.**

### 5. Rationale

We are deferring this decision until Module 03 when we assemble the working graph prototype. We currently lack data on the exact volume and schema complexity of the `WorkflowState` object JSON blobs once fully populated with raw REACH document chunks. We will use `SqliteSaver` in-memory/local for early development until we define the schema footprint sizes.

### 6. Consequences

- **Trade-offs:** Delayed infrastructure lock-in.
- **New Risks:** Re-work required in M03 when migrating from SQLite to the final production engine.
- **Follow-up actions:** Perform a spike in M03 to serialize a full 128k token context window state payload into PostgreSQL vs CosmosDB to evaluate performance degradation and resumption speed.

### 7. Status updates

**Status:** Deferred 

---

### 1. ADR metadata

**ID:** ADR-003  
**Title:** Handling High-Burst Token Quota Exhaustion (TPM Limits)  
**Date:** 2026-04-17  
**Status:** Open Risk (Unresolved)  
**Owners:** Platform Team

### 2. Context

What problem or tension required a decision?
Meridian can have burst volumes of 50-100 qualifications on the last day of the month. Given our targeted agentic design consumes dense REACH document chunks into context windows, we risk hitting the Azure OpenAI gpt-4o Tokens Per Minute (TPM) quota limits, which will yield HTTP 429 Too Many Request responses mid-orchestration.

### 3. Options considered

1. **Pay for Provisioned Throughput (PTU):** Very expensive flat-rate infrastructure cost.
2. **Deploy Azure API Management with auto-retries & exponential backoff:** Graph level pause/retry behaviors.
3. **Multi-Region Load Balancing:** Deploy gpt-4o endpoints in UK South, Sweden Central, and East US, and round-robin the requests.

### 4. Decision

**Unresolved Risk.**

### 5. Rationale

We have not yet determined the exact token consumption profile per qualification. If the context window density averages 10k tokens, we can easily survive under standard Pay-As-You-Go limits. If it jumps to 100k tokens per pass due to dense chunk retrieval, we might need multi-region balancing. We cannot decide until M05 (Evaluation) provides concrete telemetry on average token load.

### 6. Consequences

- **Trade-offs:** Development environment might experience intermittent 429s during load drills in M04.
- **New Risks:** Latency spikes beyond the 45-second p95 target if retries are relied upon too heavily.
- **Follow-up actions:** Enforce strict token counting spans in the M03 telemetry architecture and establish the baseline usage before returning to this ADR.

### 7. Status updates

**Status:** Open Risk

## Evidence required for acceptance

- [x] At least one ADR for each major module decision area.
- [x] Rejected alternatives are real and reasoned.
- [x] Consequences are acknowledged.

## Review prompts

- What decision would this artifact allow an instructor, operator, or architect to make?
- Where does this artifact connect to the running Meridian system?
- What would fail if this artifact were wrong or missing?

## Common failure modes

- Decision recorded with no alternatives.
- Generic context.
- ADR updated only at the end.

## Submission standard

- Commit the completed artifact to the learner branch.
- Keep it consistent with `CAPSTONE_PROJECT_SPEC.md`, the module file, and any related ADRs.
- Update this artifact when later module work materially changes the underlying decision.
