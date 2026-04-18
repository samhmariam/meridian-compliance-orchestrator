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
param complianceOfficerGroupId = 'a38a350b-1e5a-410b-a462-1d9dd638bbe0'

param searchServiceName = 'srch-meridian-dev-free'
param searchSkuName = 'free'
param cosmosAccountName = 'cosmos-meridian-dev'
param cosmosAccountMode = 'serverless'

// Default to the account root until the dev database/container paths are finalized.
param graphCosmosScope = '/'
param complianceOfficerCosmosScope = '/'
