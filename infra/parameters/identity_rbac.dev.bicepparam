using '../identity_rbac.bicep'

// Sample dev parameters for the Day 04 identity topology module.
// Replace the Entra object IDs before deploying.

param keyVaultName = 'kv-meridian-dev-uksouth'
param graphSecretNames = [
  'langsmith-api-key'
  'azure-openai-key'
]
param erpSecretNames = [
  'erp-api-client-id'
  'erp-api-client-secret'
]

param graphIdentityObjectId = 'd8520947-8807-48f2-aca0-b6e818d06ab6'
param ingestIdentityObjectId = '26c77517-028e-431a-8837-52240c52b1c8'
param erpWriterIdentityObjectId = '9df9d8d8-31fa-4151-9c4d-208c6326f881'

param searchServiceName = 'srch-meridian-dev-free'
param searchSkuName = 'free'
param postgresServerName = 'psql-meridian-dev'

// Optional dedicated PostgreSQL bootstrap admin used once to create scoped DB roles.
// Leave unset here so runtime and approver identities are not granted server-level admin.
