# 03_ROI_MODEL

## Role in the programme

- **Primary module:** M01
- **First due:** D02
- **Capstone anchor:** `meridian-compliance-orchestrator`

## Purpose

Model whether the capstone creates economic value under conservative assumptions.

## How to use this template

Complete every section with Meridian-specific content. Do not submit a generic framework answer. Where a section does not apply, explain why it does not apply in the capstone rather than leaving it blank.

## Required sections

### 1. Model scope

This model calculates the Return on Investment (ROI) for the `meridian-compliance-orchestrator` agentic system replacing the mechanical evidence-gathering portion of the supplier qualification lifecycle. It covers infrastructure costs, LLM tokens, build/maintenance engineering effort, and compliance officer time saved. It does not include hard-to-measure downstream benefits like avoiding hypothetical regulatory fines, which are treated as risk mitigations rather than direct financial ROI.

### 2. Assumptions register

- **Throughput:** 400 qualification events per month (upper bound of Meridian volume).
- **Human Hourly Rate:** £60/hour (£120k/year loaded) for Compliance Officers.
- **Manual Baseline Time:** 2 hours per qualification event currently.
- **Agentic Target Time:** 15 minutes per qualification event (reviewing the generated evidence packet).
- **Engineering Cost:** £80/hour loaded cost for Forward Deployed Engineers.
- **Maintenance Overheads:** 20 hours per month for model-ops, prompt tuning, and dependency updates.
- **Token Usage:** Max £0.25 target cost per qualification event.

### 3. Cost model

- **Build Cost (One-time):** £24,000 (300 engineering hours to scaffold, build, and evaluate the orchestration).
- **Run-time (Infra + Tokens):** ~£77.00 infra + ~£100 tokens = £177.00 / month (cloud spend only).
- **Maintenance (Ongoing):** £1,600 / month (20 engineering hours).
- **Human Review (Ongoing):** £6,000 / month (100 hours of compliance review time at £60/hr for 400 events).
- **Total Operational Cost:** ~£7,777 / month. Reconciliation: £177 cloud spend + £1,600 maintenance + £6,000 human review = £7,777 monthly operating cost.

### 3b. Azure infrastructure cost decomposition

Break down the monthly Azure operating cost for the production topology. Use the Azure Pricing Calculator to estimate each line item. Do not guess — use published pricing for the chosen region (UK South).

| Cost category | Azure service | Tier / SKU | Estimated monthly cost | Assumptions |
|---|---|---|---|---|
| Model inference | Azure OpenAI Service | gpt-4o (30k TPM quota) | £100.00 | Assuming max £0.25 per run at 400 runs/month. |
| Search and retrieval | Azure AI Search | Basic | £55.00 | 2GB index, sufficient for document corpus. |
| Checkpoint and state storage | Azure Database for PostgreSQL | Burstable (B1ms) | £15.00 | Low transaction rate required for sqlite/postgres LangGraph saving. |
| API gateway | Azure API Management | Consumption | £0.00 | Assuming < 1 million calls/month. |
| Compute | Azure Container Apps | 1 vCPU, 2GB, 1-2 replicas | £0.00 | Covered by free grant (2 million requests). Negligible cost. |
| Secrets management | Azure Key Vault | Standard | £0.50 | ~10k operations. |
| Observability | Azure Monitor / Log Analytics | Pay-As-You-Go | £2.50 | Estimating 1GB ingestion/month for traces. |
| Container registry | Azure Container Registry | Basic | £4.00 | Minimal image storage. |
| Network egress | Egress to LangSmith / external | Zone 1 | £0.00 | First 100GB/month is free. |
| **Total Azure cloud spend (monthly)** | | | **£177.00** | Cloud services only; human review and maintenance costs are accounted for in the operating-cost model above. |

**Cost scaling note:** If qualification volume doubles to 800/month, inference tokens scale linearly to £200, human review scales linearly to £12,000. Azure fixed costs (Search, DB, ACR) remain flat, driving strong economies of scale. 

### 4. Benefit model

- **Avoided manual work (Savings):**
  Current manual cost: 400 events × 2 hours × £60 = £48,000 / month.
  New operational cost (human review): £6,000 / month.
  *Gross Savings:* £42,000 / month in compliance officer time.
- **Cycle-time reduction:** Qualification goes from 3-5 days to 1 day. Supply chain can onboard alternate suppliers faster, avoiding shipping bottleneck costs.
- **Risk reduction:** Centralizing compliance knowledge into a structured pipeline mitigates key-person dependency and enforces uniform application of rules against every supplier.

### 5. Scenarios

- **Conservative:** Volume is only 200/month. The LLM evidence packet is poor, requiring 45 minutes of human review. Human savings drop from £24,000 (manual) to £9,000 (review) = £15,000 savings/month.
- **Base:** Volume 400/month. LLM outputs are great, reducing review to 15 minutes. Savings: £42,000/month.
- **Optimistic:** The system scales to other jurisdictions (e.g., US ITAR) with near-zero extra fixed cost, doubling the event processing volume without increasing headcount.

### 6. Break-even analysis

**Conservative Scenario:** Net monthly savings = £15,000 - £1,777 (infra/maint) = £13,223/month.
Payback period = £24,000 upfront cost / £13,223 = **~1.8 months**.
**Base Scenario:** Net monthly savings = £42,000 - £1,777 = £40,223/month.
Payback period = £24,000 / £40,223 = **< 1 month**.

### 7. Sensitivity analysis

The model is highly sensitive to the **human review latency**. If the evidence packet quality is poor and forces the compliance officer to manually double-check REACH PDFs, the review time spikes back to 1.5 hours, wiping out 75% of the ROI. The ROI is relatively insensitive to token costs; even if inference cost doubles to £0.50 per event (£200/month), it barely dents the £40k+ human labor savings. 

### 8. Recommendation

Proceed. The economics overwhelmingly justify the development. The break-even period is under two months even in the conservative scenario, and the system addresses the operational bottleneck of compliance officer starvation directly.

## Evidence required for acceptance

- [x] Maintenance cost included.
- [x] A downside or worse-than-conservative scenario is present.
- [x] At least one assumption ties to the capstone NFRs.
- [x] Azure infrastructure cost decomposition completed with Pricing Calculator estimates.
- [x] Human review cost included as a line item.

## Review prompts

- What decision would this artifact allow an instructor, operator, or architect to make?
- Where does this artifact connect to the running Meridian system?
- What would fail if this artifact were wrong or missing?

## Common failure modes

- Only upside numbers.
- No human-review cost.
- No sensitivity analysis.
- No Azure infrastructure cost breakdown — only token costs modelled.
- Cost scaling assumptions absent.

## Submission standard

- Commit the completed artifact to the learner branch.
- Keep it consistent with `CAPSTONE_PROJECT_SPEC.md`, the module file, and any related ADRs.
- Update this artifact when later module work materially changes the underlying decision.
