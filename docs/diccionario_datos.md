# Diccionario de datos — capa bronze_simple

_Generado automáticamente por `scripts/diccionario_datos.py` a partir de los CSV reales, contrastado con el diagrama del levantamiento inicial._

## 1. Volumen, granularidad y periodo histórico

| tabla | filas | columnas | granularidad | clave_primaria | columna_periodo | desde | hasta | dias_cubiertos | filas_duplicadas_exactas | filas_con_pk_repetida | tamano_kb |
|---|---|---|---|---|---|---|---|---|---|---|---|
| clientes | 53 | 6 | 1 fila por cliente | cliente_id | fecha_vinculacion | 2015-12-08 | 2023-04-20 | 2691 | 3 | 6 | 2.7 |
| creditos | 65 | 9 | 1 fila por crédito | credito_id | fecha_desembolso | 2023-05-29 | 2024-05-27 | 365 | 0 | 0 | 5.0 |
| pagos | 1235 | 7 | 1 fila por pago registrado | pago_id | fecha_pago | 2023-06-26 | 2025-12-30 | 919 | 5 | 10 | 77.9 |
| gestiones_cobranza | 945 | 7 | 1 fila por gestión de cobranza | gestion_id | fecha_gestion | 2024-07-01 | 2025-12-31 | 549 | 0 | 0 | 54.6 |
| cartera_diaria | 35695 | 8 | 1 fila por crédito y día (snapshot diario) | credito_id + fecha_corte | fecha_corte | 2024-07-01 | 2025-12-31 | 549 | 10 | 20 | 1548.7 |


## 2. Reglas de integridad (PK / FK / NOT NULL)

| tabla | regla | filas_que_incumplen | valores |
|---|---|---|---|
| clientes | PK única (cliente_id) | 6 |  |
| creditos | PK única (credito_id) | 0 |  |
| creditos | FK cliente_id → clientes.cliente_id | 2 | C99999 |
| creditos | NOT NULL cliente_id | 0 |  |
| pagos | PK única (pago_id) | 10 |  |
| pagos | FK credito_id → creditos.credito_id | 0 |  |
| pagos | NOT NULL credito_id | 0 |  |
| gestiones_cobranza | PK única (gestion_id) | 0 |  |
| gestiones_cobranza | FK credito_id → creditos.credito_id | 0 |  |
| gestiones_cobranza | NOT NULL credito_id | 0 |  |
| cartera_diaria | PK única (credito_id + fecha_corte) | 20 |  |
| cartera_diaria | FK credito_id → creditos.credito_id | 0 |  |
| cartera_diaria | NOT NULL credito_id | 0 |  |
| cartera_diaria | NOT NULL fecha_corte | 0 |  |


## 3. Diccionario por columna

### clientes

| columna | clave | tipo_diagrama | tipo_real | coincide_tipo | formato | nulos | pct_nulos | not_null_diagrama | distintos | rango | ejemplo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cliente_id | PK | varchar | varchar | sí | patrón A99999 | 0 | 0.0 |  | 50 | C00001 … C00050 | C00001 |
| fecha_vinculacion |  | date | date | sí | YYYY-MM-DD | 0 | 0.0 |  | 49 | 2015-12-08 … 2023-04-20 | 2023-02-04 |
| tipo_cliente |  | varchar | varchar | sí | categórica: DEPENDIENTE, INDEPENDIENTE | 0 | 0.0 |  | 2 | DEPENDIENTE … INDEPENDIENTE | INDEPENDIENTE |
| rango_ingreso |  | varchar | varchar | sí | categórica: 1-2M, 2-3M, 3-5M, 5-8M, 8M+ | 4 | 7.55 |  | 5 | 1-2M … 8M+ | 8M+ |
| departamento |  | varchar | varchar | sí | categórica: ANTIOQUIA, ATLANTICO, CUNDINAMARCA, SANTANDER, VALLE | 0 | 0.0 |  | 5 | ANTIOQUIA … VALLE | SANTANDER |
| antiguedad_laboral_meses |  | int | int | sí | numérico sin separador de miles | 0 | 0.0 |  | 42 | -163 … 175 | -68 |


### creditos

| columna | clave | tipo_diagrama | tipo_real | coincide_tipo | formato | nulos | pct_nulos | not_null_diagrama | distintos | rango | ejemplo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| credito_id | PK | varchar | varchar | sí | patrón AA999999 | 0 | 0.0 |  | 65 | CR000001 … CR000065 | CR000001 |
| cliente_id | FK→clientes.cliente_id | varchar | varchar | sí | patrón A99999 | 0 | 0.0 | sí | 50 | C00001 … C99999 | C00001 |
| producto |  | varchar | varchar | sí | categórica: CONSUMO, LIBRE_INVERSION | 0 | 0.0 |  | 2 | CONSUMO … LIBRE_INVERSION | LIBRE_INVERSION |
| fecha_desembolso |  | date | date | sí | YYYY-MM-DD | 0 | 0.0 |  | 57 | 2023-05-29 … 2024-05-27 | 2023-07-14 |
| monto_original |  | decimal | int | sí | numérico sin separador de miles | 0 | 0.0 |  | 32 | -37,000,000 … 39,000,000 | 24000000 |
| plazo_meses |  | int | int | sí | numérico sin separador de miles | 0 | 0.0 |  | 3 | 12 … 36 | 24 |
| cuota_pactada |  | decimal | int | sí | numérico sin separador de miles | 0 | 0.0 |  | 48 | 156,900 … 3,687,800 | 1268900 |
| fecha_vencimiento |  | date | date | sí | YYYY-MM-DD | 0 | 0.0 |  | 61 | 2024-06-07 … 2027-05-27 | 2025-07-14 |
| estado_actual |  | varchar | varchar | sí | categórica: ACTIVO | 0 | 0.0 |  | 1 | ACTIVO … ACTIVO | ACTIVO |


