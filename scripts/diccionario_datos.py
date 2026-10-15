"""Diccionario de datos: perfila los CSV reales y los contrasta con el diagrama del levantamiento inicial.

Uso (desde la raiz del proyecto):
    python scripts/diccionario_datos.py
Genera en docs/:  diccionario_columnas.csv, resumen_tablas.csv, integridad.csv, hallazgos.csv, diccionario_datos.md
"""
import re
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "data" / "bronze_simple" / "data" / "bronze_simple"
SALIDA = RAIZ / "docs"

# ---------------------------------------------------------------------------
# Lo que dice el diagrama (levantamiento inicial): tipo, PK, FK, NOT NULL
# ---------------------------------------------------------------------------
DIAGRAMA = {
    "clientes": {
        "granularidad": "1 fila por cliente",
        "pk": ["cliente_id"], "fk": {},
        "cols": {"cliente_id": "varchar", "fecha_vinculacion": "date", "tipo_cliente": "varchar",
                 "rango_ingreso": "varchar", "departamento": "varchar", "antiguedad_laboral_meses": "int"},
        "not_null": [],
    },
    "creditos": {
        "granularidad": "1 fila por crédito",
        "pk": ["credito_id"], "fk": {"cliente_id": "clientes.cliente_id"},
        "cols": {"credito_id": "varchar", "cliente_id": "varchar", "producto": "varchar",
                 "fecha_desembolso": "date", "monto_original": "decimal", "plazo_meses": "int",
                 "cuota_pactada": "decimal", "fecha_vencimiento": "date", "estado_actual": "varchar"},
        "not_null": ["cliente_id"],
    },
    "pagos": {
        "granularidad": "1 fila por pago registrado",
        "pk": ["pago_id"], "fk": {"credito_id": "creditos.credito_id"},
        "cols": {"pago_id": "varchar", "credito_id": "varchar", "fecha_pago": "date",
                 "fecha_registro": "timestamp", "monto_pagado": "decimal", "tipo_pago": "varchar",
                 "estado_pago": "varchar"},
        "not_null": ["credito_id"],
    },
    "gestiones_cobranza": {
        "granularidad": "1 fila por gestión de cobranza",
        "pk": ["gestion_id"], "fk": {"credito_id": "creditos.credito_id"},
        "cols": {"gestion_id": "varchar", "credito_id": "varchar", "fecha_gestion": "timestamp",
                 "canal": "varchar", "resultado": "varchar", "promesa_pago": "boolean",
                 "fecha_promesa": "date"},
        "not_null": ["credito_id"],
    },
    "cartera_diaria": {
        "granularidad": "1 fila por crédito y día (snapshot diario)",
        "pk": ["credito_id", "fecha_corte"], "fk": {"credito_id": "creditos.credito_id"},
        "cols": {"credito_id": "varchar", "fecha_corte": "date", "dias_mora": "int",
                 "saldo_capital": "decimal", "saldo_vencido": "decimal", "cuotas_vencidas": "int",
                 "valor_exigible": "decimal", "estado_mora": "varchar"},
        "not_null": ["credito_id", "fecha_corte"],
    },
}

# Columna de fecha que define el periodo histórico de cada tabla
COL_PERIODO = {"clientes": "fecha_vinculacion", "creditos": "fecha_desembolso", "pagos": "fecha_pago",
               "gestiones_cobranza": "fecha_gestion", "cartera_diaria": "fecha_corte"}

MAX_CATEGORIAS = 12      # una columna con <= N valores distintos se trata como categórica


# ---------------------------------------------------------------------------
# Utilidades de perfilado
# ---------------------------------------------------------------------------
def leer(tabla: str) -> pd.DataFrame:
    """Lee todo como texto para no perder el formato original."""
    return pd.read_csv(DATOS / tabla / f"{tabla}.csv", dtype=str)


def patron(valor: str) -> str:
    """Formato de un valor: dígitos -> 9, letras -> A  (C00001 -> A99999)."""
    return re.sub(r"[A-Za-z]", "A", re.sub(r"\d", "9", valor))


