# ADR-0001: Stack Azure-nativo

**Estado:** Aceptada · **Fecha:** 2026-06-12

## Contexto
ManpowerGroup opera sobre el ecosistema Microsoft/Azure (Entra ID, Azure OpenAI en otras iniciativas, SharePoint, Teams). PowerAI manejará información financiera de 15 países y requiere alineación con compliance corporativo, residencia de datos y la revisión de Global Technology.

## Decisión
Toda la infraestructura de PowerAI se despliega en el tenant Azure corporativo: Azure Blob Storage, Azure Database for PostgreSQL, Azure Container Apps, Azure Cache for Redis, Azure OpenAI y Microsoft Entra ID para SSO.

## Consecuencias
- (+) Networking, identidad y compliance heredan los controles corporativos existentes.
- (+) Conversación simple con Global Technology: sin proveedores nuevos.
- (+) Integración natural con SharePoint (Graph API) y Teams (webhooks de alertas).
- (−) Lock-in parcial a Azure; mitigado con contenedores estándar y la capa adapter de IA (ADR pendiente si se requiere multi-cloud).
