# 07_IDENTITY_MATRIX

## Role in the programme

- **Primary module:** M01
- **First due:** D04
- **Capstone anchor:** `meridian-compliance-orchestrator`

## Purpose

Describe least-privilege identity boundaries across the Meridian system.

## How to use this template

Complete every section with Meridian-specific content. Do not submit a generic framework answer. Where a section does not apply, explain why it does not apply in the capstone rather than leaving it blank.

## Required sections

### 1. Principals

List all machine and human identities.

**Fill here:**

*Machine Identities (Managed)*:
1. `mi-meridian-graph`: Execution host identity for the primary LangGraph orchestration loop.
2. `mi-meridian-ingest`: Ingestion pipeline identity specifically designated for populating the RAG/Vector store during background syncs.
3. `mi-meridian-erp-activator`: Isolated write-node token identity, scoped completely separate from the Graph to prevent unintended hallucinated ERP hits.
4. `mi-meridian-deployer`: CI/CD Pipeline federated identity (GitHub Actions matching workflow federated credentials) for provisioning Azure resources (ACA, Key Vaults) and container images.

*Human Identities (Entra ID)*:
5. `Meridian Compliance Officer` (Group): The human review authority designated to approve/reject activation sequences within the graph.
6. `Meridian Admin Group` (Group): Platform operators needing to inspect Azure Monitor (Log Analytics / Application Insights) and deployment logs to debug incidents.
7. `PostgreSQL Bootstrap Admin` (Dedicated Entra Principal): A tightly held setup-only identity used to create scoped PostgreSQL roles for application services. It is never used by the graph runtime or the approver UI.

### 2. Access matrix

Map each principal to service/resource, required role, scope, and reason.

**Fill here:**

| Identity | Type | Scope | Can read | Can write | Cannot access | Justification |
|---|---|---|---|---|---|---|
| `mi-meridian-graph` | Managed identity | Executing ACA | AI Search (`Search Index Data Reader`), Key Vault (`Key Vault Secrets User`) | PostgreSQL Checkpoint Schema (`Scoped DB Role via Entra Auth`) | ERP System Credentials, PostgreSQL Server Admin, RBAC Config, Infrastructure Bicep | LangGraph needs to synthesize LLM data and checkpoint workflow state, but it must not hold server-level database administration rights. |
| `mi-meridian-ingest` | Managed identity | Backchannel ACA | Blob Storage Storage (`Storage Blob Data Reader`) | AI Search (`Search Index Data Contributor`) | ERP System, PostgreSQL State | Limits vector sync pipelines from tampering with active compliance decisions mapped in PostgreSQL. |
| `mi-meridian-erp-activator` | Managed identity | Write ACA | Key Vault (`Key Vault Secrets User` - ONLY ERP Auth subset) | ERP Subnets / APIs | AI Search, PostgreSQL DB, Azure OpenAI | Narrow token scopes execution logic down just to invoking external downstream systems after receiving graph signal. |
| `mi-meridian-deployer` | Federated GitHub | Deployment | Subscription diagnostic logs | `Contributor` at designated RG level, `Role Based Access Control Administrator` (narrowed condition) | PostgreSQL (Data Plane), Key Vault (Data Plane Secrets) | Deploys ACA containers and networks but purposefully cannot extract business keys or read production DB state. |
| `Meridian Compliance Officer` | Entra ID Group | Web Client | Graph state (Review UI) | Approval decisions via Review Web API only | PostgreSQL Data Plane, Azure Portal Configuration, Key Vaults | Keeps humans strictly bound to their business duty while preventing direct checkpoint mutations outside the audited API boundary. |
| `Meridian Admin Group` | Entra ID Group | Debugger | Azure Monitor (Log Analytics / Application Insights), LangSmith OTEL | - | PostgreSQL Data Plane, ERP write tokens | Diagnostic plane separation; IT admins cannot approve compliance flows, only fix infrastructure. |
| `PostgreSQL Bootstrap Admin` | Dedicated Entra principal | One-time DB bootstrap | PostgreSQL server metadata and role catalog | Scoped PostgreSQL roles for service identities | ERP System, Azure AI Search, runtime secrets | This identity exists only to create and rotate non-admin database roles after server provisioning. It is not part of the steady-state runtime path. |

### 3. Read/write/admin separation

Show distinct control planes.

**Fill here:**

- **Read Plane (Synthesis):** Primarily governed by `mi-meridian-graph` traversing AI logic and state observation.
- **Write Plane (Irreversible):** Sequestered to `mi-meridian-erp-activator`. Human approval (via `Meridian Compliance Officer`) explicitly sits in front of this plane acting as the gatekeeper.
- **Admin/Pipeline Plane:** Governed by `mi-meridian-deployer` for CI/CD mutation control, the `Meridian Admin Group` for Azure-native diagnostic observation (Azure Monitor (Log Analytics / Application Insights)), and the separate `PostgreSQL Bootstrap Admin` for one-time database role bootstrap only. Neither the pipeline identity nor human approvers have rights to mutate checkpoint data directly.

### 4. Credential strategy

State managed identity, Key Vault, and any exceptions.

**Fill here:**

All API Keys (e.g. `LANGSMITH_API_KEY`, `AZURE_OPENAI_KEY`) belong strictly to an Azure Key Vault setup. `DefaultAzureCredential` natively evaluates RBAC and permits our Managed Identities (`Key Vault Secrets User`) to pull these credentials into local memory at runtime inside Azure Container Apps. There are zero `.env` values holding secrets deployed. The code has been rewritten (via `auth.py`) to mandate live execution to Azure SDKs over local file dumps.
For PostgreSQL specifically, the application exchanges an Entra token for a connection and authenticates as a constrained database role; server-level administrators are reserved for the bootstrap identity only.

### 5. Local dev posture

Explain how local dev credentials differ from deployed runtime.

**Fill here:**

Locally, developers do not use a hardcoded `.env` for secrets. Executing our runtime locally utilizes `DefaultAzureCredential`. The `azure-identity` package falls back to evaluating the developer's `AzureCliCredential` (specifically resolving to `az login`). The developer must personally be a `Key Vault Secrets User` in the test-vault to run the orchestration loop, preserving absolute parity between Local Dev context execution and Container App managed-identity execution.

### 6. Open issues and risks

Anything not yet implemented or proven.

**Fill here:**

- CI/CD mapping of `mi-meridian-deployer` requires explicitly locking down OpenID Connect (OIDC) federation purely to the `main` branch of this repository. Current RBAC Bicep scopes may need to be tightened natively upon first full deployment execution.
- Scoped PostgreSQL roles for `mi-meridian-graph` and the Review Web API still need a post-deployment SQL bootstrap step. Those roles are intentionally not granted through ARM/Bicep server-admin assignments.

## Evidence required for acceptance

- [x] No runtime identity has RG Contributor.
- [x] Key Vault access path is explicit.
- [x] Local and deployed auth paths are both understood (captured via telemetry via `auth_smoke_test.py`).

## Review prompts

- What decision would this artifact allow an instructor, operator, or architect to make?
  - Clear paths to diagnose unauthorized lateral movement if telemetry indicates `mi-meridian-graph` attempting an ERP write.
- Where does this artifact connect to the running Meridian system?
  - The Bicep deployment translates the Azure RBAC and server-auth boundaries, while a separate PostgreSQL bootstrap step maps Entra principals to constrained database roles.
- What would fail if this artifact were wrong or missing?
  - Accidental `Contributor` defaults would give LLM-prompted endpoints lateral surface code to wipe the subscription or harvest generic API keys.