### pagos

| columna | clave | tipo_diagrama | tipo_real | coincide_tipo | formato | nulos | pct_nulos | not_null_diagrama | distintos | rango | ejemplo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pago_id | PK | varchar | varchar | sí | patrón A99999999 | 0 | 0.0 |  | 1230 | P00000001 … P00001230 | P00000001 |
| credito_id | FK→creditos.credito_id | varchar | varchar | sí | patrón AA999999 | 0 | 0.0 | sí | 65 | CR000001 … CR000065 | CR000006 |
| fecha_pago |  | date | varchar | NO | patrón 9999-99-99 (+1 variantes) | 0 | 0.0 |  | 647 | 2023-06-26 … 2025-12-30 (solo las fechas ISO) | 2023-06-26 |
| monto_pagado |  | decimal | int | sí | numérico sin separador de miles | 3 | 0.24 |  | 48 | 156,900 … 3,687,800 | 549300 |
| fecha_registro |  | timestamp | date | NO | YYYY-MM-DD | 0 | 0.0 |  | 665 | 2023-06-28 … 2025-12-31 | 2023-06-28 |
| tipo_pago |  | varchar | varchar | sí | categórica: CUOTA | 0 | 0.0 |  | 1 | CUOTA … CUOTA | CUOTA |
| estado_pago |  | varchar | varchar | sí | categórica: APLICADO | 0 | 0.0 |  | 1 | APLICADO … APLICADO | APLICADO |


### gestiones_cobranza

| columna | clave | tipo_diagrama | tipo_real | coincide_tipo | formato | nulos | pct_nulos | not_null_diagrama | distintos | rango | ejemplo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gestion_id | PK | varchar | varchar | sí | patrón A99999999 | 0 | 0.0 |  | 945 | G00000001 … G00000945 | G00000001 |
| credito_id | FK→creditos.credito_id | varchar | varchar | sí | patrón AA999999 | 0 | 0.0 | sí | 49 | CR000001 … CR000065 | CR000001 |
| fecha_gestion |  | timestamp | date | NO | YYYY-MM-DD | 0 | 0.0 |  | 450 | 2024-07-01 … 2025-12-31 | 2024-09-17 |
| canal |  | varchar | varchar | sí | categórica: EMAIL, LLAMADA, SMS, email, llamada, sms | 0 | 0.0 |  | 6 | EMAIL … sms | SMS |
| resultado |  | varchar | varchar | sí | categórica: CONTACTADO, NO_CONTACTADO | 3 | 0.32 |  | 2 | CONTACTADO … NO_CONTACTADO | NO_CONTACTADO |
| promesa_pago |  | boolean | boolean | sí | True / False | 0 | 0.0 |  | 2 | False … True | False |
| fecha_promesa |  | date | date | sí | YYYY-MM-DD | 667 | 70.58 |  | 211 | 2024-07-03 … 2026-01-10 | 2024-10-01 |


### cartera_diaria

| columna | clave | tipo_diagrama | tipo_real | coincide_tipo | formato | nulos | pct_nulos | not_null_diagrama | distintos | rango | ejemplo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| credito_id | PK | varchar | varchar | sí | patrón AA999999 | 0 | 0.0 | sí | 65 | CR000001 … CR000065 | CR000001 |
| fecha_corte | PK | date | date | sí | YYYY-MM-DD | 0 | 0.0 | sí | 549 | 2024-07-01 … 2025-12-31 | 2024-07-01 |
| dias_mora |  | int | int | sí | numérico sin separador de miles | 3 | 0.01 |  | 764 | 0 … 763 | 0 |
| saldo_capital |  | decimal | int | sí | numérico sin separador de miles | 0 | 0.0 |  | 397 | -18,000,000 … 36,000,000 | 13000000 |
| saldo_vencido |  | decimal | int | sí | numérico sin separador de miles | 0 | 0.0 |  | 57 | 0 … 3,971,600 | 0 |
| cuotas_vencidas |  | int | int | sí | numérico sin separador de miles | 0 | 0.0 |  | 4 | 0 … 3 | 0 |
| valor_exigible |  | decimal | int | sí | numérico sin separador de miles | 0 | 0.0 |  | 57 | 0 … 3,971,600 | 0 |
| estado_mora |  | varchar | varchar | sí | categórica: AL_DIA, MORA | 0 | 0.0 |  | 2 | AL_DIA … MORA | AL_DIA |

