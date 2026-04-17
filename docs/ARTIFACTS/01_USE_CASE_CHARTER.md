# 01_USE_CASE_CHARTER

## Role in the programme

- **Primary module:** M01
- **First due:** D01
- **Capstone anchor:** `meridian-compliance-orchestrator`

## Purpose

Define why the Meridian workflow is worth solving, why it may warrant an agentic architecture, and what success looks like in measurable business terms.

## How to use this template

Complete every section with Meridian-specific content. Do not submit a generic framework answer. Where a section does not apply, explain why it does not apply in the capstone rather than leaving it blank.

## Required sections

### 1. Artifact intent

This charter establishes the business case and operational justification for developing an agentic supplier qualification system at Meridian Industrial Components Ltd. It enables the architecture board to decide whether to proceed with building the `meridian-compliance-orchestrator` by clarifying what will be automated, what remains human-driven, and what the success metrics are.

### 2. Workflow identification

- **Workflow name:** Supplier Qualification and Compliance Orchestration
- **Business owner:** Head of Compliance, Meridian Industrial Components Ltd
- **Technical owner:** Forward Deployed Engineering Team
- **Target environment:** Azure Container Apps (with Azure AI Foundry/Search/OpenAI) 
- **Affected business unit:** Global Supply Chain & Compliance Operations

### 3. Problem statement

Meridian's compliance team manually processes 200–400 supplier qualification events per month. Each event involves cross-referencing suppliers against sanctions lists (e.g., OFAC, UK HMT), validating REACH substance declarations (CAS numbers), looking up export control classifications (HS codes), and synthesizing a compliance memo for sign-off.
This highly manual evidence-gathering and reporting process is fragile, inconsistent, and takes 3–5 business days to complete per supplier, stalling supply chain agility. The bottleneck is entirely dependent on the availability of human compliance officers, who spend the majority of their time navigating documents rather than exercising compliance judgment.

### 4. Agentic fit analysis

The workflow consists of several distinct tasks:
1. **Intake Validation (Deterministic):** Validating the incoming `QualificationRequest` schema and parsing data.
2. **Sanctions Screening (Deterministic):** Querying structured sanctions lists via API to see if `supplier_id` matches.
3. **Export Control Classification (Deterministic / LLM-Assisted):** Looking up internal database/schedules based on primary commodity codes.
4. **REACH Check (LLM-Assisted / Agentic):** Retrieving unstructured regulatory guidance against declared CAS numbers to assess compliance, which requires navigating complex, evolving text.
5. **Risk Classification & Memo Generation (Agentic):** Synthesizing the gathered evidence from all the parallel checks, evaluating contradictions (e.g. stale vs fresh documents), classifying the severity of the risk, and authoring a cohesive, cited compliance memo. This mimics human reasoning.
6. **Human Approval Gate (Human-driven):** The final sign-off based on the generated evidence packet remains human-driven.
7. **ERP Activation (Deterministic):** Triggers the activation API in the ERP upon approval.

An agentic architecture is justified because the workflow requires reading unstructured compliance guidance (REACH) and dynamically pulling contextual evidence from a corpus to synthesize a complex, multi-factor risk decision before human review. Rule-based automation fails at the unstructured data synthesis, and human-only leaves the bottleneck intact. See `02_COUNTERFACTUAL_MEMO.md` for rejected alternatives.

### 5. Scope boundaries

**In scope:**
- Automated initiation from structured intake form.
- Sanctions screening against provided API simulator.
- REACH substance declaration validation against local knowledge base via Retrieval-Augmented Generation (RAG).
- Export control classification lookup.
- Autonomous compliance memo generation with citations to evidence.
- A human-in-the-loop approval routing with an evidence packet.
- Automated ERP activation trigger after human approval.
- Complete execution audit trail.

**Out of scope:**
- Integration with live real-world OFAC/sanctions APIs (using simulator).
- Integration with real, production ERP systems (using mock stub).
- Multi-language support.
- Customer-facing UI.

### 6. Success metrics

- **Business:** Reduce end-to-end supplier qualification time. 
  - *Baseline:* 3–5 days. *Target:* < 1 day (blocked only by human approval latency).
- **Operational:** Reduce human compliance officer time spent per request.
  - *Baseline:* ~2 hours (gathering evidence and memo writing). *Target:* < 15 minutes (reviewing evidence packet).
- **Economic (Token Cost):** Token cost per qualification.
  - *Baseline:* N/A. *Target:* < £0.25 at production pricing.
- **Economic (Latency):** End-to-end orchestration latency (p95).
  - *Baseline:* N/A. *Target:* < 45 seconds (excluding human approval pause).
- **Quality (RAGAS):** Faithfulness and Context Recall of generated memos.
  - *Baseline:* N/A. *Target:* Faithfulness >= 0.85, Context Recall >= 0.80.

### 7. Failure consequences

- **Severe (Regulatory/Reputational):** A false negative in sanctions screening or REACH compliance leading to the ERP activation of an illegal supplier. *Consequence:* Fines from UK FCA/EU authorities, prison for executives, severe reputational damage.
- **Medium (Operational):** A high rate of false positives (hallucinated risk). *Consequence:* The human compliance officer workload increases as they must manually re-verify the evidence, nullifying the ROI. Token budgets are wasted on repeated escalations.
- **Low (Technical):** Graph orchestration times out under load. *Consequence:* Delay in qualification by a few minutes, system retires/restarts.

### 8. Recommendation

Proceed with the development of `meridian-compliance-orchestrator`. 
*Conditions:* The project must enforce a strict `interrupt_before` node before the `activate_supplier_in_erp` tool is called. The LLM must not have autonomous write access to the ERP. 
*Unresolved questions:* How will the system react if the provided REACH document corpus contradicts itself across different dates? (Will be addressed in M02 Grounding Policy).

### 9. Discovery Notes (Stakeholder Simulation)

**What I Learned:**
The stakeholder (Head of Compliance) firmly believes their team exercises deep judgment at every step, but our questioning revealed that 80% of their "judgment" is actually just searching CTRL-F in PDF documents and copy-pasting tables. Their hesitation towards AI stems from a past vendor who tried to replace the final sign-off, which terrified them due to regulatory liability. They are highly protective of their staff.

**What I Missed:**
I failed to identify the exact difference between a "standard" priority and an "urgent" priority qualification request and how that cascades into SLAs during the manual process. I also assumed the ERP activation was just a simple flag, but it might require specific transaction IDs.

**Questions for Session 2:**
- "Could you walk me through an example of a time when the team had to reject a supplier despite them passing initial sanctions checks?" (To find hidden edge cases).
- "When you finally sign off, what exactly are you looking at on the screen? What formatting makes you trust the evidence?"

## Evidence required for acceptance

- [x] Referenced workflow steps match `CAPSTONE_PROJECT_SPEC.md`.
- [x] KPIs have numeric baselines or explicit baseline-collection plan.
- [x] At least one counterfactual is acknowledged here and linked to `02_COUNTERFACTUAL_MEMO.md`.

## Review prompts

- What decision would this artifact allow an instructor, operator, or architect to make?
- Where does this artifact connect to the running Meridian system?
- What would fail if this artifact were wrong or missing?

## Common failure modes

- Calling every step 'agentic'.
- Using generic KPI language with no baseline or target.
- Scope boundary missing or contradictory to capstone.

## Submission standard

- Commit the completed artifact to the learner branch.
- Keep it consistent with `CAPSTONE_PROJECT_SPEC.md`, the module file, and any related ADRs.
- Update this artifact when later module work materially changes the underlying decision.
