import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)                     # semilla fija: mismos datos cada vez
N_CLIENTES, N_CREDITOS = 50, 65                     # volumen pequeño; súbelo para generar más datos
INICIO, FIN = pd.Timestamp("2024-07-01"), pd.Timestamp("2025-12-31")   # ventana de la cartera diaria
SALIDA = Path("data/bronze_simple")                 # carpeta nueva: no toca tu Bronze actual

# ---------- 1. CLIENTES ----------
clientes = pd.DataFrame({
    "cliente_id": [f"C{i:05d}" for i in range(1, N_CLIENTES + 1)],
    "fecha_vinculacion": (INICIO - pd.to_timedelta(rng.integers(250, 3200, N_CLIENTES), unit="D")).strftime("%Y-%m-%d"),
    "tipo_cliente": rng.choice(["DEPENDIENTE", "INDEPENDIENTE"], N_CLIENTES),
    "rango_ingreso": rng.choice(["1-2M", "2-3M", "3-5M", "5-8M", "8M+"], N_CLIENTES),
    "departamento": rng.choice(["ANTIOQUIA", "CUNDINAMARCA", "VALLE", "ATLANTICO", "SANTANDER"], N_CLIENTES),
    "antiguedad_laboral_meses": rng.integers(3, 181, N_CLIENTES),
})

# ---------- 2. CREDITOS ----------
# Cada cliente recibe 1 crédito; los créditos que sobran se reparten al azar entre clientes.
dueños = np.concatenate([clientes["cliente_id"], rng.choice(clientes["cliente_id"], N_CREDITOS - N_CLIENTES)])
n = len(dueños)
monto = rng.integers(4, 40, n) * 1_000_000
plazo = rng.choice([12, 24, 36], n)
tasa = 0.02                                          # 2 % mensual
desembolso = INICIO - pd.to_timedelta(rng.integers(30, 400, n), unit="D")
cuota = (monto * tasa / (1 - (1 + tasa) ** -plazo)).round(-2)       # fórmula de cuota fija (sistema francés)
creditos = pd.DataFrame({
    "credito_id": [f"CR{i:06d}" for i in range(1, n + 1)], "cliente_id": dueños,
    "producto": rng.choice(["CONSUMO", "LIBRE_INVERSION"], n),
    "fecha_desembolso": desembolso.strftime("%Y-%m-%d"), "monto_original": monto, "plazo_meses": plazo,
    "cuota_pactada": cuota.astype(int), "fecha_vencimiento": [(d + pd.DateOffset(months=int(p))).strftime("%Y-%m-%d") for d, p in zip(desembolso, plazo)],
    "estado_actual": "ACTIVO",
})

# ---------- 3. PAGOS y 4. CARTERA DIARIA (una historia coherente por crédito) ----------
pagos, cartera, gestiones = [], [], []
dias = pd.date_range(INICIO, FIN)                    # un snapshot por día
puntualidad = dict(zip(clientes["cliente_id"], rng.uniform(0.70, 0.98, N_CLIENTES)))   # qué tan cumplido es cada cliente

for cr in creditos.itertuples():
    vence = [pd.Timestamp(cr.fecha_desembolso) + pd.DateOffset(months=k) for k in range(1, cr.plazo_meses + 1)]
    pagado = []                                      # fecha de pago de cada cuota (NaT = no pagada)
    for d in vence:
        if d > FIN:
            pagado.append(pd.NaT); continue
        if rng.random() < puntualidad[cr.cliente_id]:
            f = d - pd.Timedelta(days=int(rng.integers(0, 4)))               # paga a tiempo
        elif rng.random() < 0.985:
            f = d + pd.Timedelta(days=int(rng.integers(3, 60)))              # paga tarde: aquí nace la mora
        else:
            f = pd.NaT                                                       # no paga
        pagado.append(f if (pd.isna(f) or f <= FIN) else pd.NaT)
        if pd.notna(pagado[-1]):
            pagos.append({"credito_id": cr.credito_id, "fecha_pago": pagado[-1], "monto_pagado": cr.cuota_pactada,
                          "fecha_registro": pagado[-1] + pd.Timedelta(days=int(rng.integers(0, 3)))})   # el banco registra días después
    vence, pag = pd.DatetimeIndex(vence).to_numpy(), pd.DatetimeIndex(pagado).to_numpy()
    pag = np.where(np.isnat(pag), np.datetime64("2100-01-01"), pag)          # NaT -> "nunca"
    for d in dias[dias >= pd.Timestamp(cr.fecha_desembolso)]:
        impagas = (vence < d.to_datetime64()) & (pag > d.to_datetime64())     # vencidas y aún sin pagar ese día
        mora = int((d - pd.Timestamp(vence[impagas].min())).days) if impagas.any() else 0   # mora = días desde la cuota impaga más antigua
        pagadas = int(((pag <= d.to_datetime64()) & (vence <= FIN.to_datetime64())).sum())
        cartera.append((cr.credito_id, d, mora, int(cr.monto_original * (1 - pagadas / cr.plazo_meses)),
                        int(cr.cuota_pactada * impagas.sum()), int(impagas.sum())))

cartera = pd.DataFrame(cartera, columns=["credito_id", "fecha_corte", "dias_mora", "saldo_capital", "saldo_vencido", "cuotas_vencidas"])
cartera["valor_exigible"] = cartera["saldo_vencido"]
cartera["estado_mora"] = np.where(cartera["dias_mora"] > 0, "MORA", "AL_DIA")

