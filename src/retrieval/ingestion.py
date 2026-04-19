"""
src/retrieval/ingestion.py

Structure-aware ingestion pipeline for the Meridian Compliance Orchestrator.

Loads Markdown documents from data/compliance_corpus/ into an Azure AI Search
index (meridian-compliance-index) using a Markdown-header-aware chunking strategy
and the strict provenance schema required by ADR-007 and the D07 metadata contract.

Usage:
    python src/retrieval/ingestion.py --dry-run
        Validate chunking and metadata schema without connecting to Azure AI Search.
        Satisfies the D07 "demonstrably runnable" gate locally.

    python src/retrieval/ingestion.py
        Full run. Requires AZURE_SEARCH_ENDPOINT in .env and a reachable Azure AI
        Search instance with DefaultAzureCredential access.
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from azure.core.credentials import AzureKeyCredential, TokenCredential
from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

SearchCredential = TokenCredential | AzureKeyCredential

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INDEX_NAME = "meridian-compliance-index"
CORPUS_PATH = Path(__file__).resolve().parents[2] / "data" / "compliance_corpus"

# Vector dimension must match the embeddings model used in the full pipeline.
# Azure OpenAI text-embedding-3-small produces 1536-dim vectors.
VECTOR_DIMENSIONS = 1536

# ---------------------------------------------------------------------------
# Index schema
#
# Fields implement the full ADR-007 provenance contract plus D07 operational
# metadata minimums.  The schema is intentionally designed to support hybrid
# retrieval (keyword + vector) from the outset so that D08 can wire retrieval
# without a destructive index migration.
# ---------------------------------------------------------------------------

FIELDS: list[Any] = [
    # Key — globally unique per chunk
    SimpleField(
        name="chunk_id",
        type=SearchFieldDataType.String,
        key=True,
        filterable=True,
    ),
    # Document-level identity
    SimpleField(
        name="document_id",
        type=SearchFieldDataType.String,
        filterable=True,
        facetable=True,
    ),
    SimpleField(
        name="source_name",
        type=SearchFieldDataType.String,
        filterable=True,
    ),
    SimpleField(
        name="source_tier",
        type=SearchFieldDataType.Int32,
        filterable=True,
        sortable=True,
        facetable=True,
    ),
    SimpleField(
        name="document_version",
        type=SearchFieldDataType.String,
        filterable=True,
    ),
    # ADR-007 provenance fields
    SimpleField(
        name="origin_type",
        type=SearchFieldDataType.String,
        filterable=True,
        facetable=True,
    ),
    SimpleField(
        name="canonical_source_id",
        type=SearchFieldDataType.String,
        filterable=True,
    ),
    SimpleField(
        name="effective_from",
        type=SearchFieldDataType.DateTimeOffset,
        filterable=True,
        sortable=True,
    ),
    SimpleField(
        name="valid_until",
        type=SearchFieldDataType.DateTimeOffset,
        filterable=True,
        sortable=True,
    ),
    SimpleField(
        name="jurisdiction",
        type=SearchFieldDataType.String,
        filterable=True,
        facetable=True,
    ),
    SimpleField(
        name="amendment_of",
        type=SearchFieldDataType.String,
        filterable=True,
    ),
    # Conditional mirror fields (required only when origin_type == "mirror")
    SimpleField(
        name="mirror_of",
        type=SearchFieldDataType.String,
        filterable=True,
    ),
    SimpleField(
        name="mirror_last_synced",
        type=SearchFieldDataType.DateTimeOffset,
        filterable=True,
        sortable=True,
    ),
    # Ingestion audit fields
    SimpleField(
        name="ingested_at",
        type=SearchFieldDataType.DateTimeOffset,
        filterable=True,
        sortable=True,
    ),
    SimpleField(
        name="content_hash",
        type=SearchFieldDataType.String,
        filterable=True,
    ),
    # Structure-aware chunking fields
    SimpleField(
        name="section_path",
        type=SearchFieldDataType.String,
        filterable=True,
    ),
    # Searchable text fields
    SearchableField(name="title", type=SearchFieldDataType.String),
    SearchableField(name="content", type=SearchFieldDataType.String),
    # Vector field for hybrid retrieval (HNSW)
    SearchField(
        name="content_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=VECTOR_DIMENSIONS,
        vector_search_profile_name="meridian-vector-profile",
    ),
]

VECTOR_SEARCH_CONFIG = VectorSearch(
    algorithms=[HnswAlgorithmConfiguration(name="meridian-hnsw")],
    profiles=[
        VectorSearchProfile(
            name="meridian-vector-profile",
            algorithm_configuration_name="meridian-hnsw",
        )
    ],
)

# ---------------------------------------------------------------------------
# Front-matter parser
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?\n)---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """
    Parses YAML-style front-matter from a Markdown file.

    Returns (metadata_dict, body_text).  The metadata dict is keyed by the
    front-matter field names; values are raw strings.  The body_text is the
    document content after the closing --- delimiter.

    If no front-matter block is present the metadata dict is empty and the
    full text is returned as body_text.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    block = match.group(1)
    body = text[match.end():]
    metadata: dict[str, Any] = {}
    for line in block.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            metadata[key.strip()] = value.strip()

    return metadata, body


