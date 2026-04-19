# 09_GROUNDING_POLICY

**Artifact ID:** 09_GROUNDING_POLICY  
**Status:** Active — D07 initial version  
**Primary module:** M02  
**First committed:** D07  
**Last updated:** D07  
**ADR cross-reference:** ADR-007 (Strict Metadata and Provenance Schema)  
**Zero-tolerance addressed:** ZT03 (no provenance or freshness policy)

---

## 1. Index and corpus design

### Index

The Meridian compliance workflow indexes all regulatory content into a single Azure AI Search index named `meridian-compliance-index`. A single index is chosen over per-tier indices because it permits a unified hybrid retrieval query path (keyword + vector), allows authority-tier filtering to be applied at query time rather than at routing time, and avoids index fan-out complexity during the D08 retrieval service build.

The index schema supports hybrid retrieval from day one (vector field `content_vector` with HNSW, keyword-searchable `content` and `title` fields) to avoid a schema migration when semantic ranking is added in D08.

### Corpus classes

All indexed documents belong to exactly one of three authority classes defined in `08_SOURCE_OF_TRUTH_MATRIX.md`:

| Corpus class | `source_tier` | `origin_type` | Example sources |
|---|---|---|---|
| **Authoritative** | `1` | `origin` | ECHA REACH statutory directives, export control commodity code schedules (origin copy) |
| **Operational mirror** | `2` | `mirror` | OFSI sanctions simulator snapshot, internal export-control DB export |
| **Supporting / contextual** | `3` | `origin` or `mirror` | Internal compliance policy templates, supplier qualification guides |

Each chunk carries `source_tier` as a filterable integer so retrieval queries can hard-filter below a minimum tier when generating compliance memos for ERP-activation decisions.

---

## 2. Chunking strategy

### Chosen strategy: Markdown header-aware structural chunking

Compliance documents in `data/compliance_corpus/` are authored in Markdown with explicit H1 / H2 / H3 section headers. The ingestion pipeline (`src/retrieval/ingestion.py`) splits each document at those header boundaries rather than at a fixed character or token count.

**How it works:**

1. The document front-matter (YAML block between `---` delimiters) is parsed separately and used to populate document-level metadata fields. It is not included in chunk content.
2. The remaining body is scanned for `#`, `##`, and `###` header lines using a regex. Each header and its following content up to the next header forms one chunk.
3. Every chunk records a `section_path` string encoding the full heading hierarchy (e.g. `REACH Regulation R1 > Annex XVII > Entry 28 — Lead`). This preserves the regulatory scope context for downstream citation.
4. An empty section (header with no body text) is discarded rather than indexed as a content-free stub.

**Why fixed-size chunking is inadequate for this corpus:**

Fixed-size chunking without structure preservation splits text at arbitrary byte or token offsets, with three concrete failure modes for Meridian:

1. **Jurisdiction boundary crossing.** A REACH directive may have adjacent sections covering EU obligations and UK GB obligations separated only by a header. Fixed-size chunks routinely merge them, causing the retrieval system to surface a chunk that falsely implies a UK supplier is subject to an EU-only constraint.
2. **Amendment lineage destruction.** Partial amendments (e.g. "this entry replaces Entry 28 as of 2025-01-01") appear as short sections. A fixed-size chunker absorbs the amendment text into its surrounding section, making the `amendment_of` provenance link meaningless at query time.
3. **Recall / citation precision tradeoff.** Oversized fixed chunks improve recall at the cost of returning paragraphs that contain the answer buried inside irrelevant regulatory boilerplate. For a compliance officer reading the evidence packet, this raises cognitive load and risks misinterpretation.

### Re-ingestion behaviour for updated documents

When a document is updated (e.g. a new REACH amendment supersedes a prior entry):

- The newer document is ingested with an updated `document_version` and `effective_from` date, and `valid_until` set on the superseded chunks in a separate patch call.
- The `amendment_of` field on affected chunks records the `canonical_source_id` of the document being superseded, enabling the retrieval layer to exclude or down-rank chunks whose entire section has been superseded.
- Previous version chunks remain in the index to support audit replay but are excluded from active compliance retrieval by the `valid_until` filter defined in Section 6.
- `content_hash` provides a deterministic equality check to skip re-upsert when a file is re-processed without meaningful change.

---

## 3. Metadata fields

Every indexed chunk must carry all of the following fields. Fields marked **conditional** are required only when `origin_type == "mirror"`; they must be absent or null for `origin_type == "origin"` and must not trigger a hard-fail rejection on absence.

