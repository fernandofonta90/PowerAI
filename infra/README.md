# Infraestructura — PowerAI

IaC en **Bicep** para el despliegue Azure-nativo (ADR-0001) sobre **Azure
Container Apps**.

> **Estado (M1):** esqueleto base, **no desplegado**. Define el andamiaje de
> recursos para iterarlo con Global Technology (networking, private endpoints,
> Key Vault, Entra ID, identidades administradas). No contiene secretos: la
> contraseña de PostgreSQL se inyecta desde Key Vault en el despliegue.

## Recursos definidos

- Log Analytics workspace (observabilidad de Container Apps).
- Storage Account (datasets Parquet y archivos originales versionados).
- Azure Cache for Redis (broker de Celery).
- PostgreSQL Flexible Server 16 (base transaccional).
- Container Apps Managed Environment (host de API y frontend).

## Uso (cuando se habilite el despliegue)

```bash
# Validar la plantilla
az bicep build --file main.bicep

# Desplegar a un resource group existente
az deployment group create \
  --resource-group <RG> \
  --template-file main.bicep \
  --parameters main.parameters.example.json
```

Pendiente para fases siguientes: definición de las Container Apps de `api/` y
`web/`, ingress, identidades administradas, reglas de escalado y wiring de
secretos desde Key Vault.
