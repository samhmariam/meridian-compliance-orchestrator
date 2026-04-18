# 04_RISK_REGISTER

## Role in the programme

- **Primary module:** M01
- **First due:** D02
- **Capstone anchor:** `meridian-compliance-orchestrator`

## Purpose

Create the program’s primary risk control artifact for operational, compliance, security, and model-related failure modes.

## How to use this template

Complete every section with Meridian-specific content. Do not submit a generic framework answer. Where a section does not apply, explain why it does not apply in the capstone rather than leaving it blank.

## Required sections

### 1. Risk model

Define likelihood and consequence scale.

**Likelihood Scale:**
- **High:** Expected to happen multiple times per month.
- **Medium:** Expected to happen multiple times per year.
- **Low:** Unlikely to happen in a given year.

**Consequence Scale:**
- **Tier 1 (Catastrophic):** Direct regulatory failure leading to fines (FCA/EU authorities), public reputational damage, or severe operational block.
- **Tier 2 (Severe):** Major degradation of compliance throughput causing supply chain stall, or mass errors requiring extensive manual remediation. 
- **Tier 3 (Moderate):** Re-work required by compliance officers on a small subset of qualifications; minor loss of SLA.
- **Tier 4 (Minor):** Handled transparently by systemic retry or delayed processing with no business consequence.

### 2. Risk table

For each risk: ID, description, category, consequence, likelihood, blast radius, owner, mitigation.

| ID | Description | Category | Consequence | Likelihood | Blast Radius | Owner | Mitigation |
|---|---|---|---|---|---|---|---|
| **R01** | **False Negative in Sanctions Matching (Mirror Lag)** - The Tier 2 operational mirror (simulator / export DB) returns a stale 'clear' for an actually sanctioned supplier. | Compliance | Tier 1 | Low | Up to 10 qualifications per day mischaracterized | Platform Team | The ERP activation requires an active human review gate; the evidence packet must explicitly show `mirror_last_synced` and the `mvp_override_applied` flag to contextualize the authority basis. |
| **R02** | **Stale REACH Document Retrieval (Authority Collision)** - The vector DB retrieves an outdated REACH directive that was partially superseded, leading the LLM to hallucinate a compliance positive. | Model / Compliance | Tier 1 | Medium | All workflows triggering chemical checks until doc refreshed (50-100 suppliers) | Knowledge Ops | Require strict semantic metadata filtering (ADR-007) by `valid_until` and `amendment_of` parameters in retrieval before similarity scoring. |
| **R03** | **Indirect Prompt Injection via Supplier Documents** - Supplier submits a malicious PDF designed to force the LLM to output "clear" for serious violations. | Security | Tier 2 | Medium | 1 qualification affected (isolated); possible automated activation if human reviewer rubber-stamps. | Security Team | Strict extraction-only tooling; system cannot jump human boundary; LLM operates with read-only scopes. |
| **R04** | **Azure OpenAI API Throttling (TPM limits)** - High burst traffic during month-end exhausts token limits. | Operational | Tier 3 | High | 100+ qualification requests delayed; fallbacks triggered. | Architecture Team | Implement Azure API Management with exponential backoff & retry nodes. |
| **R05** | **Hallucinated Compliance Citations** - LLM invents a non-existent REACH clause or CAS number matching in the generated memo. | Model Misbehavior | Tier 2 | Medium | Up to 5 qualifications before detection by human. | Prompt Eng Team | Grounding with RAGAS faithfulness metrics > 0.85; explicit directives to quote text sequences exactly. |
| **R06** | **LangGraph Checkpoint Database Failure** - PostgreSQL goes down, preventing threads from resuming after human approval. | Operational | Tier 2 | Low | All in-flight approvals dropped (10-50 stuck qualifications). | Infra Team | Burstable B1ms redundancy and automated PaaS backups in Azure. |
| **R07** | **Context Window Exhaustion** - Supplier document size > 128k tokens, causing text generation to truncate sanctions evidence. | Operational / Model | Tier 3 | Medium | 1 qualification stalled or partial synthesis generated. | FDE Team | Document chunking in Azure AI Search; metadata extraction over raw text ingestion. |
| **R08** | **Human Rubber-Stamping (Compliance Fatigue)** - Reviewer gets tired of reading long LLM memos and blindly signs off, bypassing our critical control. | Compliance | Tier 1 | High | Entire downstream pipe compromised; systematic legal exposure. | Product/UX Team | Make evidence packet concisely structured; require a mandatory 'reasoning' string field in approval webhook instead of a single click. |
| **R09** | **Export Control DB Schema Change** - The simulated database for HS Codes changes format silently. | Operational | Tier 3 | Low | Export control step defects and defaults to "elevated" risk recursively. | Platform Team | Strict API versioning; default-secure (system rejects rather than passes if API parsing fails). |
| **R10** | **Credential Leak in Code** - LangSmith or OpenAI keys checked into Git repository. | Security | Tier 1 | Low | Global exposure of telemetry data or token quota theft. | Security Team | ZT05 zero-tolerance checks in CI/CD pipeline; exclusively use Azure Managed Identity `DefaultAzureCredential`. |
| **R11** | **API Impersonation** - Threat actor mimics the Review Web API identity to forge human approval webhooks to the orchestrator. | Security | Tier 1 | Low | Bypasses human gate, autonomous ERP writes enabled. | Security Team | Mutual TLS or Entra specific token audience validation for inter-service calls. |
| **R12** | **Request Replay Attack** - Intercepted or re-transmitted Web API payload causes multiple downstream ERP triggers for the same compliance packet. | Security | Tier 2 | Low | Duplicate ERP records or sync errors. | Platform Team | Enforce strict idempotency keys in webhook payload and state graph checks. |
| **R13** | **Web-API Outage / Rate-Limiting** - The Review Web API goes down or hits rate limits, preventing Compliance Officers from submitting decisions. | Operational | Tier 2 | Medium | Backlog of human reviews (paused workflows). | Infra Team | ACA autoscaling for the Web API, circuit breakers on the UI. |
| **R14** | **Graph-Resume Desync** - The orchestrator thread ID is lost or mismatched between the Web API backend and LangGraph checkpoint. | Model / Operational | Tier 2 | Low | Zombie workflows waiting forever for approval. | Architecture Team | Strict thread ID tracking and automated sweep of stagnant state queues. |

