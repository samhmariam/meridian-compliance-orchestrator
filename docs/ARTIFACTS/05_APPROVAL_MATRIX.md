# 05_APPROVAL_MATRIX

## Role in the programme

- **Primary module:** M01
- **First due:** D02
- **Capstone anchor:** `meridian-compliance-orchestrator`

## Purpose

Define where meaningful human oversight exists and what evidence a human needs to act responsibly.

## How to use this template

Complete every section with Meridian-specific content. Do not submit a generic framework answer. Where a section does not apply, explain why it does not apply in the capstone rather than leaving it blank.

## Required sections

### 1. Decision inventory

List each workflow decision node.

1. `intake_validation`
2. `search_sanctions_list` (API ping)
3. `search_reach_knowledge_base` (RAG semantic search)
4. `lookup_export_control_classification` (DB ping)
5. `risk_classifier` (Initial synthesis)
6. `generate_compliance_memo` (Drafting output)
7. `human_approval_gate` (Routing to Human Reviewer)
8. `activate_supplier_in_erp` (Irreversible API execution)

### 2. Control classification

Mark each as autonomous, advisory, or approval-required.

| Decision Node | Classification |
|---|---|
| `intake_validation` | **Autonomous** |
| `search_sanctions_list` | **Autonomous** |
| `search_reach_knowledge_base`| **Autonomous** |
| `lookup_export_control_classification`| **Autonomous** |
| `risk_classifier` | **Advisory** (Output is purely a recommendation for the human) |
| `generate_compliance_memo` | **Advisory** (Output is an evidence draft for the human reviewer) |
| `human_approval_gate` | **Approval-Required** (Halts the StateGraph via `interrupt_before`) |
| `activate_supplier_in_erp` | **Approval-Required** (Executes only after the state contains a valid `"approved"` signal from the human approval gate; that signal is the approval, not a separate control class) |

### 3. Evidence required

For approval-required nodes, specify evidence packet contents.

**Node:** `human_approval_gate`
**Evidence Packet Required for Human Approver:**
- **Supplier Profile Details:** `supplier_id`, `legal_name`, `country_of_incorporation`
- **Sanctions Result:** Pass/Fail categorical flag with API execution timestamp and hash.
- **REACH Compliance Summary:** LLM-generated synthesis of chemicals found, backed by directly cited source chunks (rendered with metadata showing `source_name` and `valid_until` dates for trust validation).
- **Export Control Codes:** Raw HS Codes matching.
- **System Recommendation:** The advisory `severity` level (clear, elevated, block) with explicit natural-language reasoning.
- **Action Buttons:** Approve, Reject, or Defer. (System explicitly rejects the hook if submitted without accompanying justification text).

### 4. Approval outcomes

Approved, rejected, deferred, plus downstream effect.

- **Approved:** The `WorkflowState.human_decision` is marked as `"approved"`. The LangGraph thread is resumed. The orchestrator transitions autonomously to the `activate_supplier_in_erp` node, executing the API call, logging the transaction ID, and progressing to the audit close node.
- **Rejected:** The `WorkflowState.human_decision` is marked as `"rejected"`. The LangGraph thread is resumed. The orchestrator bypasses the ERP activation block completely, transitions directly to the `audit_close` node, and formalizes the rejection state.
- **Deferred:** The `WorkflowState.human_decision` is marked as `"deferred"`. The state checkpoint is updated, but the orchestrator remains paused at the `human_approval_gate` pending further information (e.g., human requesting more documents from the supplier via an out-of-band email).

### 5. Identity and audit

State who can approve and how the action is logged.

- **Who:** Only identities bearing the explicit RBAC `Meridian Compliance Officer` Entra ID security group assignment can authenticate against a dedicated "Review Web API" boundary. This strictly revokes arbitrary direct database write scopes, isolating the human interaction to controlled Web API endpoints that proxy the approval webhook payload. The Web API itself holds the constrained application role required to update approval state and resume the graph.
- **Audit Logging:** Upon resume, the `audit_close` node will append a durable `AuditEvent` to the graph state recording the `human_decision`, the exact `human_decision_by` (using their Entra Object ID), the `human_decision_at` timestamp, and the required textual `human_decision_rationale`. This enforces non-repudiation of the approval.

### 6. Future change triggers

What would cause reclassification of a node?

- If Meridian scales to processing >10k qualifications monthly, the business might request purely "Green/Clear" path qualifications (where sanctions, REACH, and Export Control all return native clears) to bypass the `human_approval_gate` automatically. This would reclassify `activate_supplier_in_erp` to purely Autonomous on Green. 
- *Caveat:* Such a change would trigger a complete rebuild of the Threat Model and Risk Register to account for False Negatives bypassing humans entirely, and require regulatory sign-off.

## Evidence required for acceptance

- [x] ERP activation is approval-required.
- [x] Evidence packet is described in operator terms.
- [x] Approval outcomes are typed and traceable.

## Review prompts

- What decision would this artifact allow an instructor, operator, or architect to make?
- Where does this artifact connect to the running Meridian system?
- What would fail if this artifact were wrong or missing?

## Common failure modes

- Human approval noted but no evidence packet.
- No identity/logging path.
- Irreversible action not explicitly gated.

## Submission standard

- Commit the completed artifact to the learner branch.
- Keep it consistent with `CAPSTONE_PROJECT_SPEC.md`, the module file, and any related ADRs.
- Update this artifact when later module work materially changes the underlying decision.
