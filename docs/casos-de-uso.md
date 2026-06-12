# Casos de uso del SSC — Resumen del levantamiento

> Fuente: levantamiento realizado por el equipo del SSC Finanzas LATAM (noviembre 2025), archivo `Casos_uso_IA_SSC.xlsx`. Este documento resume y organiza los casos para el diseño de PowerAI; el Excel original es el insumo de detalle.

## Los tres patrones funcionales

Los más de 150 casos se cubren con tres motores:

1. **Chat analítico** — preguntas en lenguaje natural sobre datos estructurados.
2. **Reportes y conciliaciones** — generación recurrente y cruces entre fuentes con motor determinístico + explicación por IA.
3. **Monitoreo y alertas** — tríadas de estado actual / tendencia histórica / alertas de desviación por proceso.

## OTC (Order to Cash)

| ID | Caso | Tipo | Fuente | Frecuencia | Impacto |
|---|---|---|---|---|---|
| CU-00 | Reporte Aging (3 reportes Oracle fuente) | Reporte | AR abiertas, pagos unapplied, revenue reconciliation | Semanal | Alto (>200 usuarios) |
| CU-01 | Promedios de pago por cliente | Reporte | Pagos aplicados + historial facturas | Semanal | Alto |
| CU-02 | Conciliación AR vs GL | Reporte | Trial Balance + Aging | Mensual | Alto |
| CU-03 | Reserva de incobrabilidad MeCCA | Reporte | AR abiertas + distribución PWS | Mensual | Alto |
| CU-03b | Chat libre a la cartera de cobranzas | Chat | AR abiertas / Aging | Semanal | Medio |
| OTC-01/02/03 | Tríadas: cobranza LATAM, créditos mensual, top 20 clientes | Monitoreo | Oracle / Excel | Diaria–mensual | Alto |

## PTP (Procure to Pay)

| ID | Caso | Tipo | Frecuencia | Impacto |
|---|---|---|---|---|
| AP-01 a AP-05 | Chat: top proveedores, eficiencia de pago, proyección, pagos programados, concentración | Chat | Mensual | Medio/Bajo |
| AP-06 | Conciliación estado de cuenta bancario vs Oracle | Conciliación | Diario | Medio |
| AP-07 | Partidas abiertas por periodo contable | Conciliación | Mensual | Medio |
| AP-08 | Project Matching vs Payment Register | Reporte | Mensual | Medio |
| AP-09 | Anticipos: cancelaciones y saldos pendientes | Conciliación | Mensual | Medio |
| AP-10 | Lectura de contratos → días de crédito vs master data | Validación documental | Mensual | Bajo |
| REEM-01/02 | Tiempos de reembolso, picos de gasto | Chat | Mensual | Alto/Bajo |
| IA-01 | Consultas en lenguaje natural AP | Chat | Ad hoc | Medio (>100 usuarios) |
| PTP-01 a PTP-08 | Tríadas: anticipos, compras, CxP, días de crédito, transferencias, tipo de cambio, cash flow MeCCA, compras LATAM | Monitoreo | Diaria–mensual | Alto |

## RTR (Record to Report)

| ID | Caso | Tipo | Impacto |
|---|---|---|---|
| RTR-01 | Estados de gasto personalizados (P&L filtrable) | Reporte | Alto |
| RTR-02/03 | Top de gastos, proveedores de mayor impacto | Reporte | Medio |
| RTR-04 | Centros de costo vs presupuesto | Reporte | Alto |
| RTR-05/06 | Clientes relevantes, control de WIP | Consulta | Medio |
| RTR-07 | Soporte al cierre: variaciones vs mes anterior | Consulta | Alto |
| RTR-08/09 | Tendencias y proyección de gastos | Reporte/Consulta | Medio/Alto |
| RTR-10 | Consultas en lenguaje natural | Chat | Medio |
| RTR-01-x a RTR-03-x | Tríadas: conciliaciones bancarias, cierre contable, conciliaciones mensuales | Monitoreo | Alto |

## QCI / CARE

| ID | Caso | Fuente | Nota técnica |
|---|---|---|---|
| QCI-01 | Calidad de atención por ejecutivo en grabaciones de llamadas | Grabaciones | Requiere transcripción (Azure AI Speech) — Fase 4 |
| QCI-02 | Productividad y desempeño del SSC | Reportes operativos | |
| QCI-01-x a QCI-04-x | Tríadas: evaluación de servicio, informe bimestral, facturación SSC, volumetría histórica | Excel / SharePoint | |
| CARE-01 a CARE-06 | Tríadas: backlog diario, SLA semanal, KPI histórico, tablero CARE, ServiceNow, tablero calidad | Pentafon WS + SharePoint | Conector webservice — Fase 4 |

## HTR (Hire to Retire)

| ID | Caso | Fuente |
|---|---|---|
| HTR-01/02 | Análisis de uso y KPIs del portal de talento | Portal de Talento |
| HTR-03 | Consolidación de nómina por órdenes de trabajo | Sistema Payrolling |
| HTR-04 | Curación de datos Base LATAM (Excel vs SharePoint) | Excel / SharePoint |
| HTR-05/06 | Correos de aprobación de pagos, altas de usuarios | Excel |
| HTR-07/08 | Facturación del SSC, organigramas | Excel |
| HTR-01-x | Tríada: administración de personal | Excel |

## Generales (transversales)

| ID | Caso | Resolución en PowerAI |
|---|---|---|
| GEN-01 | Generación de dashboards | Specs declarativas guardables; datasets expuestos para Power BI si se requiere |
| GEN-02 | Reporte consolidado de varios archivos | Motor de ingesta + chat analítico |
| GEN-03 | Estadística/análisis de Excel y bases | Chat analítico sobre catálogo semántico |
| GEN-04 | Propuestas de solución (business case) | RAG documental sobre plantillas y políticas |
| IA-T01 | Vista financiera integral | Dashboard consolidado GL+AP+AR (Fase 3) |
| IA-T02 | Alertas financieras automáticas | Motor de alertas a Teams (Fase 2) |
| IA-T03 | Explicación de variaciones | Análisis explicativo con IA (Fase 3) |