| Field | Type | Mandatory | Purpose |
|---|---|---|---|
| `chunk_id` | string (key) | Required | Deterministic Azure Search-safe key derived from `{document_id}::{section_path}::{content_hash}` via SHA-256. The readable hierarchy remains in `section_path`. |
| `document_id` | string | Required | Stable identifier for the source document. Used to group all chunks from one document for lineage queries. |
| `source_name` | string | Required | Human-readable document name (e.g. "ECHA REACH Guidance R1 2024"). Used in citation output. |
| `source_tier` | int32 | Required | `1` = authoritative, `2` = operational mirror, `3` = supporting. Hard-filter gate for ERP-activation memo retrieval. |
| `origin_type` | string | Required | `"origin"` or `"mirror"`. Governs which conditional fields are enforced. Drives telemetry classification. |
| `canonical_source_id` | string | Required | Stable identifier for the original legal text or authority document. For mirrors, this is the ID of the original, not the mirror copy. |
| `effective_from` | DateTimeOffset | Required | Date from which this chunk's content became legally or operationally effective. Freshness filter lower bound. |
| `valid_until` | DateTimeOffset | Optional | Date after which this chunk is superseded. Freshness filter upper bound. Null means currently valid. |
| `jurisdiction` | string | Required | Regulatory jurisdiction this chunk applies to (e.g. `"EU"`, `"GB"`, `"GLOBAL"`). Used to prevent cross-jurisdiction citation errors. |
| `document_version` | string | Required | Semantic version or publication identifier of the source document. |
| `amendment_of` | string | Optional | `canonical_source_id` of the document or chunk this content supersedes. Null for non-amendment content. |
| `mirror_of` | string | **Conditional** | `canonical_source_id` of the original document this is a mirror of. Required when `origin_type == "mirror"`. |
| `mirror_last_synced` | DateTimeOffset | **Conditional** | Timestamp of the most recent sync from the authoritative source. Required when `origin_type == "mirror"`. Staleness gate for Tier 2 MVP override (see Section 6). |
| `ingested_at` | DateTimeOffset | Required | UTC timestamp of the ingestion run. Provides an audit trail independent of document dates. |
| `content_hash` | string | Required | SHA-256 (truncated to 16 hex chars) of the chunk's content text. Deduplication and change-detection signal. |
| `section_path` | string | Required | Full heading hierarchy path (e.g. `"Annex XVII > Entry 28 > Scope"`). Supports citation precision and lineage reconstruction. |
| `title` | string | Required | Leaf section heading. Searchable. Used in citation display. |
| `content` | string | Required | The chunk's text body. Keyword-searchable. |
| `content_vector` | Collection(Single) | Required (full pipeline) | 1536-dimension embedding vector for HNSW nearest-neighbour search. Populated by the embeddings service; empty in `--dry-run` mode. |

These fields satisfy both the ADR-007 provenance contract and the D07 metadata minimums simultaneously. The mapping is explicit:

- ADR-007 mandatory: `origin_type` ✓ `canonical_source_id` ✓ `effective_from` ✓ `valid_until` ✓ `jurisdiction` ✓ `amendment_of` ✓
- ADR-007 conditional (mirror): `mirror_of` ✓ `mirror_last_synced` ✓
- D07 minimums: `document_id` ✓ `source_name` ✓ `source_tier` ✓ `effective_from` ✓ `jurisdiction` ✓ `document_version` ✓ `ingested_at` ✓ `content_hash` ✓

---

## 4. Retrieval policy

> **Note:** Full retrieval query logic is implemented in D08 (`src/retrieval/retriever.py`). This section establishes the policy constraints that the retrieval service must enforce; implementation evidence is deferred to D08.

### Hybrid retrieval

The retrieval service combines two signal paths:

1. **BM25 keyword search** over `content` and `title` for exact regulatory term recall.
2. **HNSW vector search** over `content_vector` for semantic similarity.

Both paths are required because REACH directives use precise technical language (CAS numbers, substance names, threshold values) where BM25 gives exact recall, while compliance policy documents use varied phrasing where vector search is necessary.

### Mandatory pre-filters (applied before scoring)

All retrieval queries for compliance memo generation must apply:

1. `source_tier le 2` — Tier 3 supporting documents never justify ERP-activation memos unilaterally (per `08_SOURCE_OF_TRUTH_MATRIX.md` Section 4).
2. `valid_until eq null or valid_until gt <query_timestamp>` — Excludes superseded chunks (see Section 6).
3. `effective_from le <query_timestamp>` — Excludes not-yet-effective content.
4. `jurisdiction eq '<supplier_jurisdiction>' or jurisdiction eq 'GLOBAL'` — Prevents cross-jurisdiction citation errors.

### Conflict resolution

- **Newer authoritative over older authoritative:** When two Tier 1 chunks address the same obligation, the chunk with the later `effective_from` wins. `amendment_of` linkage takes explicit precedence over date comparison.
- **Authoritative over supporting:** Tier 1 always overrides Tier 3 regardless of date.
- **Mirror staleness conflict:** If `mirror_last_synced` exceeds the 24-hour SLA, the Tier 2 MVP override is suspended and the conflicting Tier 2 chunk is excluded (see Section 6).

---

## 5. Citation contract

