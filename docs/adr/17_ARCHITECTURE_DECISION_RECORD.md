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
**Date:** 2026-04-18  
**Status:** Accepted (D05)  
**Owners:** Architecture Team

### 2. Context

What problem or tension required a decision?
LangGraph requires a checkpoint store for durable state persistence to support our `interrupt_before` human gate (ADR-001). We need a production-grade database to store long-running threads that is compliant with Azure hosting infrastructure constraints.

### 3. Options considered

1. **Azure Database for PostgreSQL.**
2. **Azure Cosmos DB (NoSQL).**
3. **Azure Blob Storage (custom saver implementation).**

### 4. Decision

We choose **Option 1: Azure Database for PostgreSQL Flexible Server**.

### 5. Rationale

Following the Module 03 prototype evaluation, PostgreSQL proved exceptionally capable of handling the `WorkflowState` JSON blob serialization at scale without degrading resumption speed. Furthermore, relying on PostgreSQL's Entra native authentication provides stronger isolation against Bicep RBAC overlap that complicated the Cosmos DB deployments, aligning with our identity containment strategies.

### 6. Consequences

- **Trade-offs:** PostgreSQL Flexible Server requires distinct Entra DB administration provisioning versus standard Azure RBAC assignments, slightly complicating initial deployment scripts.
- **New Risks:** Large graph states could inflate the PostgreSQL footprint if not truncated or archived efficiently.
- **Follow-up actions:** Ensure infrastructure only enables PostgreSQL Entra authentication and a dedicated bootstrap admin path; scoped runtime and API database roles must be provisioned separately without making the graph or approver identities server administrators.

### 7. Status updates

**Status:** Accepted (D05) 

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

---

### 1. ADR metadata

**ID:** ADR-004  
**Title:** Identity Topology and Deployment Controls  
**Date:** 2026-04-17  
**Status:** Accepted (D04)  
**Owners:** FDE Security Team

### 2. Context

What problem or tension required a decision?
Day 04 requires strict separation of read/write/admin and pipeline identity planes. If we use a single monolith deployment identity to deploy our infrastructure, code, and perform migrations, it inevitably garners Data Plane access (like reading Key Vaults or peering into Cosmos DB data) breaking least privilege. We need to decouple our pipeline identities from the runtime execution ones.

### 3. Options considered

1. **Monolithic Service Principal:** A single GitHub Actions identity that creates ACA containers, provisions DBs, and acts as the application's runtime identity simultaneously.
2. **Topology Isolation (Strict Plane Decoupling):** Deployer identity creates infrastructure but cannot read runtime data (`mi-meridian-deployer`). Separate runtime execution identities are granted strictly isolated bindings mapping `mi-meridian-graph` vs `mi-meridian-erp-activator` via distinct Bicep roleAssignments.

### 4. Decision

We choose **Option 2: Topology Isolation (Strict Plane Decoupling)**.

### 5. Rationale

This natively fulfills ZT02 (No hidden write path/broad credential). By physically isolating `mi-meridian-deployer` to Control Plane operations exclusively (e.g., restricted `Role Based Access Control Administrator` on bounding groups, with exactly zero Data Plane read access), a compromised CI/CD pipeline token cannot be abused by a threat actor to download current compliance data or manually run ERP triggers. 

### 6. Consequences

- **Trade-offs:** High infrastructure-as-code (IaC) complexity. Bicep modules need fine-grained `roleDefinitions` which are trickier to debug locally.
- **New Risks:** Overly restrictive bounds might cause transient deployment failures if the deployment identity lacks a niche secondary scope needed to restart a Container App toggle.
- **Follow-up actions:** Continuous `az role assignment list` audits explicitly executed against the managed identities when deploying further architecture in M02.

### 7. Status updates

**Status:** Accepted (Active)

---

### 1. ADR metadata

**ID:** ADR-005  
**Title:** Layered Observability Strategy  
**Date:** 2026-04-18  
**Status:** Accepted (D05)  
**Owners:** Architecture Team

### 2. Context

We need comprehensive monitoring for the system, stretching from deep semantic execution logic down to root infrastructure constraints.

### 3. Options considered

1. **Single Pane of Glass (Only Azure Monitor).**
2. **Layered Split (Azure Monitor + LangSmith).**

### 4. Decision

We choose **Option 2: Layered Split (Azure Monitor + LangSmith)**.

### 5. Rationale

Formalize a telemetry split: **Azure Monitor (Application Insights + Log Analytics)** handles broad infrastructure SLA latency and enterprise alerting, while **LangSmith** drives Graph-level semantic traceability. They serve entirely distinct operational audiences.

### 6. Consequences

- **Trade-offs:** Cost of maintaining two telemetry services.
- **New Risks:** Correlating cross-system traces may require building explicit headers.
- **Follow-up actions:** Ensure terminology is consistent across documentation.

### 7. Status updates

**Status:** Accepted (D05)

---

### 1. ADR metadata

**ID:** ADR-006  
**Title:** Agentic vs Deterministic Document Synthesis  
**Date:** 2026-04-18  
**Status:** Accepted (D05)  
**Owners:** Architecture Team

### 2. Context

For extracting REACH concepts out of documents, do we rely on regex and rules engines or generative agents?

### 3. Options considered

1. **Rules Engine (Deterministic).**
2. **Generative/Agentic routing.**

### 4. Decision

We choose **Option 2: Generative/Agentic routing**.

### 5. Rationale

Explicitly lock in Generative/Agentic routing for REACH document synthesis vs Rules Engines. The complexity and variability of REACH documents overwhelm deterministic parsers.

### 6. Consequences

- **Trade-offs:** Less predictability but much higher extraction accuracy.
- **New Risks:** Hallucinations.
- **Follow-up actions:** Tie this back to the human gate from ADR-001.

### 7. Status updates

**Status:** Accepted (D05)

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
