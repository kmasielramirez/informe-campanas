"""
informe.py — El "cerebro" del proyecto.

Aquí está todo lo que hace la herramienta con los datos, sin nada de pantallas:
  1. Leer el archivo de la campaña (CSV o Excel).
  2. Revisar y limpiar los datos (detectar errores).
  3. Calcular los indicadores (KPIs).
  4. Sacar conclusiones y recomendaciones con reglas fijas.
  5. Preparar la petición para la IA y comprobar las cifras que devuelve.
  6. Crear el informe descargable en HTML.

La pantalla (la app) está en app.py y usa estas funciones.
"""

from __future__ import annotations

import csv
import html
import io
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 0. Ayudas para escribir números "a la española" (1.234,56 €)
# ---------------------------------------------------------------------------

def _es(numero: float, decimales: int) -> str:
    texto = f"{numero:,.{decimales}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def eur(v, decimales: int = 0) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    return f"{_es(v, decimales)} €"


def pct(v, decimales: int = 1) -> str:
    """v es una proporción (0,0123) y se muestra como 1,2 %."""
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    return f"{_es(v * 100, decimales)} %"


def num(v, decimales: int = 0) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    return _es(v, decimales)


def ratio(v, decimales: int = 2) -> str:
    """Para el ROAS: 3,86."""
    return num(v, decimales)


# ---------------------------------------------------------------------------
# 1. Leer el archivo
# ---------------------------------------------------------------------------

def leer_archivo(origen, nombre: str) -> pd.DataFrame:
    """Lee un CSV (separado por comas o por punto y coma) o un Excel."""
    nombre = nombre.lower()
    if nombre.endswith((".xlsx", ".xls")):
        return pd.read_excel(origen)

    if isinstance(origen, (str, Path)):
        bruto = Path(origen).read_bytes()
    else:
        bruto = origen.getvalue() if hasattr(origen, "getvalue") else origen.read()

    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            texto = bruto.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    primera_linea = texto.splitlines()[0] if texto else ""
    separador = ";" if primera_linea.count(";") > primera_linea.count(",") else ","
    return pd.read_csv(io.StringIO(texto), sep=separador, dtype=str)


# ---------------------------------------------------------------------------
# 2. Revisar y limpiar los datos
# ---------------------------------------------------------------------------

OBLIGATORIAS = ["fecha", "canal", "impresiones", "clics", "conversiones", "gasto"]
OPCIONALES = ["ingresos"]

# Nombres alternativos que la herramienta reconoce para cada columna
SINONIMOS = {
    "fecha": ["fecha", "dia", "date", "day"],
    "canal": ["canal", "channel", "medio", "plataforma", "fuente", "red"],
    "impresiones": ["impresiones", "impressions", "impr", "visualizaciones"],
    "clics": ["clics", "clicks", "clic", "click"],
    "conversiones": ["conversiones", "conversions", "pedidos", "leads", "altas", "compras"],
    "gasto": ["gasto", "inversion", "coste", "costo", "spend", "cost", "importe"],
    "ingresos": ["ingresos", "ventas", "facturacion", "revenue", "valor"],
}


def _normaliza(texto: str) -> str:
    texto = unicodedata.normalize("NFD", str(texto)).encode("ascii", "ignore").decode()
    texto = re.sub(r"\(.*?\)", "", texto.lower())
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def _a_numero(serie: pd.Series) -> pd.Series:
    """Convierte textos como '1.234,56 €' o '45,00' en números."""
    if pd.api.types.is_numeric_dtype(serie):
        return serie.astype(float)

    def convertir(x):
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return np.nan
        x = str(x).replace("€", "").replace("%", "").replace(" ", "").replace(" ", "").strip()
        if x.lower() in ("", "nan", "none", "-"):
            return np.nan
        if "," in x and "." in x:
            x = x.replace(".", "").replace(",", ".") if x.rfind(",") > x.rfind(".") else x.replace(",", "")
        elif "," in x:
            x = x.replace(",", ".")
        try:
            return float(x)
        except ValueError:
            return np.nan

    return serie.map(convertir).astype(float)