pagos = pd.DataFrame(pagos).sort_values("fecha_registro").reset_index(drop=True)
pagos.insert(0, "pago_id", [f"P{i:08d}" for i in range(1, len(pagos) + 1)])
pagos["tipo_pago"], pagos["estado_pago"] = "CUOTA", "APLICADO"

# ---------- 5. GESTIONES DE COBRANZA (solo cuando hay mora) ----------
en_mora = cartera[cartera["dias_mora"] > 0]
g = en_mora[rng.random(len(en_mora)) < 0.15][["credito_id", "fecha_corte"]].rename(columns={"fecha_corte": "fecha_gestion"}).reset_index(drop=True)
g.insert(0, "gestion_id", [f"G{i:08d}" for i in range(1, len(g) + 1)])
g["canal"] = rng.choice(["LLAMADA", "SMS", "EMAIL"], len(g))
g["resultado"] = rng.choice(["CONTACTADO", "NO_CONTACTADO"], len(g))
g["promesa_pago"] = rng.random(len(g)) < 0.3
g["fecha_promesa"] = np.where(g["promesa_pago"], (g["fecha_gestion"] + pd.to_timedelta(rng.integers(2, 12, len(g)), unit="D")).dt.strftime("%Y-%m-%d"), "")
g["fecha_gestion"] = g["fecha_gestion"].dt.strftime("%Y-%m-%d")

# ---------- 6. INYECTAR ERRORES (a propósito, para practicar la limpieza) ----------
# Todo pasa a TEXTO primero: así llega un CSV real. Los errores se aplican sobre texto.
tablas = {"clientes": clientes, "creditos": creditos, "pagos": pagos, "gestiones_cobranza": g, "cartera_diaria": cartera}
for nombre, df in tablas.items():
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.strftime("%Y-%m-%d")
    tablas[nombre] = df.astype(str).replace({"nan": "", "<NA>": ""})

respuestas = []                                       # hoja de respuestas: qué se dañó y dónde (solo para el mentor)
turnos = {t: iter(rng.permutation(df.index)) for t, df in tablas.items()}   # filas sin repetir: un error por fila


def tomar(tabla, k):
    """Devuelve k filas distintas de la tabla que todavía no tienen ningún error."""
    return [next(turnos[tabla]) for _ in range(k)]


def daño(tabla, tipo, columna, k, funcion):
    """Aplica `funcion` al valor de `columna` en k filas al azar y lo anota en la hoja de respuestas."""
    df = tablas[tabla]
    for i in tomar(tabla, k):
        antes = df.at[i, columna]
        df.at[i, columna] = funcion(antes)
        respuestas.append({"tabla": tabla, "error": tipo, "fila_csv": i + 2, "columna": columna, "antes": antes, "despues": df.at[i, columna]})


def duplicar(tabla, k):
    """Agrega k copias exactas de filas existentes al final de la tabla."""
    df = tablas[tabla]
    filas = tomar(tabla, k)
    for i in filas:
        respuestas.append({"tabla": tabla, "error": "duplicado_exacto", "fila_csv": i + 2, "columna": "*", "antes": df.at[i, df.columns[0]], "despues": "(fila repetida)"})
    tablas[tabla] = pd.concat([df, df.loc[filas]], ignore_index=True)


daño("clientes", "nulo", "rango_ingreso", 4, lambda v: "")
daño("clientes", "valor_negativo", "antiguedad_laboral_meses", 2, lambda v: f"-{v}")
duplicar("clientes", 3)

daño("creditos", "huerfano (cliente inexistente)", "cliente_id", 2, lambda v: "C99999")
daño("creditos", "valor_negativo", "monto_original", 1, lambda v: f"-{v}")

daño("pagos", "nulo", "monto_pagado", 3, lambda v: "")
daño("pagos", "fecha_formato_distinto", "fecha_pago", 2, lambda v: pd.Timestamp(v).strftime("%d/%m/%Y"))
daño("pagos", "registro_anterior_al_pago", "fecha_registro", 2, lambda v: (pd.Timestamp(v) - pd.Timedelta(days=5)).strftime("%Y-%m-%d"))
duplicar("pagos", 5)

daño("gestiones_cobranza", "texto_sin_normalizar", "canal", 4, lambda v: v.lower())
daño("gestiones_cobranza", "nulo", "resultado", 3, lambda v: "")

daño("cartera_diaria", "nulo", "dias_mora", 3, lambda v: "")
daño("cartera_diaria", "valor_negativo", "saldo_capital", 2, lambda v: f"-{v}")
duplicar("cartera_diaria", 10)

# ---------- 7. ESCRIBIR A BRONZE (CSV) ----------
for nombre, df in tablas.items():
    (SALIDA / nombre).mkdir(parents=True, exist_ok=True)
    df.to_csv(SALIDA / nombre / f"{nombre}.csv", index=False, encoding="utf-8")
    print(f"{nombre:20s} {len(df):>7} filas")
# La hoja de respuestas va FUERA de Bronze y no se le muestra al aprendiz hasta que haga su propio perfilamiento.
pd.DataFrame(respuestas).to_csv(SALIDA.parent / "respuestas_errores_bronze_simple.csv", index=False, encoding="utf-8")
print(f"{len(respuestas)} errores inyectados -> {SALIDA.parent / 'respuestas_errores_bronze_simple.csv'}")
