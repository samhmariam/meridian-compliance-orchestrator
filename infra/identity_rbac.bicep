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

@description('The principal ID of the Meridian Compliance Officer group')
param complianceOfficerGroupId string

@description('The name of the Azure AI Search service used by the graph and ingestion planes')
param searchServiceName string

@description('The name of the Cosmos DB account storing workflow state')
param cosmosAccountName string

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

@description('The dev Cosmos DB account mode. Use serverless by default, or freeTier if you prefer the free-tier account model.')
@allowed([
  'serverless'
  'freeTier'
])
param cosmosAccountMode string = 'serverless'

@description('The Cosmos DB data-plane scope for the Graph Host identity. Use / for the account or a narrower database/container path.')
param graphCosmosScope string = '/'

@description('The Cosmos DB data-plane scope for the Compliance Officer group. Use / for the account or a narrower database/container path.')
param complianceOfficerCosmosScope string = '/'

// Role Definition IDs
var roleKeyVaultSecretsUser = '4633458b-17de-408a-b874-0445c86b69e6'
var roleSearchIndexDataReader = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
var roleSearchIndexDataContributor = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var roleCosmosDBBuiltInContributor = '00000000-0000-0000-0000-000000000002'

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

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: cosmosAccountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    capabilities: cosmosAccountMode == 'serverless' ? [
      {
        name: 'EnableServerless'
      }
    ] : []
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    databaseAccountOfferType: 'Standard'
    disableKeyBasedMetadataWriteAccess: false
    disableLocalAuth: false
    enableFreeTier: cosmosAccountMode == 'freeTier'
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    ipRules: []
    isVirtualNetworkFilterEnabled: false
    locations: [
      {
        failoverPriority: 0
        isZoneRedundant: false
        locationName: location
      }
    ]
    minimalTlsVersion: 'Tls12'
    networkAclBypass: 'None'
    networkAclBypassResourceIds: []
    publicNetworkAccess: 'Enabled'
  }
}

var cosmosBuiltInContributorRoleDefinitionId = '${cosmosAccount.id}/sqlRoleDefinitions/${roleCosmosDBBuiltInContributor}'
var graphCosmosAssignmentScope = startsWith(graphCosmosScope, '/subscriptions/')
  ? graphCosmosScope
  : graphCosmosScope == '/'
    ? '${cosmosAccount.id}/'
    : '${cosmosAccount.id}${graphCosmosScope}'
var complianceOfficerCosmosAssignmentScope = startsWith(complianceOfficerCosmosScope, '/subscriptions/')
  ? complianceOfficerCosmosScope
  : complianceOfficerCosmosScope == '/'
    ? '${cosmosAccount.id}/'
    : '${cosmosAccount.id}${complianceOfficerCosmosScope}'

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

resource graphCosmosAccess 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2022-11-15' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, graphIdentityObjectId, graphCosmosAssignmentScope, roleCosmosDBBuiltInContributor)
  properties: {
    principalId: graphIdentityObjectId
    roleDefinitionId: cosmosBuiltInContributorRoleDefinitionId
    scope: graphCosmosAssignmentScope
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

resource complianceOfficerCosmosAccess 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2022-11-15' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, complianceOfficerGroupId, complianceOfficerCosmosAssignmentScope, roleCosmosDBBuiltInContributor)
  properties: {
    principalId: complianceOfficerGroupId
    roleDefinitionId: cosmosBuiltInContributorRoleDefinitionId
    scope: complianceOfficerCosmosAssignmentScope
  }
}
