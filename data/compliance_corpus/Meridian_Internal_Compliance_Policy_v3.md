---
document_id: MERIDIAN-COMPLIANCE-POLICY-V3
source_name: Meridian Internal Compliance Policy v3 — Supplier Qualification
source_tier: 3
origin_type: origin
canonical_source_id: MERIDIAN-COMPLIANCE-POLICY-V3
effective_from: 2024-06-01T00:00:00Z
jurisdiction: GLOBAL
document_version: 3.0
---

# Meridian Internal Compliance Policy v3 — Supplier Qualification

This document is a **Tier 3 supporting** internal policy template governing
the Meridian supplier qualification workflow.  It defines operational thresholds,
escalation procedures, and evidence-packet requirements for compliance officers.

**Authority limitation:** Tier 3 content may never independently justify or
block ERP activation.  It provides operational context and internal process
guidance only.  All hard compliance decisions are governed by Tier 1 (REACH
statutory directives) and Tier 2 (sanctions and export-control mirrors).

## Policy Scope

This policy applies to all new and renewal supplier qualifications processed
through the Meridian Compliance Orchestrator.  It supplements, but does not
replace, the statutory obligations under EU REACH (Regulation EC 1907/2006)
and applicable UK, EU, and US sanctions regimes.

## Qualification Submission Requirements

### Mandatory Supplier Evidence

Suppliers must submit the following documents as part of a qualification request.
Submissions without all mandatory items are rejected at intake validation.

- **REACH substance declaration**: Signed declaration listing all CAS numbers
  present in supplied articles at ≥ 0.1% concentration.  Must reference the
  regulation version consulted (e.g., "ECHA REACH Annex XVII, 2024 consolidation").
- **Restricted substance test report**: Accredited third-party test report for
  substances appearing in Annex XVII entry categories relevant to the article type.
- **Country of origin certificate**: Issued within 12 months of submission.

### Supplementary Evidence (where applicable)

- RoHS compliance declaration for electronic or electrical components.
- Conflict minerals report (Dodd-Frank 1502) for articles containing tin,
  tungsten, tantalum, or gold.

## Internal Risk Thresholds

The following thresholds represent Meridian's internal conservative position
and may be stricter than the statutory minimums.  They do not override
statutory limits.

| Substance category | Meridian internal threshold | Statutory minimum |
|---|---|---|
| Lead (Entry 28) | 0.01% by weight | 0.03% by weight |
| Cadmium (Entry 63) | 0.005% by weight | 0.01% by weight |
| Hexavalent chromium | 0.01% by weight | 0.01% by weight (RoHS) |

> **Important:** These thresholds are internal policy only.  A supplier
> exceeding the Meridian internal threshold but complying with the statutory
> limit must be escalated to a human compliance officer for a risk
> determination.  The orchestrator must not autonomously block based on
> internal thresholds alone.

## Escalation and Human Review Procedure

### Risk Classification Matrix

| Classification | Criteria | Next action |
|---|---|---|
| `BLOCKED` | Active sanctions match or statutory REACH breach | Human review required; ERP activation prohibited |
| `ELEVATED` | Internal threshold breach; no statutory breach | Human review required; ERP activation prohibited pending sign-off |
| `STANDARD` | All checks pass within statutory limits | Human review optional; ERP activation permitted with approval |

### Evidence Packet Standards

The compliance officer evidence packet produced by the memo generation node
must include, at minimum:

1. Risk classification with one-sentence rationale.
2. Each compliance finding with the cited source (`canonical_source_id`,
   `section_path`, `effective_from`).
3. Explicit `mvp_override_applied` flag if any Tier 2 mirror was used
   within the MVP Authority Exemption window.
4. Operator attestation fields: `reviewed_by`, `reviewed_at`, `decision`.

Evidence packets omitting any of the above must be held by the human approval
gate and must not be auto-approved.

## Document Version History

| Version | Date | Author | Change summary |
|---|---|---|---|
| 3.0 | 2024-06-01 | Meridian Compliance Team | Aligned with 2024 REACH consolidation; added Meridian internal thresholds table |
| 2.1 | 2023-09-15 | Meridian Compliance Team | Added conflict minerals escalation path |
| 2.0 | 2023-01-10 | Meridian Compliance Team | Initial release of v2 policy framework |
