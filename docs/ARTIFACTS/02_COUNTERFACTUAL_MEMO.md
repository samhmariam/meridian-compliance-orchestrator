# 02_COUNTERFACTUAL_MEMO

## Role in the programme

- **Primary module:** M01
- **First due:** D01
- **Capstone anchor:** `meridian-compliance-orchestrator`

## Purpose

Prove the chosen architecture has earned its complexity by comparing it against simpler alternatives.

## How to use this template

Complete every section with Meridian-specific content. Do not submit a generic framework answer. Where a section does not apply, explain why it does not apply in the capstone rather than leaving it blank.

## Required sections

### 1. Decision under review

Why use an agentic workflow for Meridian supplier qualification instead of a simpler process orchestration or manual scaling?

### 2. Alternatives considered

1. **Option A: Manual continuation (Do Nothing / Status Quo)** - Rely entirely on the current human-driven process across all 200–400 monthly events.
2. **Option B: Rule-based automation (RPA)** - Use Robotic Process Automation or static scripts to query sanctions APIs, flag HS codes from static lists, and scrape REACH documents.
3. **Option C: LLM-Assisted but Human-Driven (Copilot)** - Provide the compliance officers with an AI chat interface loaded with REACH documents to ask questions manually.
4. **Option D: Proposed Agentic Design** - An autonomous orchestrator executing intake, parallel retrieval, API verification, and reasoning to produce an evidence packet for final human approval.

### 3. Comparison criteria

We evaluate options based on the following criteria:
- **Cost:** Build vs. run/maintenance costs.
- **Risk:** Probability of false negatives (regulatory failure).
- **Time-to-Value:** How fast the solution scales supply chain onboarding.
- **Compliance Control:** Extent of auditability for the regulatory pipeline.
- **Operator Burden:** Human compliance officer time spent per request.
- **Extensibility:** Flexibility to absorb new regulatory jurisdictions and workflows.

### 4. Analysis by alternative

#### Option A: Manual continuation (Do Nothing)
- **Succeeds:** Near-zero build cost. Requires no technological change. Retains the status quo for compliance control.
- **Breaks down:** Unscalable. Time-to-value is miserable (3-5 days per qualification limit). Operator burden is catastrophic to business operations, as humans are entirely consumed by mechanical evidence gathering.

#### Option B: Rule-based automation (RPA)
- **Succeeds:** Excels at calling the sanctions API (deterministic) and looking up the ERP. Fast execution. Low operating cost.
- **Breaks down:** Fails entirely at unstructured REACH document validation. Any format change in the supplier PDF declarations or REACH guidelines breaks the rule. False negative risk spikes due to brittle regex logic for chemical substance extraction.

#### Option C: LLM-Assisted but Human-Driven
- **Succeeds:** Good for edge-case research. Extensible to new rules with no code changes.
- **Breaks down:** Operator burden remains very high because the human is still manually orchestrating the inputs into the LLM instead of reviewing outputs. Time-to-value reduces only marginally compared to the status quo since the human officer remains the continuous bottleneck for every single lookup step.

#### Option D: Proposed Agentic Design
- **Succeeds:** Eliminates the mechanical gathering bottleneck and synthesizes evidence autonomously. Standardizes outputs. Reduces operator burden to pure judgment (reviewing a pre-authored memo).
- **Breaks down:** Highest upfront build cost. Requires sophisticated guardrails to ensure indirect prompt injections don't cause automated ERP activation. Demands rigor around LLM token budgets.

### 5. Rejected alternatives

- **Manual Continuation is rejected** due to unacceptable cycle times (3-5 days) that block Meridian's supply chain agility.
- **Rule-based automation is rejected** because unstructured data sets like descriptive REACH guidance documents and varied supplier declaration PDFs cannot be safely parsed deterministically without enormous maintenance overhead and high compliance risk.
- **LLM-Assisted (Copilot) is rejected** because it fails to decouple the core event throughput from human availability constraints. The operator remains orchestrator rather than reviewer. 

### 6. Decision recommendation

The agentic approach is justified now. The cost of complex AI orchestration (Option D) is outweighed by the necessity to process unstructured regulatory compliance data autonomously prior to human review. The key mechanism to safely embrace this complexity is explicitly walling off the ERP activation with an `interrupt_before` node, ensuring we gain the speed of autonomous gathering without the liability of autonomous execution.

## Evidence required for acceptance

- [x] Comparison includes concrete Meridian workflow steps, not abstractions.
- [x] Rejected alternatives include explicit risk or cost arguments.
- [x] Decision aligns with `01_USE_CASE_CHARTER.md`.

## Review prompts

- What decision would this artifact allow an instructor, operator, or architect to make?
- Where does this artifact connect to the running Meridian system?
- What would fail if this artifact were wrong or missing?

## Common failure modes

- Straw-manning the alternatives.
- Treating LLM-assisted and agentic as the same thing.
- No explicit rejection rationale.

## Submission standard

- Commit the completed artifact to the learner branch.
- Keep it consistent with `CAPSTONE_PROJECT_SPEC.md`, the module file, and any related ADRs.
- Update this artifact when later module work materially changes the underlying decision.