### 3. Systemic vs single-event failure

- **Single-Event Failures:** Examples like Context Window Exhaustion (R07) and Prompt Injection (R03) represent a failure for a specific supplier profile or document. The blast radius is exactly 1 workflow execution.
- **Systemic Failures:** Examples like Stale Retrievals (R02), Checkpoint DB Failure (R06) and Rubber Stamping (R08) dynamically compromise the entire pipeline. The blast radius scales linearly with time until detection, affecting anything flowing concurrently.

### 4. Accepted risks

- **R04 (API Throttling)** is accepted for the M01/MVP target. We expect to hit Azure TPM limits in the Dev environment initially, and we accept degraded workflow initiation (higher latency) over deploying high-cost Provisioned Throughput units during development.
- **R09 (Export Schema Change)** is accepted, mitigated heavily by falling back to "elevated risk for human review" instead of engineering a complex resilient schema migration strategy right now.

### 5. Escalation criteria

- **Monitor to Intervention transition**:
  - If RAGAS faithfulness scores dip < 0.85 during daily batch evaluation metrics, automated alerts escalate to Prompts Team to pause autonomous generation deployments.
  - If > 3 prompt injection attempts are detected via content safety filters within 24 hours, escalate incident to Security Operations and temporarily suspend external supplier intake portal.
  - If the human review cycle time drops below 30 seconds geometric average (indicating R08 Rubber Stamping), escalate to the Head of Compliance to review audit logs and process with staff.

## Evidence required for acceptance

- [x] Minimum 10 Meridian-specific risks.
- [x] Blast radius quantified or bounded.
- [x] Owner and mitigation present for each active risk.

## Review prompts

- What decision would this artifact allow an instructor, operator, or architect to make?
- Where does this artifact connect to the running Meridian system?
- What would fail if this artifact were wrong or missing?

## Common failure modes

- Generic risk labels like 'model error'.
- No owner.
- No distinction between systemic and isolated failure.

## Submission standard

- Commit the completed artifact to the learner branch.
- Keep it consistent with `CAPSTONE_PROJECT_SPEC.md`, the module file, and any related ADRs.
- Update this artifact when later module work materially changes the underlying decision.