def tipo_real(s: pd.Series) -> str:
    """Tipo inferido de los valores no nulos."""
    v = s.dropna()
    if v.empty:
        return "vacío"
    if v.str.fullmatch(r"-?\d+").all():
        return "int"
    if v.str.fullmatch(r"-?\d+\.\d+").all() or v.str.fullmatch(r"-?\d+(\.\d+)?").all():
        return "decimal"
    if v.isin(["True", "False"]).all():
        return "boolean"
    if v.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
        return "date"
    if v.str.fullmatch(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?").all():
        return "timestamp"
    return "varchar"


def equivalente(esperado: str, real: str) -> bool:
    """¿El tipo real es compatible con el del diagrama?"""
    if real == "vacío":
        return True
    return real == esperado or (esperado == "decimal" and real == "int")


def formato(s: pd.Series, tipo: str) -> str:
    v = s.dropna()
    if v.empty:
        return "—"
    if tipo == "date":
        return "YYYY-MM-DD"
    if tipo == "timestamp":
        return "YYYY-MM-DD hh:mm[:ss]"
    if tipo == "boolean":
        return "True / False"
    if tipo in ("int", "decimal"):
        return "numérico sin separador de miles"
    pats = v.map(patron).value_counts()
    if v.nunique() <= MAX_CATEGORIAS:
        return "categórica: " + ", ".join(sorted(v.unique()))
    return f"patrón {pats.index[0]}" + (f" (+{len(pats) - 1} variantes)" if len(pats) > 1 else "")


def rango(s: pd.Series, tipo: str) -> str:
    v = s.dropna()
    if v.empty:
        return "—"
    if tipo in ("int", "decimal"):
        n = pd.to_numeric(v)
        return f"{n.min():,.0f} … {n.max():,.0f}"
    if tipo in ("date", "timestamp"):
        d = pd.to_datetime(v, errors="coerce")
        return f"{d.min().date()} … {d.max().date()}"
    if v.name.startswith("fecha"):
        iso = pd.to_datetime(v, format="%Y-%m-%d", errors="coerce").dropna()
        if len(iso):
            return f"{iso.min().date()} … {iso.max().date()} (solo las fechas ISO)"
    return f"{v.min()} … {v.max()}"


# ---------------------------------------------------------------------------
# Construcción del diccionario
# ---------------------------------------------------------------------------
def construir():
    tablas = {t: leer(t) for t in DIAGRAMA}
    filas_cols, filas_tab, filas_int = [], [], []

    for t, df in tablas.items():
        d = DIAGRAMA[t]
        n = len(df)
        # --- columnas
        for c in df.columns:
            tr = tipo_real(df[c])
            esperado = d["cols"].get(c)
            nulos = int(df[c].isna().sum())
            filas_cols.append({
                "tabla": t, "columna": c,
                "clave": "PK" if c in d["pk"] else ("FK→" + d["fk"][c] if c in d["fk"] else ""),
                "tipo_diagrama": esperado or "NO ESTÁ EN EL DIAGRAMA",
                "tipo_real": tr,
                "coincide_tipo": "sí" if esperado and equivalente(esperado, tr) else "NO",
                "formato": formato(df[c], tr),
                "nulos": nulos, "pct_nulos": round(100 * nulos / n, 2),
                "not_null_diagrama": "sí" if c in d["not_null"] else "",
                "distintos": int(df[c].nunique()),
                "rango": rango(df[c], tr),
                "ejemplo": df[c].dropna().iloc[0] if df[c].notna().any() else "",
            })
        for c in d["cols"]:
            if c not in df.columns:
                filas_cols.append({"tabla": t, "columna": c, "tipo_diagrama": d["cols"][c],
                                   "tipo_real": "NO EXISTE EN LOS DATOS", "coincide_tipo": "NO"})

        # --- resumen de la tabla
        col_p = COL_PERIODO[t]
        fechas = pd.to_datetime(df[col_p], format="%Y-%m-%d", errors="coerce")
        dup_pk = int(df.duplicated(d["pk"], keep=False).sum())
        dup_full = int(df.duplicated().sum())
        filas_tab.append({
            "tabla": t, "filas": n, "columnas": df.shape[1],
            "granularidad": d["granularidad"], "clave_primaria": " + ".join(d["pk"]),
            "columna_periodo": col_p, "desde": fechas.min().date(), "hasta": fechas.max().date(),
            "dias_cubiertos": (fechas.max() - fechas.min()).days + 1,
            "filas_duplicadas_exactas": dup_full, "filas_con_pk_repetida": dup_pk,
            "tamano_kb": round((DATOS / t / f"{t}.csv").stat().st_size / 1024, 1),
        })

        # --- integridad: PK y FK
        filas_int.append({"tabla": t, "regla": f"PK única ({' + '.join(d['pk'])})",
                          "filas_que_incumplen": dup_pk})
        for col, ref in d["fk"].items():
            tabla_ref, col_ref = ref.split(".")
            huerfanas = df[col].dropna()
            huerfanas = huerfanas[~huerfanas.isin(tablas[tabla_ref][col_ref])]
            filas_int.append({"tabla": t, "regla": f"FK {col} → {ref}",
                              "filas_que_incumplen": len(huerfanas),
                              "valores": ", ".join(sorted(huerfanas.unique())[:5])})
        for col in d["not_null"]:
            filas_int.append({"tabla": t, "regla": f"NOT NULL {col}",
                              "filas_que_incumplen": int(df[col].isna().sum())})

    return (pd.DataFrame(filas_cols), pd.DataFrame(filas_tab),
            pd.DataFrame(filas_int).fillna(""), tablas)


def hallazgos(tablas: dict) -> pd.DataFrame:
    """Reglas de calidad / negocio verificadas sobre los datos reales."""
    cl, cr, pg, ge, ca = (tablas[k] for k in ["clientes", "creditos", "pagos", "gestiones_cobranza", "cartera_diaria"])
    num = lambda s: pd.to_numeric(s, errors="coerce")
    iso = lambda s: pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    h = []

    def add(tabla, hallazgo, n, impacto):
        h.append({"tabla": tabla, "hallazgo": hallazgo, "filas_afectadas": int(n), "impacto": impacto})

    add("clientes", "Filas duplicadas exactas (cliente_id repetido)", cl.duplicated().sum(), "Inflan el conteo de clientes")
    add("clientes", "rango_ingreso nulo", cl.rango_ingreso.isna().sum(), "Falta una variable de segmentación")
    add("clientes", "antiguedad_laboral_meses negativa", (num(cl.antiguedad_laboral_meses) < 0).sum(), "Valor imposible")
    add("clientes", "Clientes sin ningún crédito", (~cl.cliente_id.drop_duplicates().isin(cr.cliente_id)).sum(), "Sin historia de crédito")
    add("creditos", "cliente_id inexistente en clientes (huérfano)", (~cr.cliente_id.isin(cl.cliente_id)).sum(), "Rompe la relación cliente-crédito")
    add("creditos", "monto_original <= 0", (num(cr.monto_original) <= 0).sum(), "Valor imposible")
    add("creditos", "estado_actual con un único valor (ACTIVO)", int(cr.estado_actual.nunique() == 1) * len(cr), "No hay créditos cancelados/castigados: sin variación para el modelo")
    add("pagos", "Filas duplicadas exactas (pago_id repetido)", pg.duplicated().sum(), "Doble conteo de recaudo")
    add("pagos", "fecha_pago en formato dd/mm/yyyy (resto es yyyy-mm-dd)", pg.fecha_pago.str.contains("/", na=False).sum(), "Formato mixto: se pierde al convertir a fecha")
    add("pagos", "monto_pagado nulo", pg.monto_pagado.isna().sum(), "Pago sin valor")
    add("pagos", "fecha_registro anterior a fecha_pago", (pd.to_datetime(pg.fecha_registro) < iso(pg.fecha_pago)).sum(), "Registro antes del pago: incoherente")
    add("pagos", "tipo_pago y estado_pago con un único valor", len(pg) if pg.tipo_pago.nunique() == 1 and pg.estado_pago.nunique() == 1 else 0, "Sin pagos parciales, reversados ni rechazados")
    add("gestiones_cobranza", "canal con mayúsculas/minúsculas mezcladas (SMS vs sms)", (ge.canal != ge.canal.str.upper()).sum(), "Una misma categoría aparece como 6 valores")
    add("gestiones_cobranza", "resultado nulo", ge.resultado.isna().sum(), "Gestión sin resultado")
    add("gestiones_cobranza", "Créditos sin ninguna gestión", (~cr.credito_id.isin(ge.credito_id)).sum(), "Esperable: solo se gestiona cuando hay mora")
    add("cartera_diaria", "Filas duplicadas exactas (credito_id + fecha_corte)", ca.duplicated().sum(), "Doble conteo de saldos")
    add("cartera_diaria", "dias_mora nulo", ca.dias_mora.isna().sum(), "Mora desconocida en ese día")
    add("cartera_diaria", "saldo_capital negativo", (num(ca.saldo_capital) < 0).sum(), "Valor imposible")
    add("cartera_diaria", "valor_exigible idéntico a saldo_vencido en todas las filas", len(ca) if (ca.valor_exigible == ca.saldo_vencido).all() else 0, "Columna redundante")
    return pd.DataFrame(h)


def a_markdown(cols, tab, integ, hall=None) -> str:
    def md(df):
        return df.astype(str).pipe(lambda x: "| " + " | ".join(x.columns) + " |\n|" + "---|" * len(x.columns) + "\n"
                                   + "\n".join("| " + " | ".join(r) + " |" for r in x.values))
    out = ["# Diccionario de datos — capa bronze_simple\n",
           "_Generado automáticamente por `scripts/diccionario_datos.py` a partir de los CSV reales, "
           "contrastado con el diagrama del levantamiento inicial._\n",
           "## 1. Volumen, granularidad y periodo histórico\n", md(tab), "\n"]
    out += ["## 2. Reglas de integridad (PK / FK / NOT NULL)\n", md(integ), "\n"]
    out += ["## 3. Diccionario por columna\n"]
    for t, g in cols.groupby("tabla", sort=False):
        out += [f"### {t}\n", md(g.drop(columns="tabla").fillna("")), "\n"]
    return "\n".join(out)


if __name__ == "__main__":
    SALIDA.mkdir(exist_ok=True)
    cols, tab, integ, tablas = construir()
    hall = hallazgos(tablas)
    hall.to_csv(SALIDA / "hallazgos.csv", index=False, encoding="utf-8-sig")
    cols.to_csv(SALIDA / "diccionario_columnas.csv", index=False, encoding="utf-8-sig")
    tab.to_csv(SALIDA / "resumen_tablas.csv", index=False, encoding="utf-8-sig")
    integ.to_csv(SALIDA / "integridad.csv", index=False, encoding="utf-8-sig")
    (SALIDA / "diccionario_datos.md").write_text(a_markdown(cols, tab, integ, hall), encoding="utf-8")
    print("Generado en", SALIDA)