Every factual claim in a Meridian compliance memo must carry a citation that includes the following minimum fields, sourced directly from the retrieved chunk's metadata:

| Citation field | Source metadata field | Required |
|---|---|---|
| Document name | `source_name` | Required |
| Authority tier | `source_tier` | Required |
| Section path | `section_path` | Required |
| Jurisdiction | `jurisdiction` | Required |
| Effective from | `effective_from` | Required |
| Retrieval timestamp | `ingested_at` (at retrieval) | Required |
| Canonical source ID | `canonical_source_id` | Required |

**Enforcement:** The memo generation node validates all citations against the document IDs present in the retrieval span. A claim citing a `canonical_source_id` not present in the retrieval results triggers a `grounding_violation` audit event and the memo is held for human review rather than routed to the approval gate.

**Ungrounded claims:** Any factual compliance assertion produced by the LLM without a retrievable citation is flagged as `UNGROUNDED` in the memo structure and excluded from the recommendation section. The human reviewer receives both the grounded and ungrounded sections explicitly labelled.

**Mirror disclosure:** If any citation derives from a Tier 2 mirror document, the evidence packet presented to the human approver prominently includes the `mvp_override_applied: true` flag and the `mirror_last_synced` timestamp, consistent with `08_SOURCE_OF_TRUTH_MATRIX.md` Section 4.

---

## 6. Freshness enforcement

This section closes the ZT03 zero-tolerance condition (no provenance or freshness policy).

### Validity window filtering

Before a chunk is eligible for retrieval, it must satisfy the validity window:

```
effective_from <= query_timestamp AND (valid_until IS NULL OR valid_until > query_timestamp)
```

This filter is applied as a hard pre-filter in Azure AI Search, not as a post-retrieval reranker, ensuring that superseded content never enters the scoring pipeline at all. This prevents the hallucination failure mode where a superseded regulation becomes the cited justification for supplier activation.

### Amendment-based supersedence

When a new amendment document is ingested that sets `amendment_of = <prior_canonical_source_id>`, the ingestion pipeline issues a patch to set `valid_until` on all prior chunks sharing that `canonical_source_id`. The patch is transactional per document: if the patch fails, the new amendment chunks are rolled back to prevent a state where both old and new versions appear valid simultaneously.

### Tier 2 mirror staleness gate

Operational mirror documents (Tier 2: sanctions simulator, export-control DB) are eligible for the MVP Authority Override only when:

```
mirror_last_synced >= query_timestamp - 24h
```

If `mirror_last_synced` is older than 24 hours, the mirror chunk is treated as `source_tier = 3` for the duration of the query. This prevents a stale sanctions snapshot from unblocking a supplier activation that should be held pending a fresh authoritative check.

### Ingestion audit event

Every ingestion run emits a structured log event:

```json
{
  "event": "corpus_ingestion_complete",
  "run_id": "<uuid>",
  "document_count": <n>,
  "chunk_count": <n>,
  "oldest_effective_from": "<ISO8601>",
  "newest_effective_from": "<ISO8601>",
  "mirror_staleness_violations": <n>
}
```

A non-zero `mirror_staleness_violations` is an operational alert requiring remediation before the next ERP-activation workflow can invoke the Tier 2 MVP override.

---

## 7. Evaluation hooks

This section establishes measurement points for D09 (Grounding Quality Lab) and later M05 evaluation work.

| Metric | Tool | Target | First measured |
|---|---|---|---|
| **Chunk validity ratio** | `ingestion.py --dry-run` output | 100% of chunks pass schema validation | D07 |
| **Stale-document recall contamination** | RAGAS context relevance + manual date filter test | 0 chunks with `valid_until < query_date` returned | D09 |
| **Cross-jurisdiction citation error rate** | Manual adversarial query (EU chunk retrieved for GB query) | 0% with jurisdiction filter active | D09 |
| **Citation contract compliance** | Memo generation node validation log | 0 `grounding_violation` events on grounded documents | D08/D09 |
| **Mirror staleness violation rate** | Ingestion audit event `mirror_staleness_violations` | 0 violations per ingestion run | D07 ongoing |
| **Amendment supersedence coverage** | Query old `canonical_source_id` post-amendment | 0 chunks returned with `valid_until` in the past | D09 |

These evaluation hooks feed directly into `14_EVAL_SCORECARD.md` Section 2 (Retrieval baseline) and the M02 exit gate.

---

## Evidence required for acceptance

- [x] Metadata fields are specific and used in example queries (Section 3 and Section 4).
- [x] Citation contract is output-enforceable (Section 5 enforcement paragraph).
- [x] Policy references authoritative precedence (ADR-007 and `08_SOURCE_OF_TRUTH_MATRIX.md`).
- [x] Freshness enforcement closes ZT03 (Section 6 validity window filter and amendment supersedence).
- [x] Chunking rationale explains why structure loss is unacceptable for this corpus (Section 2).
- [x] Code evidence: `src/retrieval/ingestion.py` implements this policy.
