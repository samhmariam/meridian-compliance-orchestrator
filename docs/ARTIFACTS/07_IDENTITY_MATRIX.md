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
6. `Meridian Admin Group` (Group): Platform operators needing to inspect Azure Monitor, OTEL traces inside LangSmith, and deployment logs to debug incidents.

### 2. Access matrix

Map each principal to service/resource, required role, scope, and reason.

**Fill here:**

| Identity | Type | Scope | Can read | Can write | Cannot access | Justification |
|---|---|---|---|---|---|---|
| `mi-meridian-graph` | Managed identity | Executing ACA | AI Search (`Search Index Data Reader`), Key Vault (`Key Vault Secrets User`) | Cosmos DB State (`Cosmos DB Built-in Data Contributor`) | ERP System Credentials, RBAC Config, Infrastructure Bicep | LangGraph needs to synthesize LLM data and check states. Denying write access to ERP stops autonomous triggers. |
| `mi-meridian-ingest` | Managed identity | Backchannel ACA | Blob Storage Storage (`Storage Blob Data Reader`) | AI Search (`Search Index Data Contributor`) | ERP System, Cosmos DB State | Limits vector sync pipelines from tampering with active compliance decisions mapped in Cosmos DB. |
| `mi-meridian-erp-activator` | Managed identity | Write ACA | Key Vault (`Key Vault Secrets User` - ONLY ERP Auth subset) | ERP Subnets / APIs | AI Search, Cosmos DB, Azure OpenAI | Narrow token scopes execution logic down just to invoking external downstream systems after receiving graph signal. |
| `mi-meridian-deployer` | Federated GitHub | Deployment | Subscription diagnostic logs | `Contributor` at designated RG level, `Role Based Access Control Administrator` (narrowed condition) | Cosmos DB (Data Plane), Key Vault (Data Plane Secrets) | Deploys ACA containers and networks but purposefully cannot extract business keys or read production DB state. |
| `Meridian Compliance Officer` | Entra ID Group | Web Client | Graph state (Review UI) | Cosmos DB approval mutations | Azure Portal Configuration, Key Vaults | Keeps humans strictly bound to their business duty, not IT infrastructure tampering. |
| `Meridian Admin Group` | Entra ID Group | Debugger | Log Analytics, Langsmith OTEL, Application Insights | - | Cosmos DB Data Plane, ERP write tokens | Diagnostic plane separation; IT admins cannot approve compliance flows, only fix infrastructure. |

### 3. Read/write/admin separation

Show distinct control planes.

**Fill here:**

- **Read Plane (Synthesis):** Primarily governed by `mi-meridian-graph` traversing AI logic and state observation.
- **Write Plane (Irreversible):** Sequestered to `mi-meridian-erp-activator`. Human approval (via `Meridian Compliance Officer`) explicitly sits in front of this plane acting as the gatekeeper.
- **Admin/Pipeline Plane:** Governed by `mi-meridian-deployer` for CI/CD mutation control, and the `Meridian Admin Group` for Azure-native diagnostic observation (OTel/Log Analytics). Neither group has rights to inject data into Cosmos DB to mimic a legal compliance action.

### 4. Credential strategy

State managed identity, Key Vault, and any exceptions.

**Fill here:**

All API Keys (e.g. `LANGSMITH_API_KEY`, `AZURE_OPENAI_KEY`) belong strictly to an Azure Key Vault setup. `DefaultAzureCredential` natively evaluates RBAC and permits our Managed Identities (`Key Vault Secrets User`) to pull these credentials into local memory at runtime inside Azure Container Apps. There are zero `.env` values holding secrets deployed. The code has been rewritten (via `auth.py`) to mandate live execution to Azure SDKs over local file dumps.

### 5. Local dev posture

Explain how local dev credentials differ from deployed runtime.

**Fill here:**

Locally, developers do not use a hardcoded `.env` for secrets. Executing our runtime locally utilizes `DefaultAzureCredential`. The `azure-identity` package falls back to evaluating the developer's `AzureCliCredential` (specifically resolving to `az login`). The developer must personally be a `Key Vault Secrets User` in the test-vault to run the orchestration loop, preserving absolute parity between Local Dev context execution and Container App managed-identity execution.

### 6. Open issues and risks

Anything not yet implemented or proven.

**Fill here:**

- CI/CD mapping of `mi-meridian-deployer` requires explicitly locking down OpenID Connect (OIDC) federation purely to the `main` branch of this repository. Current RBAC Bicep scopes may need to be tightened natively upon first full deployment execution.

## Evidence required for acceptance

- [x] No runtime identity has RG Contributor.
- [x] Key Vault access path is explicit.
- [x] Local and deployed auth paths are both understood (captured via telemetry via `auth_smoke_test.py`).

## Review prompts

- What decision would this artifact allow an instructor, operator, or architect to make?
  - Clear paths to diagnose unauthorized lateral movement if telemetry indicates `mi-meridian-graph` attempting an ERP write.
- Where does this artifact connect to the running Meridian system?
  - The Bicep deployment directly translates Section 2 into `roleAssignments`.
- What would fail if this artifact were wrong or missing?
  - Accidental `Contributor` defaults would give LLM-prompted endpoints lateral surface code to wipe the subscription or harvest generic API keys.
