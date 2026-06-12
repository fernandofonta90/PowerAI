// PowerAI — infraestructura base en Azure (esqueleto de Fase 1).
//
// Provisiona el andamiaje Azure-nativo del ADR-0001: Container Apps para la API
// y el frontend, PostgreSQL Flexible Server, Azure Cache for Redis y una cuenta
// de Storage para los datasets Parquet y archivos originales.
//
// ESTADO: esqueleto NO desplegado en M1. Pendiente de validación con Global
// Technology (networking, private endpoints, Key Vault, Entra ID). Los secretos
// jamás se fijan aquí: se inyectan desde Key Vault en el despliegue.

targetScope = 'resourceGroup'

@description('Sufijo de entorno: dev | test | prod.')
@allowed(['dev', 'test', 'prod'])
param entorno string = 'dev'

@description('Región de Azure para todos los recursos.')
param ubicacion string = resourceGroup().location

@description('Prefijo de nombres de recursos.')
param prefijo string = 'powerai'

@description('Administrador de PostgreSQL.')
param pgAdminUsuario string

@description('Contraseña del administrador de PostgreSQL (inyectar desde Key Vault).')
@secure()
param pgAdminPassword string

var sufijo = '${prefijo}-${entorno}'
var nombreStorage = toLower(replace('${prefijo}${entorno}sa', '-', ''))

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${sufijo}'
  location: ubicacion
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: nombreStorage
  location: ubicacion
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: 'redis-${sufijo}'
  location: ubicacion
  properties: {
    sku: { name: 'Basic', family: 'C', capacity: 0 }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: 'pg-${sufijo}'
  location: ubicacion
  sku: { name: 'Standard_B1ms', tier: 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: pgAdminUsuario
    administratorLoginPassword: pgAdminPassword
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7 }
  }
}

resource entornoApps 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${sufijo}'
  location: ubicacion
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

output entornoAppsId string = entornoApps.id
output storageNombre string = storage.name
output postgresHost string = postgres.properties.fullyQualifiedDomainName
