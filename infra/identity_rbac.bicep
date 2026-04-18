@description('The Azure region for the Day 04 identity resources')
param location string = resourceGroup().location

@description('The name of the Key Vault housing the secrets')
param keyVaultName string

@description('The names of the Key Vault secrets the execution Graph Host identity may read')
param graphSecretNames array

@description('The names of the Key Vault secrets the ERP Writer identity may read')
param erpSecretNames array

@description('The object ID of the execution Graph Host identity')
param graphIdentityObjectId string

@description('The object ID of the Ingestion Identity')
param ingestIdentityObjectId string

@description('The object ID of the ERP Writer identity')
param erpWriterIdentityObjectId string

@description('The name of the Azure AI Search service used by the graph and ingestion planes')
param searchServiceName string

@description('The name of the Azure Database for PostgreSQL Flexible Server storing workflow state')
param postgresServerName string

@description('Optional dedicated Entra principal object ID used only to bootstrap PostgreSQL database roles')
param postgresBootstrapAdminObjectId string = ''

@description('Optional dedicated Entra principal display name used only to bootstrap PostgreSQL database roles')
param postgresBootstrapAdminPrincipalName string = ''

@description('Principal type for the dedicated PostgreSQL bootstrap admin')
@allowed([
  'Group'
  'ServicePrincipal'
  'User'
])
param postgresBootstrapAdminPrincipalType string = 'Group'

@description('The Key Vault soft delete retention period in days')
@minValue(7)
@maxValue(90)
param keyVaultSoftDeleteRetentionDays int = 90

@description('The SKU for the Azure AI Search service. Use free for a single low-cost dev service, or basic if you need a paid tier.')
@allowed([
  'free'
  'basic'
])
param searchSkuName string = 'free'

@description('The number of Azure AI Search replicas')
@minValue(1)
param searchReplicaCount int = 1

@description('The number of Azure AI Search partitions')
@minValue(1)
param searchPartitionCount int = 1


// Role Definition IDs
var roleKeyVaultSecretsUser = '4633458b-17de-408a-b874-0445c86b69e6'
var roleSearchIndexDataReader = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
var roleSearchIndexDataContributor = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'

// Provision the bounded dev resources so the RBAC topology is self-contained.
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    accessPolicies: []
    enableRbacAuthorization: true
    enableSoftDelete: true
    publicNetworkAccess: 'enabled'
    sku: {
      family: 'A'
      name: 'standard'
    }
    softDeleteRetentionInDays: keyVaultSoftDeleteRetentionDays
    tenantId: tenant().tenantId
  }
}

resource graphSecrets 'Microsoft.KeyVault/vaults/secrets@2022-07-01' existing = [for secretName in graphSecretNames: {
  parent: kv
  name: secretName
}]

resource erpSecrets 'Microsoft.KeyVault/vaults/secrets@2022-07-01' existing = [for secretName in erpSecretNames: {
  parent: kv
  name: secretName
}]

resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  properties: {
    authOptions: {
      apiKeyOnly: {}
    }
    disableLocalAuth: false
    hostingMode: 'default'
    partitionCount: searchPartitionCount
    publicNetworkAccess: 'enabled'
    replicaCount: searchReplicaCount
    semanticSearch: 'free'
  }
  sku: {
    name: searchSkuName
  }
}

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: postgresServerName
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Disabled'
      tenantId: tenant().tenantId
    }
  }
}

// ----------------------------------------------------
// Plane 1: Reading/Execution (Graph Host)
// ----------------------------------------------------

// The graph host only reads the explicit secrets it needs, not the entire vault.
resource graphKvAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (secretName, index) in graphSecretNames: {
  name: guid(graphSecrets[index].id, graphIdentityObjectId, roleKeyVaultSecretsUser)
  scope: graphSecrets[index]
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleKeyVaultSecretsUser)
    principalId: graphIdentityObjectId
    principalType: 'ServicePrincipal'
  }
}]

resource graphSearchAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, graphIdentityObjectId, roleSearchIndexDataReader)
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleSearchIndexDataReader)
    principalId: graphIdentityObjectId
    principalType: 'ServicePrincipal'
  }
}

// Runtime access is intentionally not granted as a server administrator.
// Scoped database roles are bootstrapped separately by a dedicated admin identity.
resource postgresBootstrapAdmin 'Microsoft.DBforPostgreSQL/flexibleServers/administrators@2023-12-01-preview' = if (!empty(postgresBootstrapAdminObjectId) && !empty(postgresBootstrapAdminPrincipalName)) {
  parent: postgresServer
  name: postgresBootstrapAdminObjectId
  properties: {
    principalType: postgresBootstrapAdminPrincipalType
    principalName: postgresBootstrapAdminPrincipalName
    tenantId: tenant().tenantId
  }
}

// ----------------------------------------------------
// Plane 2: Ingestion
// ----------------------------------------------------

resource ingestSearchAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, ingestIdentityObjectId, roleSearchIndexDataContributor)
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleSearchIndexDataContributor)
    principalId: ingestIdentityObjectId
    principalType: 'ServicePrincipal'
  }
}

// ----------------------------------------------------
// Plane 3: Writing (ERP Activator)
// ----------------------------------------------------

// The ERP writer gets secret access only to the ERP credentials it needs.
resource erpKvAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (secretName, index) in erpSecretNames: {
  name: guid(erpSecrets[index].id, erpWriterIdentityObjectId, roleKeyVaultSecretsUser)
  scope: erpSecrets[index]
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleKeyVaultSecretsUser)
    principalId: erpWriterIdentityObjectId
    principalType: 'ServicePrincipal'
  }
}]

// ----------------------------------------------------
// Plane 4: Approvers (Humans)
// ----------------------------------------------------
// Approvers authenticate only to the Review Web API and never receive direct PostgreSQL admin rights.
