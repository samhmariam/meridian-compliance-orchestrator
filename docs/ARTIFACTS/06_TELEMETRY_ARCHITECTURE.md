# 06_TELEMETRY_ARCHITECTURE

## Role in the programme

- **Primary module:** M01
- **First due:** D03
- **Capstone anchor:** `meridian-compliance-orchestrator`

## Purpose

Define trace, event, metric, and audit design before graph code grows.

## How to use this template

Complete every section with Meridian-specific content. Do not submit a generic framework answer. Where a section does not apply, explain why it does not apply in the capstone rather than leaving it blank.

## Required sections

### 1. Telemetry goals

What operator questions must telemetry answer?

**Fill here:**
- **Regulatory Non-Repudiation:** Who approved this supplier, why, and what explicitly bounded evidence did they possess when they clicked 'Approve'?
- **Latency Optimization (SLA bounds):** Where is the p95 > 45s latency occurring? Is the bottleneck in the Vector Search retrieval or the LLM generation phase?
- **Financial Bound Isolation:** What is the actual API token volume running through the agentic pipeline, and does the blended cost stay beneath the £0.25/qualification business ceiling limit?
- **Workflow State Corruption:** Where are asynchronous qualifications getting stuck and failing to resume after human approval?

### 2. Correlation IDs

Define workflow_id, request_id, trace_id, and thread_id usage.

**Fill here:**
- `workflow_id`: The broader, global lifecycle master identifier spanning multiple interactions for a single qualification file from intake to close.
- `request_id` == `thread_id`: **The permanently stable LangGraph Checkpoint Key** for the *specific* human-agent transaction loop. Crucially, this ID spans all invoke, suspension (interrupt), and resumption cycles. It does not reset during human transitions.
- `trace_id`: The OpenTelemetry structural root scope, linking a *specific compute API invocation* (like the python function execution doing the synthesis) to the parent `thread_id` context. 

### 3. Span taxonomy

List spans per node, tool, retrieval step, model call, and external action.

**Fill here:**

| Span type | Name pattern | Parent | Key attributes |
|---|---|---|---|
| Graph node | `node.{node_name}` | `workflow.{workflow_id}` | `node_name`, `input_state_hash`, `output_state_hash`, `duration_ms` |
| Model call | `model.{deployment_name}` | `node.{node_name}` | `run_name`, `usage_metadata.input_tokens`, `usage_metadata.output_tokens`, `usage_metadata.total_tokens`, `metadata` |
| Tool call | `tool.{tool_name}` | `node.{node_name}` | `tool_name`, `tool_result_status`, `duration_ms` |
| Retrieval | `retrieval.{index_name}` | `node.{node_name}` | `query_hash`, `top_k`, `result_count`, `source_tiers_returned` |

*Note: Spans must attach LangSmith-recognized `usage_metadata` plus model metadata such as `ls_provider` and `ls_model_name` for token and cost dashboards to aggregate correctly.*

### 4. Audit event taxonomy

List regulated/sensitive events and their required fields.

**Fill here:**
We exclusively map the mandated audit lifecycle events to plot state progression correctly:
1. `qualification_started`
2. `sanctions_check_completed`
3. `human_approval_requested`
4. `human_decision_received`
5. `erp_activation_attempted`
6. `erp_activation_completed`
7. `workflow_closed`

*Required fields for `human_decision_received`*: `human_decision_by` (Entra ID), `human_decision_at` (ISO8601 timeframe), `human_decision_rationale` (String text).

### 5. Business metric mapping

Show how raw events become KPI and SLO measurements.

**Fill here:**
- **Time to compliance decision**: The temporal delta (latency) from the root telemetry trace start to the `human_approval_requested` event.
- **Compliance officer review time**: The critical human latency KPI measured directly as the delta between `human_approval_requested` and `human_decision_received`.
- **Financial Cost Margin**: The aggregation of `usage_metadata.input_tokens`, `usage_metadata.output_tokens`, and derived costs nested beneath a `workflow_id`, mapped against Azure PAYG rates to confirm isolation under the £0.25/qualification ceiling.

### 6. Storage and views

State where debugging telemetry and enterprise telemetry live.

**Fill here:**
- **Debugging Telemetry:** Lives transiently in LangSmith (via direct callback environment routing). This targets iterative developer experience inside the dev/test ring to troubleshoot agent loops and token efficiency (D03 target).
- **Enterprise/Compliance Telemetry:** Native Azure Monitor (Log Analytics / Application Insights) bounding ensuring SOC2/ISO limits are placed on PII retention and data sovereignty.

### 7. Alerting hooks

Name the first alerts and threshold logic.

**Fill here:**
- **Latency Violation:** Triggers if global execution duration `qualification_started -> human_approval_requested` exceeds 45s (p95 SLA bound check).
- **TPM Surge:** Triggers if prompt payloads push the region past 30k tokens-per-minute threshold, anticipating a 429 Throttle error.
- **Data Persistence Violations:** Alert on any checkpoint resumption mismatch or read/write storage engine failures. If an orchestrator resumes but drops the `thread_id` linkage, it will trigger an immediate P1 integration alert.

## Evidence required for acceptance

- [x] One running trace exists. *(Completed via D03 code payload output).*
- [x] Business metrics map back to trace or audit events.
- [x] Audit events cover approval and ERP activation.

## Review prompts

- What decision would this artifact allow an instructor, operator, or architect to make?
- Where does this artifact connect to the running Meridian system?
- What would fail if this artifact were wrong or missing?

## Common failure modes

- Logging treated as tracing.
- No correlation IDs.
- No audit event design.

## Submission standard

- Commit the completed artifact to the learner branch.
- Keep it consistent with `CAPSTONE_PROJECT_SPEC.md`, the module file, and any related ADRs.
- Update this artifact when later module work materially changes the underlying decision.