def _filas(indices) -> list[int]:
    """Número de fila tal como se ve en Excel (la fila 1 es la cabecera)."""
    return [int(i) + 2 for i in indices]


def limpiar_datos(crudo: pd.DataFrame):
    """
    Devuelve (datos_limpios, problemas, tiene_ingresos).
    'problemas' es una lista de avisos para enseñar al usuario.
    Si falta una columna imprescindible, datos_limpios es None.
    """
    problemas: list[dict] = []
    df = crudo.copy()

    # 2.1 Reconocer las columnas aunque tengan otro nombre
    renombrar = {}
    for col in df.columns:
        clave = _normaliza(col)
        for destino, alternativas in SINONIMOS.items():
            if destino not in renombrar.values() and (clave in alternativas or clave.split(" ")[0] in alternativas):
                renombrar[col] = destino
                break
    df = df.rename(columns=renombrar)
    cambiadas = [f"«{o}» → {d}" for o, d in renombrar.items() if o != d]
    if cambiadas:
        problemas.append({"nivel": "info", "mensaje": "Columnas reconocidas con otro nombre: " + ", ".join(cambiadas), "filas": []})

    faltan = [c for c in OBLIGATORIAS if c not in df.columns]
    if faltan:
        problemas.append({"nivel": "error", "mensaje": "Faltan columnas imprescindibles: " + ", ".join(faltan)
                          + ". El archivo necesita: " + ", ".join(OBLIGATORIAS) + " (e ingresos, opcional).", "filas": []})
        return None, problemas, False

    tiene_ingresos = "ingresos" in df.columns
    df = df[[c for c in OBLIGATORIAS + OPCIONALES if c in df.columns]]
    total_leidas = len(df)

    # 2.2 Filas repetidas
    duplicadas = df[df.duplicated(keep="first")]
    if len(duplicadas):
        problemas.append({"nivel": "aviso", "mensaje": f"{len(duplicadas)} fila(s) repetida(s) eliminada(s).", "filas": _filas(duplicadas.index)})
        df = df.drop(duplicadas.index)

    # 2.3 Fechas
    texto_fecha = df["fecha"].astype(str).str.strip()
    fechas = pd.to_datetime(texto_fecha, format="ISO8601", errors="coerce")
    faltan_fecha = fechas.isna()
    if faltan_fecha.any():
        fechas[faltan_fecha] = pd.to_datetime(texto_fecha[faltan_fecha], dayfirst=True, errors="coerce")
    malas = fechas.isna()
    if malas.any():
        problemas.append({"nivel": "error", "mensaje": f"{int(malas.sum())} fila(s) con fecha imposible o vacía. Se han descartado.", "filas": _filas(df.index[malas])})
    df["fecha"] = fechas
    df = df[~malas]

    # 2.4 Números
    columnas_numero = ["impresiones", "clics", "conversiones", "gasto"] + (["ingresos"] if tiene_ingresos else [])
    for col in columnas_numero:
        df[col] = _a_numero(df[col])
    vacias = df[columnas_numero].isna().any(axis=1)
    if vacias.any():
        problemas.append({"nivel": "error", "mensaje": f"{int(vacias.sum())} fila(s) con números vacíos o ilegibles. Se han descartado.", "filas": _filas(df.index[vacias])})
        df = df[~vacias]

    negativas = (df[columnas_numero] < 0).any(axis=1)
    if negativas.any():
        problemas.append({"nivel": "error", "mensaje": f"{int(negativas.sum())} fila(s) con valores negativos (por ejemplo, un gasto de -45 €). Se han descartado.", "filas": _filas(df.index[negativas])})
        df = df[~negativas]

    imposibles = df["clics"] > df["impresiones"]
    if imposibles.any():
        problemas.append({"nivel": "error", "mensaje": f"{int(imposibles.sum())} fila(s) con más clics que impresiones, algo imposible. Se han descartado.", "filas": _filas(df.index[imposibles])})
        df = df[~imposibles]

    raras = df["conversiones"] > df["clics"]
    if raras.any():
        problemas.append({"nivel": "aviso", "mensaje": f"{int(raras.sum())} fila(s) con más conversiones que clics. Puede pasar con códigos de descuento, pero conviene comprobarlo.", "filas": _filas(df.index[raras])})

    # 2.5 Canales escritos de formas distintas ("Instagram Ads" e "instagram ads ")
    df["canal"] = df["canal"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    nombre_oficial: dict[str, str] = {}
    variantes: dict[str, set] = {}
    for valor in df["canal"]:
        clave = valor.lower()
        nombre_oficial.setdefault(clave, valor)
        variantes.setdefault(clave, set()).add(valor)
    unidas = [f"{nombre_oficial[k]} ({len(v)} formas de escribirlo)" for k, v in variantes.items() if len(v) > 1]
    if unidas:
        problemas.append({"nivel": "aviso", "mensaje": "Canales escritos de formas distintas, unificados: " + ", ".join(unidas), "filas": []})
    df["canal"] = df["canal"].str.lower().map(nombre_oficial)

    descartadas = total_leidas - len(df)
    problemas.insert(0, {"nivel": "ok" if descartadas == 0 else "info",
                         "mensaje": f"Filas leídas: {total_leidas}. Filas válidas: {len(df)}. Descartadas: {descartadas}.", "filas": []})
    return df.sort_values(["fecha", "canal"]).reset_index(drop=True), problemas, tiene_ingresos


# ---------------------------------------------------------------------------
# 3. Indicadores (KPIs)
# ---------------------------------------------------------------------------

def _divide(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(b > 0, a / b, np.nan)
    return r


def _anadir_kpis(t: pd.DataFrame, tiene_ingresos: bool) -> pd.DataFrame:
    t = t.copy()
    t["ctr"] = _divide(t["clics"], t["impresiones"])            # % de gente que hace clic
    t["cpc"] = _divide(t["gasto"], t["clics"])                  # coste por clic
    t["tasa_conversion"] = _divide(t["conversiones"], t["clics"])
    t["cpa"] = _divide(t["gasto"], t["conversiones"])           # coste por conversión
    if tiene_ingresos:
        t["roas"] = _divide(t["ingresos"], t["gasto"])          # € de ventas por cada € invertido
        t["beneficio"] = t["ingresos"] - t["gasto"]
    return t


def calcular_kpis(df: pd.DataFrame, tiene_ingresos: bool):
    """Devuelve (totales, por_canal, por_semana)."""
    columnas = ["impresiones", "clics", "conversiones", "gasto"] + (["ingresos"] if tiene_ingresos else [])

    totales = _anadir_kpis(df[columnas].sum().to_frame().T, tiene_ingresos).iloc[0].to_dict()
    totales["inicio"] = df["fecha"].min()
    totales["fin"] = df["fecha"].max()
    totales["dias"] = int((totales["fin"] - totales["inicio"]).days) + 1

    canales = _anadir_kpis(df.groupby("canal", as_index=False)[columnas].sum(), tiene_ingresos)
    canales["peso_gasto"] = canales["gasto"] / canales["gasto"].sum()
    canales = canales.sort_values("gasto", ascending=False).reset_index(drop=True)

    semanal = df.copy()
    semanal["inicio_semana"] = semanal["fecha"] - pd.to_timedelta(semanal["fecha"].dt.weekday, unit="D")
    semanas = semanal.groupby("inicio_semana", as_index=False).agg(
        **{c: (c, "sum") for c in columnas}, dias=("fecha", "nunique"))
    semanas = _anadir_kpis(semanas, tiene_ingresos)
    semanas.insert(0, "semana", [f"Sem {i + 1}" for i in range(len(semanas))])

    return totales, canales, semanas


def kpis_semana_canal(df: pd.DataFrame, tiene_ingresos: bool) -> pd.DataFrame:
    columnas = ["impresiones", "clics", "conversiones", "gasto"] + (["ingresos"] if tiene_ingresos else [])
    d = df.copy()
    d["inicio_semana"] = d["fecha"] - pd.to_timedelta(d["fecha"].dt.weekday, unit="D")
    t = d.groupby(["inicio_semana", "canal"], as_index=False)[columnas].sum()
    orden = {s: i + 1 for i, s in enumerate(sorted(t["inicio_semana"].unique()))}
    t.insert(0, "semana", t["inicio_semana"].map(lambda s: f"Sem {orden[s]}"))
    return _anadir_kpis(t, tiene_ingresos)


# ---------------------------------------------------------------------------
# 4. Conclusiones y recomendaciones automáticas (reglas fijas, sin IA)
# ---------------------------------------------------------------------------

def generar_conclusiones(totales, canales, df, tiene_ingresos, cpa_objetivo=None, roas_objetivo=None):
    """Devuelve (hallazgos, recomendaciones): dos listas de frases."""
    hallazgos: list[str] = []
    recs: list[str] = []
    relevantes = canales[canales["peso_gasto"] >= 0.05]   # canales con al menos el 5 % del presupuesto
    if relevantes.empty:
        relevantes = canales

    # Resumen global
    if tiene_ingresos:
        hallazgos.append(
            f"La campaña ha invertido {eur(totales['gasto'])} y ha generado {eur(totales['ingresos'])} en ventas "
            f"con {num(totales['conversiones'])} conversiones. ROAS global de {ratio(totales['roas'])}: "
            f"cada euro invertido ha devuelto {eur(totales['roas'], 2)}.")
    else:
        hallazgos.append(
            f"La campaña ha invertido {eur(totales['gasto'])} y ha conseguido {num(totales['conversiones'])} conversiones, "
            f"a un coste medio de {eur(totales['cpa'], 2)} por conversión.")

    # Mejor y peor canal
    clave, mejor_alto = ("roas", True) if tiene_ingresos else ("cpa", False)
    validos = relevantes.dropna(subset=[clave])
    mejor = peor = None
    if len(validos) >= 2:
        orden = validos.sort_values(clave, ascending=not mejor_alto)
        mejor, peor = orden.iloc[0], orden.iloc[-1]
        if tiene_ingresos:
            hallazgos.append(
                f"{mejor['canal']} es el canal más rentable: ROAS de {ratio(mejor['roas'])} y CPA de {eur(mejor['cpa'], 2)}, "
                f"con el {pct(mejor['peso_gasto'], 0)} del presupuesto.")
            texto_peor = (f"{peor['canal']} es el canal menos rentable: ROAS de {ratio(peor['roas'])} "
                          f"con el {pct(peor['peso_gasto'], 0)} del presupuesto.")
            if peor["roas"] < 1:
                texto_peor += (f" Pierde dinero: ha costado {eur(peor['gasto'])} y ha vendido {eur(peor['ingresos'])}.")
            hallazgos.append(texto_peor)
        else:
            hallazgos.append(f"{mejor['canal']} consigue las conversiones más baratas: CPA de {eur(mejor['cpa'], 2)}.")
            hallazgos.append(f"{peor['canal']} tiene el CPA más alto: {eur(peor['cpa'], 2)} por conversión.")

    # Canal pequeño con muy buen rendimiento
    if tiene_ingresos:
        pequenos = canales[(canales["peso_gasto"] < 0.05) & (canales["roas"] > totales["roas"] * 1.3)]
        for _, c in pequenos.iterrows():
            hallazgos.append(
                f"{c['canal']} tiene un ROAS muy alto ({ratio(c['roas'])}), pero solo usa el {pct(c['peso_gasto'], 0)} "
                f"del presupuesto, así que su volumen es pequeño.")
            recs.append(f"Probar a dar más peso a {c['canal']} (más envíos o más presupuesto) y vigilar si mantiene el rendimiento.")

    # Objetivos del cliente
    if cpa_objetivo:
        estado = "cumple" if totales["cpa"] <= cpa_objetivo else "no cumple"
        fuera = canales[canales["cpa"] > cpa_objetivo]["canal"].tolist()
        frase = f"El CPA global ({eur(totales['cpa'], 2)}) {estado} el objetivo de {eur(cpa_objetivo, 2)}."
        if fuera:
            frase += " Por encima del objetivo: " + ", ".join(fuera) + "."
        hallazgos.append(frase)
    if roas_objetivo and tiene_ingresos:
        estado = "cumple" if totales["roas"] >= roas_objetivo else "no cumple"
        fuera = canales[canales["roas"] < roas_objetivo]["canal"].tolist()
        frase = f"El ROAS global ({ratio(totales['roas'])}) {estado} el objetivo de {ratio(roas_objetivo)}."
        if fuera:
            frase += " Por debajo del objetivo: " + ", ".join(fuera) + "."
        hallazgos.append(frase)

    # Evolución: primera semana frente a última, por canal
    sc = kpis_semana_canal(df, tiene_ingresos)
    semanas = sorted(sc["semana"].unique(), key=lambda s: int(s.split()[1]))
    if len(semanas) >= 2:
        primera, ultima = semanas[0], semanas[-1]
        cambios = []
        for canal in relevantes["canal"]:
            a = sc[(sc["canal"] == canal) & (sc["semana"] == primera)]
            b = sc[(sc["canal"] == canal) & (sc["semana"] == ultima)]
            # Con menos de 5 conversiones por semana la diferencia puede ser casualidad: no la juzgamos
            if (len(a) and len(b) and a["conversiones"].iloc[0] >= 5 and b["conversiones"].iloc[0] >= 5):
                cambios.append((canal, (b["cpa"].iloc[0] - a["cpa"].iloc[0]) / a["cpa"].iloc[0],
                                a["cpa"].iloc[0], b["cpa"].iloc[0]))
        if cambios:
            mejora = min(cambios, key=lambda x: x[1])
            empeora = max(cambios, key=lambda x: x[1])
            if mejora[1] < -0.15:
                hallazgos.append(
                    f"{mejora[0]} mejora a lo largo de la campaña: su CPA baja de {eur(mejora[2], 2)} ({primera}) "
                    f"a {eur(mejora[3], 2)} ({ultima}).")
                fila = canales[canales["canal"] == mejora[0]].iloc[0]
                rentable = fila["roas"] >= totales["roas"] * 0.8 if tiene_ingresos else fila["cpa"] <= totales["cpa"] * 1.2
                if rentable:
                    recs.append(f"Subir de forma gradual (un 20 %) el presupuesto de {mejora[0]}, que está mejorando semana a semana.")
            if empeora[1] > 0.20:
                hallazgos.append(
                    f"{empeora[0]} empeora: su CPA sube de {eur(empeora[2], 2)} ({primera}) a {eur(empeora[3], 2)} ({ultima}).")
                recs.append(f"Renovar las creatividades o revisar la segmentación de {empeora[0]}: el público puede estar saturado.")

    # CTR muy bajo
    ctr_bajo = canales[canales["ctr"] < 0.005]
    if len(ctr_bajo):
        nombres = ", ".join(f"{c} ({pct(v, 2)})" for c, v in zip(ctr_bajo["canal"], ctr_bajo["ctr"]))
        hallazgos.append(f"CTR muy bajo (menos del 0,5 %) en: {nombres}. Los anuncios apenas llaman la atención.")
        recs.append(f"Probar nuevas creatividades en {', '.join(ctr_bajo['canal'])} antes de invertir más.")

    # Mucho clic pero poca conversión: posible problema en la web
    mediana_cvr = canales["tasa_conversion"].median()
    mediana_ctr = canales["ctr"].median()
    web = canales[(canales["ctr"] >= mediana_ctr) & (canales["tasa_conversion"] < mediana_cvr * 0.5)]
    for _, c in web.iterrows():
        hallazgos.append(
            f"{c['canal']} atrae clics (CTR {pct(c['ctr'], 2)}) pero convierte poco ({pct(c['tasa_conversion'], 2)}).")
        recs.append(f"Revisar la página de destino de {c['canal']}: el anuncio interesa, pero la web no convierte.")

    # Reasignar presupuesto del peor al mejor canal
    if mejor is not None and peor is not None and mejor["canal"] != peor["canal"]:
        if tiene_ingresos and (peor["roas"] < 1 or peor["roas"] < totales["roas"] * 0.6):
            mover = peor["gasto"] * 0.5
            extra = mover * (mejor["roas"] - peor["roas"])
            recs.insert(0,
                f"Mover el 50 % del presupuesto de {peor['canal']} ({eur(mover)}) a {mejor['canal']}. "
                f"Estimación: unos {eur(extra)} más en ventas si {mejor['canal']} mantiene su rendimiento actual.")
            if peor["roas"] < 1:
                recs.insert(1, f"Si en dos semanas {peor['canal']} no supera un ROAS de 1, pausarlo del todo.")
        elif not tiene_ingresos and peor["cpa"] > totales["cpa"] * 1.5:
            mover = peor["gasto"] * 0.5
            extra = mover / mejor["cpa"] - mover / peor["cpa"]
            recs.insert(0,
                f"Mover el 50 % del presupuesto de {peor['canal']} ({eur(mover)}) a {mejor['canal']}. "
                f"Estimación: unas {num(extra)} conversiones más con el mismo dinero.")

    recs.append("Volver a medir dentro de dos semanas con este mismo informe para comprobar si los cambios funcionan.")
    return hallazgos, recs


# ---------------------------------------------------------------------------
# 5. IA: preparar la petición y comprobar las cifras de la respuesta
# ---------------------------------------------------------------------------

def tabla_markdown(canales: pd.DataFrame, tiene_ingresos: bool) -> str:
    cab = ["Canal", "Gasto", "% presupuesto", "Impresiones", "Clics", "CTR", "Conversiones", "CPA"]
    if tiene_ingresos:
        cab += ["Ventas", "ROAS"]
    filas = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    for _, c in canales.iterrows():
        f = [c["canal"], eur(c["gasto"]), pct(c["peso_gasto"], 0), num(c["impresiones"]), num(c["clics"]),
             pct(c["ctr"], 2), num(c["conversiones"]), eur(c["cpa"], 2)]
        if tiene_ingresos:
            f += [eur(c["ingresos"]), ratio(c["roas"])]
        filas.append("| " + " | ".join(str(x) for x in f) + " |")
    return "\n".join(filas)


def construir_prompt(cliente, totales, canales, tiene_ingresos, hallazgos, recs, cpa_objetivo=None, roas_objetivo=None):
    periodo = f"del {totales['inicio']:%d/%m/%Y} al {totales['fin']:%d/%m/%Y}"
    resumen = [f"- Inversión total: {eur(totales['gasto'])}",
               f"- Conversiones: {num(totales['conversiones'])}",
               f"- CTR global: {pct(totales['ctr'], 2)}",
               f"- CPA global: {eur(totales['cpa'], 2)}"]
    if tiene_ingresos:
        resumen += [f"- Ventas: {eur(totales['ingresos'])}", f"- ROAS global: {ratio(totales['roas'])}"]
    objetivos = []
    if cpa_objetivo:
        objetivos.append(f"CPA objetivo: {eur(cpa_objetivo, 2)}")
    if roas_objetivo:
        objetivos.append(f"ROAS objetivo: {ratio(roas_objetivo)}")

    return f"""Eres analista de una agencia de marketing española. Redacta el informe de resultados de una campaña para el cliente {cliente}.

REGLAS
1. Usa SOLO las cifras que aparecen abajo. No inventes datos, porcentajes ni comparaciones con el sector.
2. Si haces una cuenta nueva, explica de dónde sale.
3. Escribe en español de España, claro y sin tecnicismos. Explica qué es el ROAS o el CPA la primera vez que aparezcan.
4. Máximo 300 palabras.
5. Usa exactamente estos apartados con títulos que empiecen por "## ": Resumen, Lo que ha funcionado, Lo que hay que mejorar, Recomendaciones (3 como máximo), Próximos pasos.

DATOS DE LA CAMPAÑA ({periodo}, {totales['dias']} días)
{chr(10).join(resumen)}
{('Objetivos del cliente: ' + '; '.join(objetivos)) if objetivos else ''}

RESULTADOS POR CANAL
{tabla_markdown(canales, tiene_ingresos)}

CONCLUSIONES DEL ANÁLISIS AUTOMÁTICO
{chr(10).join('- ' + h for h in hallazgos)}

RECOMENDACIONES DEL ANÁLISIS AUTOMÁTICO
{chr(10).join('- ' + r for r in recs)}
"""


_NUMERO = re.compile(r"\d[\d.,]*\d|\d")


def _leer_numero(token: str):
    token = token.strip(".,")
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", token):
        return float(token.replace(".", "").replace(",", "."))
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", token):
        return float(token.replace(",", ""))
    if "," in token:
        return float(token.replace(",", ".")) if token.count(",") == 1 else None
    try:
        return float(token)
    except ValueError:
        return None


def numeros_en(texto: str) -> list[tuple[str, float]]:
    salida = []
    for m in _NUMERO.finditer(texto):
        valor = _leer_numero(m.group())
        if valor is not None:
            salida.append((m.group().strip(".,"), valor))
    return salida


def revisar_cifras(texto_ia: str, prompt: str) -> list[str]:
    """
    Busca en la respuesta de la IA cifras que NO estaban en los datos que le dimos.
    Devuelve la lista de cifras sospechosas para que una persona las compruebe.
    """
    permitidas = [v for _, v in numeros_en(prompt)]
    sospechosas = []
    for texto, v in numeros_en(texto_ia):
        if v <= 12 and float(v).is_integer():       # números pequeños: "3 recomendaciones", "semana 2"
            continue
        ok = any(abs(v - p) <= max(0.06, abs(p) * 0.015) or (v >= 10 and abs(v - p) <= 0.5) for p in permitidas)
        if not ok and texto not in sospechosas:
            sospechosas.append(texto)
    return sospechosas


def pedir_a_gemini(prompt: str, api_key: str, modelos: list[str]) -> tuple[str, str]:
    """
    Envía el prompt a Gemini y devuelve (texto, modelo_usado).
    Prueba varios modelos por si alguno ya no existe. Lanza RuntimeError con un mensaje claro si falla.
    """
    try:
        from google import genai
    except ImportError as e:
        raise RuntimeError("Falta la librería de Gemini. Cierra la app y vuelve a abrirla con el archivo de inicio.") from e

    cliente = genai.Client(api_key=api_key)
    ultimo_error = ""
    for modelo in modelos:
        try:
            respuesta = cliente.models.generate_content(model=modelo, contents=prompt)
            texto = (respuesta.text or "").strip()
            if texto:
                return texto, modelo
            ultimo_error = "La IA devolvió una respuesta vacía."
        except Exception as e:  # noqa: BLE001 — queremos explicar cualquier fallo al usuario
            mensaje = str(e)
            if "API_KEY_INVALID" in mensaje or "API key not valid" in mensaje:
                raise RuntimeError("La clave de Gemini no es válida. Revisa que la has copiado entera en el archivo .env.") from e
            if "429" in mensaje or "RESOURCE_EXHAUSTED" in mensaje:
                raise RuntimeError("Has llegado al límite gratuito de Gemini por ahora. Espera un minuto y vuelve a intentarlo.") from e
            ultimo_error = mensaje
            continue   # probamos el siguiente modelo
    raise RuntimeError(f"No se ha podido usar Gemini. Detalle técnico: {ultimo_error[:300]}")


# ---------------------------------------------------------------------------
# 6. Informe descargable (HTML) y registro de pruebas
# ---------------------------------------------------------------------------

def _markdown_a_html(texto: str) -> str:
    """Conversión muy sencilla de Markdown (títulos, listas y negritas) a HTML."""
    lineas, salida, en_lista = texto.splitlines(), [], False
    for linea in lineas:
        l = html.escape(linea.strip())
        l = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", l)
        if l.startswith(("- ", "* ")) or re.match(r"^\d+\.\s", l):
            if not en_lista:
                salida.append("<ul>")
                en_lista = True
            salida.append("<li>" + re.sub(r"^(- |\* |\d+\.\s)", "", l) + "</li>")
            continue
        if en_lista:
            salida.append("</ul>")
            en_lista = False
        if l.startswith("#"):
            salida.append("<h3>" + l.lstrip("#").strip() + "</h3>")
        elif l:
            salida.append("<p>" + l + "</p>")
    if en_lista:
        salida.append("</ul>")
    return "\n".join(salida)


def informe_html(cliente, totales, canales, tiene_ingresos, hallazgos, recs, graficos_html, texto_ia=None, cifras_revisar=None) -> str:
    e = html.escape
    tarjetas = [("Inversión", eur(totales["gasto"])), ("Conversiones", num(totales["conversiones"])),
                ("CPA", eur(totales["cpa"], 2)), ("CTR", pct(totales["ctr"], 2))]
    if tiene_ingresos:
        tarjetas = [("Inversión", eur(totales["gasto"])), ("Ventas", eur(totales["ingresos"])),
                    ("ROAS", ratio(totales["roas"]))] + tarjetas[1:]
    cab = ["Canal", "Gasto", "% presup.", "Impresiones", "Clics", "CTR", "Conv.", "CPA"] + (["Ventas", "ROAS"] if tiene_ingresos else [])
    filas = ""
    for _, c in canales.iterrows():
        celdas = [e(c["canal"]), eur(c["gasto"]), pct(c["peso_gasto"], 0), num(c["impresiones"]), num(c["clics"]),
                  pct(c["ctr"], 2), num(c["conversiones"]), eur(c["cpa"], 2)]
        if tiene_ingresos:
            celdas += [eur(c["ingresos"]), ratio(c["roas"])]
        filas += "<tr>" + "".join(f"<td>{x}</td>" for x in celdas) + "</tr>"

    bloque_ia = ""
    if texto_ia:
        aviso = ""
        if cifras_revisar:
            aviso = f"<p class='aviso'>Cifras que la herramienta no ha encontrado en los datos y que el equipo ha revisado: {e(', '.join(cifras_revisar))}</p>"
        bloque_ia = f"<section><h2>Informe redactado con IA y revisado por el equipo</h2>{_markdown_a_html(texto_ia)}{aviso}</section>"

    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Informe de campaña · {e(cliente)}</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#141821;max-width:1000px;margin:0 auto;padding:32px 20px;line-height:1.55}}
h1{{margin:0 0 4px}} h2{{margin-top:36px;border-bottom:2px solid #2c55e0;padding-bottom:4px}}
.sub{{color:#555}} .kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:20px}}
.kpi{{background:#f1f4fa;border-radius:8px;padding:12px}} .kpi b{{display:block;font-size:24px}}
table{{border-collapse:collapse;width:100%;font-size:14px}} th,td{{padding:6px 8px;border-bottom:1px solid #dde2ec;text-align:right}}
th:first-child,td:first-child{{text-align:left}} th{{background:#f1f4fa}}
.aviso{{background:#fdf0d9;padding:10px;border-radius:6px}} .pie{{color:#777;font-size:13px;margin-top:40px}}
</style></head><body>
<h1>Informe de campaña · {e(cliente)}</h1>
<div class="sub">Del {totales['inicio']:%d/%m/%Y} al {totales['fin']:%d/%m/%Y} ({totales['dias']} días)</div>
<div class="kpis">{''.join(f'<div class="kpi">{e(k)}<b>{v}</b></div>' for k, v in tarjetas)}</div>
<h2>Resultados por canal</h2><div style="overflow-x:auto"><table><tr>{''.join(f'<th>{h}</th>' for h in cab)}</tr>{filas}</table></div>
{''.join(graficos_html)}
<h2>Conclusiones</h2><ul>{''.join(f'<li>{e(h)}</li>' for h in hallazgos)}</ul>
<h2>Recomendaciones</h2><ol>{''.join(f'<li>{e(r)}</li>' for r in recs)}</ol>
{bloque_ia}
<p class="pie">Informe generado automáticamente el {datetime.now():%d/%m/%Y a las %H:%M}. Las estimaciones suponen que cada canal mantiene su rendimiento actual.</p>
</body></html>"""


def guardar_registro(ruta: Path, fila: dict) -> None:
    """Añade una línea al registro de pruebas (se abre con Excel)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not ruta.exists()
    with ruta.open("a", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=list(fila.keys()), delimiter=";")
        if nuevo:
            escritor.writeheader()
        # Decimales con coma para que Excel en español los lea como números
        escritor.writerow({k: (str(v).replace(".", ",") if isinstance(v, float) else v) for k, v in fila.items()})