# ---------------------------------------------------------------------------
# Structure-aware Markdown chunker
# ---------------------------------------------------------------------------

_HEADER_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)


def chunk_markdown(
    body: str,
    document_id: str,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Splits a Markdown body into chunks at H1/H2/H3 header boundaries.

    Each chunk:
    - Inherits all document-level provenance metadata.
    - Records a section_path encoding the full heading hierarchy
      (e.g. "Annex XVII > Entry 28 — Lead > Scope"), preserving regulatory
      scope context for downstream citation and jurisdiction filtering.
    - Carries a content_hash for deduplication and change detection.
    - Carries a deterministic Azure Search-safe chunk_id derived from
      document_id, section_path, and content_hash.

    Rationale for structure-aware chunking (rather than fixed-size chunking):
    Fixed-size chunking without header awareness crosses section boundaries and
    produces three concrete failure modes for this corpus:
      1. Jurisdiction boundary crossing: adjacent EU and GB sections can merge
         into a single chunk, causing a UK supplier to be cited against EU-only
         obligations.
      2. Amendment lineage destruction: short amendment sections (e.g. "this
         entry replaces Entry 28 as of 2025-01-01") are absorbed into adjacent
         chunks, making the amendment_of provenance link meaningless at query
         time.
      3. Evidence packet readability: oversized fixed chunks return paragraphs
         burying the cited obligation inside regulatory boilerplate, raising
         cognitive load for the human compliance reviewer.

    Empty sections (header with no content body) are silently discarded.
    """
    ingested_at = datetime.now(timezone.utc).isoformat()
    chunks: list[dict[str, Any]] = []

    # Find all header positions and append a sentinel at end-of-body
    positions = [m.start() for m in _HEADER_RE.finditer(body)]
    positions.append(len(body))

    # Heading stack tracks active hierarchy: list of (level_int, heading_text)
    heading_stack: list[tuple[int, str]] = []

    # If there is a preamble before the first header, treat it as a chunk
    preamble_end = positions[0] if positions else len(body)
    preamble_content = body[:preamble_end].strip()
    if preamble_content:
        content_hash = hashlib.sha256(preamble_content.encode()).hexdigest()[:16]
        chunk_id = _make_chunk_id(
            document_id=document_id,
            section_path="(preamble)",
            content_hash=content_hash,
        )
        chunks.append(
            _build_chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                metadata=metadata,
                section_path="(preamble)",
                title=document_id,
                content=preamble_content,
                content_hash=content_hash,
                ingested_at=ingested_at,
            )
        )

    for i, start in enumerate(positions[:-1]):
        end = positions[i + 1]
        segment = body[start:end]

        header_match = _HEADER_RE.match(segment)
        if not header_match:
            # Should not occur given positions[] was built from _HEADER_RE,
            # but guard defensively.
            continue

        level = len(header_match.group(1))
        heading_text = header_match.group(2).strip()
        content = segment[header_match.end():].strip()

        # Maintain heading stack: pop any heading at same or deeper level
        heading_stack = [(lvl, txt) for lvl, txt in heading_stack if lvl < level]
        heading_stack.append((level, heading_text))

        if not content:
            continue

        section_path = " > ".join(txt for _, txt in heading_stack)
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        chunk_id = _make_chunk_id(
            document_id=document_id,
            section_path=section_path,
            content_hash=content_hash,
        )

        chunks.append(
            _build_chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                metadata=metadata,
                section_path=section_path,
                title=heading_text,
                content=content,
                content_hash=content_hash,
                ingested_at=ingested_at,
            )
        )

    return chunks


def _make_chunk_id(*, document_id: str, section_path: str, content_hash: str) -> str:
    """
    Builds a deterministic Azure Search-safe key for a chunk.

    The readable hierarchy stays in `section_path`; the key itself is hashed so
    that headings containing spaces, punctuation, or Unicode characters don't
    violate Azure AI Search key constraints.
    """
    raw_key = f"{document_id}::{section_path}::{content_hash}"
    return f"chunk-{hashlib.sha256(raw_key.encode('utf-8')).hexdigest()}"


def _build_search_credential() -> tuple[SearchCredential, str]:
    """
    Builds the Azure AI Search credential for this run.

    Prefer an explicit admin/query key when one is configured locally; otherwise
    fall back to DefaultAzureCredential for Entra ID / Azure CLI auth.
    """
    api_key = os.environ.get("AZURE_SEARCH_API_KEY")
    if api_key:
        return AzureKeyCredential(api_key), "api_key"
    return DefaultAzureCredential(), "default_azure_credential"


def _handle_search_auth_error(
    exc: HttpResponseError,
    *,
    operation: str,
    auth_mode: str,
) -> None:
    """
    Converts Azure AI Search auth failures into an actionable operator message.
    """
    if exc.status_code not in {401, 403}:
        raise exc

    if auth_mode == "api_key":
        logger.error(
            "Azure AI Search rejected the configured API key while attempting to %s. "
            "Check that AZURE_SEARCH_API_KEY is an admin key for '%s'.",
            operation,
            INDEX_NAME,
        )
    else:
        logger.error(
            "Azure AI Search denied the current Azure identity while attempting to %s. "
            "For index management the principal needs the 'Search Service Contributor' "
            "role; for document uploads it also needs 'Search Index Data Contributor'. "
            "Alternatively, set AZURE_SEARCH_API_KEY in .env to use key-based auth.",
            operation,
        )
    sys.exit(1)


def _build_chunk(
    *,
    chunk_id: str,
    document_id: str,
    metadata: dict[str, Any],
    section_path: str,
    title: str,
    content: str,
    content_hash: str,
    ingested_at: str,
) -> dict[str, Any]:
    """
    Constructs a fully-populated chunk document dict and validates the
    ADR-007 conditional mirror fields contract.

    Raises ValueError if origin_type == "mirror" but mirror_of or
    mirror_last_synced are absent, preventing silent provenance violations.
    """
    origin_type = metadata.get("origin_type", "origin")

    mirror_of: str | None = None
    mirror_last_synced: str | None = None
    if origin_type == "mirror":
        mirror_of = metadata.get("mirror_of") or None
        mirror_last_synced = metadata.get("mirror_last_synced") or None
        if not mirror_of or not mirror_last_synced:
            raise ValueError(
                f"Chunk '{chunk_id}': origin_type='mirror' requires both "
                "'mirror_of' and 'mirror_last_synced' in document front-matter "
                "(ADR-007 conditional mirror contract)."
            )

    chunk: dict[str, Any] = {
        "chunk_id": chunk_id,
        "document_id": document_id,
        "source_name": metadata.get("source_name", ""),
        "source_tier": int(metadata.get("source_tier", 3)),
        "origin_type": origin_type,
        "canonical_source_id": metadata.get("canonical_source_id", document_id),
        "effective_from": metadata.get("effective_from"),
        "valid_until": metadata.get("valid_until") or None,
        "jurisdiction": metadata.get("jurisdiction", ""),
        "document_version": metadata.get("document_version", "1.0"),
        "amendment_of": metadata.get("amendment_of") or None,
        "mirror_of": mirror_of,
        "mirror_last_synced": mirror_last_synced,
        "ingested_at": ingested_at,
        "content_hash": content_hash,
        "section_path": section_path,
        "title": title,
        "content": content,
        # content_vector is populated by the embeddings service in the full
        # pipeline.  The dry-run and index-creation path leave it empty.
        "content_vector": [],
    }

    _validate_required_fields(chunk)
    return chunk


_REQUIRED_FIELDS = [
    "chunk_id",
    "document_id",
    "source_name",
    "source_tier",
    "origin_type",
    "canonical_source_id",
    "effective_from",
    "jurisdiction",
    "document_version",
    "ingested_at",
    "content_hash",
    "section_path",
    "title",
    "content",
]


def _validate_required_fields(chunk: dict[str, Any]) -> None:
    """
    Validates that all mandatory metadata fields are present and non-empty.
    Raises ValueError on first violation to fail fast during ingestion.
    """
    for field in _REQUIRED_FIELDS:
        value = chunk.get(field)
        if value is None or value == "" or (isinstance(value, list) and len(value) == 0 and field != "content_vector"):
            # content_vector is intentionally empty in dry-run / pre-embedding runs
            if field == "content_vector":
                continue
            raise ValueError(
                f"Chunk '{chunk.get('chunk_id', '<unknown>')}': "
                f"required field '{field}' is missing or empty."
            )


# ---------------------------------------------------------------------------
# Azure AI Search index management
# ---------------------------------------------------------------------------


def ensure_index(index_client: SearchIndexClient) -> None:
    """
    Creates the meridian-compliance-index if it does not exist.
    If the index already exists, logs and returns without modification.
    """
    index = SearchIndex(
        name=INDEX_NAME,
        fields=FIELDS,
        vector_search=VECTOR_SEARCH_CONFIG,
    )
    try:
        index_client.get_index(INDEX_NAME)
        logger.info("Index '%s' already exists — skipping creation.", INDEX_NAME)
    except HttpResponseError as exc:
        if exc.status_code != 404:
            raise
        index_client.create_index(index)
        logger.info("Created index '%s'.", INDEX_NAME)


# ---------------------------------------------------------------------------
# Ingestion pipeline
# ---------------------------------------------------------------------------


def ingest_corpus(dry_run: bool = False) -> None:
    """
    Main ingestion pipeline.

    In dry-run mode:
    - No Azure connection is established.
    - All documents in the corpus are parsed, chunked, and validated.
    - Each chunk is printed to stdout as JSON (minus the empty vector field).
    - Exits non-zero if any document fails schema validation.

    In live mode:
    - Reads AZURE_SEARCH_ENDPOINT from the environment.
    - Uses DefaultAzureCredential (honours managed identity, Azure CLI, env vars).
    - Ensures the index exists then upserts all chunks in batches.
    """
    if not CORPUS_PATH.exists():
        logger.error("Corpus path does not exist: %s", CORPUS_PATH)
        sys.exit(1)

    markdown_files = sorted(CORPUS_PATH.glob("*.md"))
    if not markdown_files:
        logger.warning("No .md files found in %s", CORPUS_PATH)
        return

    credential: SearchCredential | None = None
    index_client: SearchIndexClient | None = None
    search_client: SearchClient | None = None
    auth_mode = "unknown"

    if not dry_run:
        endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
        if not endpoint:
            logger.error(
                "AZURE_SEARCH_ENDPOINT is not set. "
                "Set it in .env or use --dry-run for local validation."
            )
            sys.exit(1)
        credential, auth_mode = _build_search_credential()
        index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
        try:
            ensure_index(index_client)
        except HttpResponseError as exc:
            _handle_search_auth_error(
                exc,
                operation="inspect or create the search index",
                auth_mode=auth_mode,
            )
        search_client = SearchClient(
            endpoint=endpoint,
            index_name=INDEX_NAME,
            credential=credential,
        )

    total_chunks = 0
    mirror_staleness_violations = 0
    run_id = _generate_run_id()

    for filepath in markdown_files:
        raw = filepath.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(raw)
        document_id = fm.get("document_id", filepath.stem)
        logger.info(
            "Processing '%s' → document_id='%s'  tier=%s  origin_type=%s",
            filepath.name,
            document_id,
            fm.get("source_tier", "?"),
            fm.get("origin_type", "?"),
        )

        try:
            chunks = chunk_markdown(body, document_id, fm)
        except ValueError as exc:
            logger.error("Schema validation failed for '%s': %s", filepath.name, exc)
            sys.exit(1)

        total_chunks += len(chunks)

        # Check mirror staleness
        for chunk in chunks:
            if chunk.get("origin_type") == "mirror" and chunk.get("mirror_last_synced"):
                if _is_mirror_stale(chunk["mirror_last_synced"]):
                    mirror_staleness_violations += 1
                    logger.warning(
                        "Stale mirror detected: chunk '%s' mirror_last_synced=%s",
                        chunk["chunk_id"],
                        chunk["mirror_last_synced"],
                    )

        if dry_run:
            for chunk in chunks:
                display = {k: v for k, v in chunk.items() if k != "content_vector"}
                logger.info("[DRY-RUN] Chunk: %s", json.dumps(display, default=str))
            logger.info(
                "[DRY-RUN] %d chunks validated from '%s'.",
                len(chunks),
                filepath.name,
            )
        else:
            assert search_client is not None
            # Azure AI Search SDK accepts up to 1000 documents per upload call
            try:
                results = search_client.upload_documents(chunks)
            except HttpResponseError as exc:
                _handle_search_auth_error(
                    exc,
                    operation="upload documents to the search index",
                    auth_mode=auth_mode,
                )
            failed = [r for r in results if not r.succeeded]
            if failed:
                failed_keys = ", ".join(
                    str(getattr(result, "key", "<unknown>"))
                    for result in failed[:5]
                )
                logger.error(
                    "%d chunk(s) failed to upsert from '%s'.",
                    len(failed),
                    filepath.name,
                )
                logger.error(
                    "Aborting ingestion after Azure rejected chunk upload(s): %s",
                    failed_keys,
                )
                sys.exit(1)
            else:
                logger.info(
                    "Upserted %d chunks from '%s'.",
                    len(chunks),
                    filepath.name,
                )

    _emit_audit_event(
        run_id=run_id,
        document_count=len(markdown_files),
        chunk_count=total_chunks,
        mirror_staleness_violations=mirror_staleness_violations,
        dry_run=dry_run,
    )


def _is_mirror_stale(mirror_last_synced: str) -> bool:
    """
    Returns True if mirror_last_synced is older than 24 hours from now.
    Parses ISO 8601 strings with or without timezone info.
    """
    try:
        synced_at = datetime.fromisoformat(mirror_last_synced)
        if synced_at.tzinfo is None:
            synced_at = synced_at.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - synced_at).total_seconds() / 3600
        return age_hours > 24
    except ValueError:
        logger.warning("Could not parse mirror_last_synced value: %s", mirror_last_synced)
        return True


def _generate_run_id() -> str:
    """Generates a simple run ID based on the current UTC timestamp."""
    return datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")


def _emit_audit_event(
    *,
    run_id: str,
    document_count: int,
    chunk_count: int,
    mirror_staleness_violations: int,
    dry_run: bool,
) -> None:
    """
    Emits a structured ingestion audit event to stdout / the log.
    In production this would be forwarded to Azure Monitor / LangSmith.
    """
    event = {
        "event": "corpus_ingestion_complete",
        "run_id": run_id,
        "dry_run": dry_run,
        "document_count": document_count,
        "chunk_count": chunk_count,
        "mirror_staleness_violations": mirror_staleness_violations,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("AUDIT: %s", json.dumps(event))
    if mirror_staleness_violations > 0:
        logger.warning(
            "ALERT: %d mirror staleness violation(s) detected. "
            "The Tier 2 MVP override is suspended for stale documents until "
            "mirrors are re-synced.",
            mirror_staleness_violations,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Meridian compliance corpus ingestion pipeline (structure-aware).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python src/retrieval/ingestion.py --dry-run\n"
            "      Validate chunking and metadata without Azure connection.\n\n"
            "  python src/retrieval/ingestion.py\n"
            "      Full run. Requires AZURE_SEARCH_ENDPOINT in .env.\n"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Parse, chunk, and validate all corpus documents without connecting "
            "to Azure AI Search. Suitable for local CI verification."
        ),
    )
    args = parser.parse_args()
    ingest_corpus(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
