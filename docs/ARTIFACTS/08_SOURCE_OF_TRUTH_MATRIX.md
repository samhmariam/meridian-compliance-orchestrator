# 08_SOURCE_OF_TRUTH_MATRIX

## Role in the programme

- **Primary module:** M02
- **First due:** D06
- **Capstone anchor:** `meridian-compliance-orchestrator`

## Purpose

Classify which content sources the system may trust for different decisions, ensuring strict distinction between origination reality, mirroring latency, and external supplier claims.

## Required sections

### 1. Source inventory

The Meridian capstone uses the following content sources:
- **REACH Regulation Directives (ECHA):** The origin statutory legal guidance governing chemical constraints.
- **UK Sanctions List Simulator (OFSI mock):** Structured external-mimic dataset providing sanctioned entity states.
- **Export Control Lookups (Internal Schedule DB):** Internal tracking database indexing export restriction commodity codes.
- **Internal Compliance Policies:** Meridian corporate standard operating procedures and threshold templates.
- **Supplier Qualification Submissions:** Incoming external declarations attached to a `submission_id` stipulating CAS values.

### 2. Authority tiers

- **Tier 1 (Authoritative Legal Source):** Original EU REACH statutory directives and origin legal statutes. Cannot be overridden. 
- **Tier 2 (Operational Mirror / Simulator):** Sanctions Simulator data and Internal Export-Control database. (These are copies or bounded proxies of an original DB).
  - *MVP Authority Exemption:* For this capstone, Tier 2 operational simulators/mirrors are granted `Authoritative Override` status to unblock ERP Activation, provided their telemetry proves they are running within a strict `mirror_last_synced` SLA timeframe.
- **Tier 3 (Supporting/Contextual):** Supplier-submitted evidence, qualification form data, or vendor declarations. Under no circumstances can a Tier 3 source independently justify ERP activation without a corresponding Tier 1 / Tier 2 regulatory validation.

### 3. Freshness expectations

- **Tier 1 REACH Guidance:** Must hold an `effective_from` date and participate in explicit chunk-level `amendment_of` lineage so newer partial amendments can supersede only the targeted passage. Re-ingested chunks update `valid_until`.
- **Tier 2 Operational Mirrors:** Must track `mirror_last_synced` explicitly in telemetry. Sanctions simulator lists and export-control DB snapshots must both be < 24-hours stale before the MVP Authority Exemption can unblock activation.
- **Tier 3 Supplier Evidence:** Isolated logically to its designated `submission_id` and `document_version_id`. Operates independently of the executing graph's `thread_id` so an unreviewed queue does not artificially invalidate fresh evidence.

### 4. Decision linkage

- **Export Control Block:** Driven purely by Tier 2 (Export Control DB). May block activation. May unblock activation if the MVP Tier 2 Exception is valid.
- **Sanctions Block:** Driven purely by Tier 2 (Sanctions Simulator). May block activation. May unblock activation if MVP Exception applies.
- **Chemical Compliance (REACH):** Synthesized using supplier input (Tier 3) evaluated exclusively against the statutory guidelines (Tier 1).
- **Human Approval (Review UI):** Driven by an evidence packet surfacing citations. Must prominently flag if `mvp_override_applied` to contextualize that a Tier 2 mirror governed the block decision.

### 5. Contradiction handling

1. **Tier Precedence:** Tier 1 definitively overrides Tier 2, which definitively overrides Tier 3. If a Tier 3 supplier declaration asserts compliance but Tier 1 statutory text conflicts with that declaration, the risk state is immediately Elevated, and the supplier's claim is discarded as invalid.
2. **Intra-Tier Resolution:** 
   - Between two valid Tier 1 sources (e.g. multiple active REACH guidelines), narrow `jurisdiction` > broader `jurisdiction`.
   - Newest `effective_from` > older `effective_from`.
   - Explicit `amendment_of` chunking linkage determines supersedence. Partial amendments override only the target chunk, allowing the rest of the generic original document to survive.

### 6. Operational controls

- All chunks indexed into Azure AI Search MUST carry the ADR-007 base schema: `origin_type`, `canonical_source_id`, `effective_from`, `valid_until`, `jurisdiction`, and `amendment_of`.
- Mirror-only lineage fields are conditional on provenance. If `origin_type == "mirror"`, the payload MUST also include `mirror_of` and `mirror_last_synced`. If `origin_type == "origin"`, those fields remain null or omitted and must not trigger hard-fail rejection.
- Retrieval architecture will enforce strict hard-filters on validity metadata before ever executing a pure semantic similarity score on document chunks.

## Evidence required for acceptance

- [x] Tier definitions align with compliance use case.
- [x] Freshness rules are actionable.
- [x] Contradiction policy is explicit.
