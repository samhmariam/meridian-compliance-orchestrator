---
document_id: OFSI-SANCTIONS-SIM-2024Q4
source_name: OFSI Sanctions Simulator — Consolidated List Q4 2024
source_tier: 2
origin_type: mirror
canonical_source_id: OFSI-CONSOLIDATED-LIST-2024Q4
effective_from: 2024-10-01T00:00:00Z
jurisdiction: GB
document_version: 2024Q4.1
mirror_of: OFSI-CONSOLIDATED-LIST-2024Q4
mirror_last_synced: 2026-04-18T06:00:00Z
---

# OFSI Sanctions Simulator — Consolidated Designated Persons List (Q4 2024)

This document is a **Tier 2 operational mirror** of the Office of Financial
Sanctions Implementation (OFSI) consolidated designated persons list, snapshot
Q4 2024.  It is maintained as a local simulator dataset for the Meridian
qualification workflow and must not be treated as the authoritative legal source.

The authoritative source is the OFSI published list at
https://www.gov.uk/government/publications/financial-sanctions-consolidated-list-of-targets.

**MVP Authority Exemption notice:** This mirror is eligible for the Tier 2
override to unblock ERP activation only when `mirror_last_synced` is within
24 hours of the qualification timestamp, as defined in
`08_SOURCE_OF_TRUTH_MATRIX.md` Section 3 and `09_GROUNDING_POLICY.md` Section 6.

## Designated Entity Simulator Entries

### Entry S-001: Acme Chemical Holdings Ltd

**Entity type:** Corporate  
**Aliases:** Acme Chem, ACH Holdings  
**Jurisdiction of incorporation:** GB  
**Status:** DESIGNATED  
**Designation date:** 2023-05-12  
**Applicable regime:** UK Financial Sanctions (Russia)  
**Basis:** Financial services prohibition, asset freeze  

Suppliers matching this entity name or any recorded alias must be flagged
`SANCTIONS_BLOCKED` regardless of REACH compliance outcome.  ERP activation
is prohibited until a compliance officer resolves the match via the human
approval gate.

### Entry S-002: Nordhaven Industrials GmbH

**Entity type:** Corporate  
**Aliases:** Nordhaven AG  
**Jurisdiction of incorporation:** DE  
**Status:** DESIGNATED  
**Designation date:** 2024-02-28  
**Applicable regime:** UK Financial Sanctions (Iran)  
**Basis:** Proliferation financing prohibition  

### Entry S-003: Coastal Polymers Sdn Bhd

**Entity type:** Corporate  
**Aliases:** CP Sdn Bhd, Coastal Poly  
**Jurisdiction of incorporation:** MY  
**Status:** REMOVED — designation lifted 2024-09-30  
**Applicable regime:** UK Financial Sanctions (Myanmar)  
**Basis:** Designation lifted following policy review  

> **Retrieval note:** This entry's designation was removed effective
> 2024-09-30.  Retrieval queries using `valid_until` filters will correctly
> exclude this entry when the qualification date is after 2024-09-30.
> An earlier snapshot ingested without `valid_until` set would erroneously
> classify this supplier as sanctioned — demonstrating why freshness
> enforcement is a hard gate, not a scoring preference.

## Scope Statement

This simulator covers GB-regime sanctions only.  For EU sanctions under
Council Regulation (EU) No 269/2014, a separate corpus entry is required.
Cross-jurisdiction contamination of sanctions results is prevented by the
`jurisdiction` hard-filter applied at retrieval time.

## Mirror Sync Audit

| Sync timestamp | Record count | Delta vs prior |
|---|---|---|
| 2026-04-18T06:00:00Z | 3 (simulator) | +0 |
| 2026-04-17T06:00:00Z | 3 (simulator) | +0 |
| 2026-01-15T09:00:00Z | 3 (simulator) | +1 (Entry S-003 removal recorded) |
