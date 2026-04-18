# 10_PEER_REVIEW_RECORD

## Role in the programme
- **Primary module:** M05
- **First due:** D05
- **Capstone anchor:** `meridian-compliance-orchestrator`

## Purpose

To officially memorialize peer review activity that occurred leading up to the architectural lock-in, emphasizing reviews that validated the separation of AI computation from system side-effects.

## 1. Codebase Separation Review

**Review Date**: D05  
**Reviewer**: Forward Deployed Engineering Lead  
**Artifacts/Code Audited**: `mi-meridian-graph`, `mi-meridian-erp-activator`, and `infra/identity_rbac.bicep`

### Observations & Corrections
- **Observation:** Original proposals merged the graph node handling REACH extraction directly with the HTTP client that mutates the ERP.
- **Correction:** The team forced a strict codebase separation. `mi-meridian-graph` is sequestered computationally; it emits an immutable evidence payload as a final node output. `mi-meridian-erp-activator` processes only this strictly-typed output payload downstream, ensuring the LLM runtime never holds ERP credentials in memory.

## 2. Infrastructure Identity Matrix Audit

**Review Date**: D05  
**Reviewer**: Architecture Review Board / SecOps Proxy  
**Artifacts/Code Audited**: `07_IDENTITY_MATRIX.md`, `17_ARCHITECTURE_DECISION_RECORD.md`

### Observations & Corrections
- **Observation:** The use of Cosmos DB data-plane RBAC was flagged as potentially too complex for simple graph checkpointing. Additionally, long-lived access keys were proposed for DB authentication.
- **Correction:** Formalized **ADR-002** to pivot to Azure Database for PostgreSQL Flexible Server using Entra-authenticated connections plus a dedicated bootstrap-admin path. The graph runtime and human approver group are no longer PostgreSQL server administrators; constrained database roles are provisioned separately after server creation.

## 3. Human Gate API Boundary Check

**Review Date**: D05  
**Reviewer**: Compliance Ops  
**Artifacts/Code Audited**: `05_APPROVAL_MATRIX.md`, `04_RISK_REGISTER.md`

### Observations & Corrections
- **Observation:** A lack of defense-in-depth on the human approval step. An attacker could impersonate the webhook boundary and bypass the human approval entirely.
- **Correction:** Expanded the `04_RISK_REGISTER.md` with risks R11-R14, decoupling the human action into a dedicated "Review Web API." This restricts direct DB mutation scopes and mandates `human_decision_rationale` along with the Entra Object ID of the approver for non-repudiation.

## Submission standard

- Commit the completed artifact to the learner branch.
- Ensure the recorded peer reviews align precisely with the ADR closures and identity matrix refinements.
