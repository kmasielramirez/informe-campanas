"""
app.py — La pantalla de la herramienta (lo que veis en el navegador).

Para abrirla: doble clic en INICIAR_WINDOWS.bat (Windows) o INICIAR_MAC.command (Mac).
Toda la lógica de cálculo está en informe.py.
"""

import os
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import clientes
import informe as inf

CARPETA = Path(__file__).parent
DATOS = CARPETA / "datos"
REGISTRO = CARPETA / "evidencias" / "registro_pruebas.csv"

# Lee la clave de la IA del archivo .env (si existe)
try:
    from dotenv import load_dotenv
    load_dotenv(CARPETA / ".env")
except ImportError:
    pass

MODELOS_GEMINI = list(dict.fromkeys(m for m in [
    os.getenv("GEMINI_MODEL", "").strip(), "gemini-3.5-flash", "gemini-2.5-flash", "gemini-3.1-flash-lite"] if m))

EJEMPLOS = {
    "Hilo Verde · moda sostenible (4 semanas)": ("campana_hilo_verde.csv", "Hilo Verde", 20.0, 3.0),
    "Fit Pisuerga · gimnasio (6 semanas)": ("campana_fit_pisuerga.csv", "Fit Pisuerga", 20.0, 4.0),
    "Archivo con errores (para probar la revisión)": ("campana_con_errores.csv", "Hilo Verde", 20.0, 3.0),
}

st.set_page_config(page_title="Agencia del futuro · Herramientas", page_icon="📊", layout="wide")

# ---------------------------------------------------------------------------
# Selector de sección: informes de campañas o clientes (CRM)
# ---------------------------------------------------------------------------
SECCIONES = ["Informes de campañas", "Clientes (CRM)"]
if st.session_state.get("seccion") not in SECCIONES:
    st.session_state.seccion = SECCIONES[0]
with st.sidebar:
    st.radio("Sección", SECCIONES, key="seccion", horizontal=True)
    st.divider()

if st.session_state.seccion == "Clientes (CRM)":
    clientes.mostrar(CARPETA, DATOS)
    st.stop()


def _quitar_cliente_crm():
    st.session_state.pop("cliente_crm", None)


crm = st.session_state.get("cliente_crm")   # cliente elegido en la pestaña CRM (si lo hay)

# ---------------------------------------------------------------------------
# Barra lateral: datos, cliente, objetivos e IA
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("1. Datos de la campaña")
    modo = st.radio("¿Qué datos quieres usar?", ["Un ejemplo", "Mi propio archivo"], horizontal=True)
    origen = nombre_archivo = None
    cliente_def, cpa_def, roas_def = "Mi cliente", 20.0, 3.0
    if modo == "Un ejemplo":
        nombres = list(EJEMPLOS)
        # Si venimos del CRM y hay un ejemplo de ese cliente, lo elegimos directamente
        indice = next((i for i, n in enumerate(nombres) if crm and EJEMPLOS[n][1] == crm["empresa"]), 0)
        elegido = st.selectbox("Ejemplo", nombres, index=indice)
        nombre_archivo, cliente_def, cpa_def, roas_def = EJEMPLOS[elegido]
        origen = DATOS / nombre_archivo
    else:
        subido = st.file_uploader("Sube un CSV o un Excel", type=["csv", "xlsx"])
        if subido is not None:
            origen, nombre_archivo = subido, subido.name
        with st.expander("¿Qué columnas necesita el archivo?"):
            st.markdown(
                "Una fila por día y canal, con estas columnas:\n\n"
                "`fecha`, `canal`, `impresiones`, `clics`, `conversiones`, `gasto` y, si hay ventas, `ingresos`.\n\n"
                "También reconoce nombres parecidos: *inversión*, *coste*, *ventas*, *clicks*…")

    st.header("2. Cliente y objetivos")
    if crm:
        cliente_def = crm["empresa"]
        cpa_def = float(crm["cpa"]) if crm.get("cpa") else cpa_def
        roas_def = float(crm["roas"]) if crm.get("roas") else roas_def
        st.info(f"Cliente y objetivos traídos del CRM: {crm['empresa']}")
        st.button("Quitar los datos del CRM", on_click=_quitar_cliente_crm)
    cliente = st.text_input("Nombre del cliente", value=cliente_def)
    cpa_obj = st.number_input("CPA objetivo (€)", min_value=0.0, value=cpa_def, step=1.0,
                              help="Lo máximo que el cliente quiere pagar por cada venta o cliente nuevo.")
    roas_obj = st.number_input("ROAS objetivo", min_value=0.0, value=roas_def, step=0.5,
                               help="Cuántos euros de ventas quiere conseguir por cada euro invertido.")

    st.header("3. Inteligencia artificial")
    clave = os.getenv("GEMINI_API_KEY", "").strip()
    if clave and not clave.startswith("pega"):
        st.success("Clave de Gemini cargada desde el archivo .env")
    else:
        clave = st.text_input("Clave de Gemini (opcional)", type="password",
                              help="Sin clave la herramienta funciona igual; solo se desactiva el botón de redactar con IA.")
    st.caption("La IA solo recibe cifras agregadas por canal, nunca datos personales.")

# ---------------------------------------------------------------------------
# Leer, revisar y calcular
# ---------------------------------------------------------------------------
if origen is None:
    st.title("Informe automático de campañas")
    st.info("Sube un archivo en la barra lateral o elige un ejemplo para generar el informe.")
    st.stop()

inicio = time.perf_counter()
try:
    crudo = inf.leer_archivo(origen, nombre_archivo)
except Exception as e:  # noqa: BLE001
    st.error(f"No se ha podido leer el archivo. Comprueba que es un CSV o un Excel. Detalle: {e}")
    st.stop()

df, problemas, tiene_ingresos = inf.limpiar_datos(crudo)
if df is None or df.empty:
    st.title("Informe automático de campañas")
    for p in problemas:
        st.error(p["mensaje"])
    if df is not None:
        st.error("No queda ninguna fila válida después de revisar los datos.")
    st.stop()

totales, canales, semanas = inf.calcular_kpis(df, tiene_ingresos)
sem_canal = inf.kpis_semana_canal(df, tiene_ingresos)
hallazgos, recomendaciones = inf.generar_conclusiones(
    totales, canales, df, tiene_ingresos, cpa_obj or None, roas_obj or None)
segundos_informe = time.perf_counter() - inicio

# Si cambian los datos o el cliente, olvidamos el informe de IA anterior
firma = f"{nombre_archivo}|{cliente}|{cpa_obj}|{roas_obj}|{len(df)}"
if st.session_state.get("firma") != firma:
    st.session_state.firma = firma
    st.session_state.ia = None

# ---------------------------------------------------------------------------
# Cabecera, calidad de datos y KPIs
# ---------------------------------------------------------------------------
st.title(f"Informe de campaña · {cliente}")
st.caption(f"Del {totales['inicio']:%d/%m/%Y} al {totales['fin']:%d/%m/%Y} · {totales['dias']} días · "
           f"{len(df)} filas analizadas · informe generado en {segundos_informe:.2f} segundos")

incidencias = [p for p in problemas if p["nivel"] in ("error", "aviso")]
iconos = {"error": "❌", "aviso": "⚠️", "info": "ℹ️", "ok": "✅"}
if incidencias:
    st.warning(f"Revisión de datos: {len(incidencias)} incidencia(s) detectada(s) y corregida(s). Mira el detalle antes de enviar el informe.")
else:
    st.success("Revisión de datos: el archivo no tiene errores.")
with st.expander("Ver la revisión de datos"):
    for p in problemas:
        filas = f" (filas {', '.join(map(str, p['filas'][:10]))})" if p["filas"] else ""
        st.markdown(f"{iconos[p['nivel']]} {p['mensaje']}{filas}")


def variacion(columna, decimales=2, porcentaje=False):
    """Diferencia entre la última semana y la anterior, como texto para st.metric."""
    if len(semanas) < 2:
        return None
    a, b = semanas[columna].iloc[-2], semanas[columna].iloc[-1]
    if pd.isna(a) or pd.isna(b):
        return None
    d = (b - a) * (100 if porcentaje else 1)
    signo = "+" if d >= 0 else ""
    sufijo = " p.p." if porcentaje else ""
    return f"{signo}{inf.num(d, decimales)}{sufijo} vs semana anterior"


columnas = st.columns(6 if tiene_ingresos else 4)
i = 0
columnas[i].metric("Inversión", inf.eur(totales["gasto"])); i += 1
if tiene_ingresos:
    columnas[i].metric("Ventas", inf.eur(totales["ingresos"])); i += 1
    columnas[i].metric("ROAS", inf.ratio(totales["roas"]), variacion("roas"),
                       help="Euros de ventas por cada euro invertido."); i += 1
columnas[i].metric("Conversiones", inf.num(totales["conversiones"]), variacion("conversiones", 0)); i += 1
columnas[i].metric("CPA", inf.eur(totales["cpa"], 2), variacion("cpa"), delta_color="inverse",
                   help="Coste por conversión. Cuanto más bajo, mejor."); i += 1
columnas[i].metric("CTR", inf.pct(totales["ctr"], 2), variacion("ctr", 2, porcentaje=True),
                   help="Porcentaje de personas que hacen clic al ver el anuncio.")

# ---------------------------------------------------------------------------
# Gráficos (se usan en la app y en el informe descargable)
# ---------------------------------------------------------------------------
graficos = {}
if tiene_ingresos:
    largo = canales.melt(id_vars="canal", value_vars=["gasto", "ingresos"], var_name="concepto", value_name="euros")
    largo["concepto"] = largo["concepto"].map({"gasto": "Inversión", "ingresos": "Ventas"})
    graficos["Inversión y ventas por canal"] = px.bar(
        largo, x="canal", y="euros", color="concepto", barmode="group",
        labels={"canal": "", "euros": "€", "concepto": ""}, title="Inversión y ventas por canal")
    orden = canales.sort_values("roas")
    fig_roas = px.bar(orden, x="roas", y="canal", orientation="h", text=orden["roas"].map(inf.ratio),
                      labels={"roas": "ROAS", "canal": ""}, title="ROAS por canal")
    fig_roas.add_vline(x=1, line_dash="dot", annotation_text="Recupera la inversión")
    if roas_obj:
        fig_roas.add_vline(x=roas_obj, line_dash="dash", line_color="green", annotation_text="Objetivo",
                           annotation_position="bottom right")
    graficos["ROAS por canal"] = fig_roas
else:
    orden = canales.sort_values("cpa", ascending=False)
    fig_cpa = px.bar(orden, x="cpa", y="canal", orientation="h", text=orden["cpa"].map(lambda v: inf.eur(v, 2)),
                     labels={"cpa": "CPA (€)", "canal": ""}, title="Coste por conversión por canal")
    if cpa_obj:
        fig_cpa.add_vline(x=cpa_obj, line_dash="dash", line_color="green", annotation_text="Objetivo")
    graficos["CPA por canal"] = fig_cpa

graficos["Reparto del presupuesto"] = px.pie(canales, names="canal", values="gasto", hole=0.5,
                                             title="Reparto del presupuesto")
embudo = pd.DataFrame({"paso": ["Impresiones", "Clics", "Conversiones"],
                       "personas": [totales["impresiones"], totales["clics"], totales["conversiones"]]})
graficos["Embudo de la campaña"] = px.funnel(embudo, x="personas", y="paso", title="Embudo de la campaña")
graficos["Evolución del CPA por canal"] = px.line(
    sem_canal, x="semana", y="cpa", color="canal", markers=True,
    labels={"cpa": "CPA (€)", "semana": "", "canal": "Canal"}, title="Evolución del CPA por canal")

# ---------------------------------------------------------------------------
# Pestañas
# ---------------------------------------------------------------------------
tab_canal, tab_evol, tab_concl, tab_ia, tab_desc, tab_datos = st.tabs(
    ["Por canal", "Evolución", "Conclusiones", "Informe con IA", "Descargar y registrar", "Datos"])

with tab_canal:
    tabla = pd.DataFrame({
        "Canal": canales["canal"],
        "Inversión": canales["gasto"].map(inf.eur),
        "% presupuesto": canales["peso_gasto"].map(lambda v: inf.pct(v, 0)),
        "Impresiones": canales["impresiones"].map(inf.num),
        "Clics": canales["clics"].map(inf.num),
        "CTR": canales["ctr"].map(lambda v: inf.pct(v, 2)),
        "Conversiones": canales["conversiones"].map(inf.num),
        "CPA": canales["cpa"].map(lambda v: inf.eur(v, 2)),
    })
    if tiene_ingresos:
        tabla["Ventas"] = canales["ingresos"].map(inf.eur)
        tabla["ROAS"] = canales["roas"].map(inf.ratio)
    st.dataframe(tabla, hide_index=True)
    nombres = list(graficos)
    c1, c2 = st.columns(2)
    c1.plotly_chart(graficos[nombres[0]])
    c2.plotly_chart(graficos[nombres[1]] if tiene_ingresos else graficos["Reparto del presupuesto"])
    c3, c4 = st.columns(2)
    if tiene_ingresos:
        c3.plotly_chart(graficos["Reparto del presupuesto"])
    c4.plotly_chart(graficos["Embudo de la campaña"])

with tab_evol:
    opciones = {"CPA (€)": "cpa", "Conversiones": "conversiones", "CTR": "ctr", "Inversión (€)": "gasto"}
    if tiene_ingresos:
        opciones = {"ROAS": "roas", **opciones}
    elegida = st.radio("Indicador", list(opciones), horizontal=True)
    st.plotly_chart(px.line(sem_canal, x="semana", y=opciones[elegida], color="canal", markers=True,
                            labels={opciones[elegida]: elegida, "semana": "", "canal": "Canal"}))
    resumen_sem = pd.DataFrame({
        "Semana": semanas["semana"],
        "Desde": semanas["inicio_semana"].dt.strftime("%d/%m"),
        "Inversión": semanas["gasto"].map(inf.eur),
        "Conversiones": semanas["conversiones"].map(inf.num),
        "CPA": semanas["cpa"].map(lambda v: inf.eur(v, 2)),
    })
    if tiene_ingresos:
        resumen_sem["Ventas"] = semanas["ingresos"].map(inf.eur)
        resumen_sem["ROAS"] = semanas["roas"].map(inf.ratio)
    st.dataframe(resumen_sem, hide_index=True)

with tab_concl:
    st.caption("Calculadas con reglas fijas, sin IA: con los mismos datos siempre dan el mismo resultado.")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Conclusiones")
        st.markdown("\n".join(f"- {h}" for h in hallazgos))
    with c2:
        st.subheader("Recomendaciones")
        st.markdown("\n".join(f"{n}. {r}" for n, r in enumerate(recomendaciones, 1)))

with tab_ia:
    st.markdown("La IA redacta el informe para el cliente a partir de los datos y las conclusiones anteriores. "
                "Después, la herramienta **comprueba sus cifras** y el equipo revisa el texto antes de enviarlo.")
    prompt = inf.construir_prompt(cliente, totales, canales, tiene_ingresos, hallazgos, recomendaciones,
                                  cpa_obj or None, roas_obj or None)
    if not clave:
        st.info("Para usar la IA necesitas una clave gratuita de Gemini. Consíguela en "
                "https://aistudio.google.com/apikey y pégala en el archivo .env (mira la guía) "
                "o en la barra lateral.")
    elif st.button("Redactar informe con IA", type="primary"):
        with st.spinner("La IA está redactando el informe…"):
            t = time.perf_counter()
            try:
                texto, modelo = inf.pedir_a_gemini(prompt, clave, MODELOS_GEMINI)
                st.session_state.ia = {"texto": texto, "modelo": modelo, "segundos": time.perf_counter() - t,
                                       "sospechosas": inf.revisar_cifras(texto, prompt)}
            except RuntimeError as e:
                st.error(str(e))

    ia = st.session_state.get("ia")
    if ia:
        st.caption(f"Redactado por {ia['modelo']} en {ia['segundos']:.1f} segundos.")
        with st.container(border=True):
            st.markdown(ia["texto"])
        st.subheader("Comprobación automática de cifras")
        if ia["sospechosas"]:
            st.warning("Estas cifras no aparecen en los datos. Comprobad de dónde salen o borradlas: "
                       + ", ".join(ia["sospechosas"]))
        else:
            st.success("Todas las cifras del texto coinciden con los datos de la campaña.")
        st.subheader("Revisión del equipo")
        revisiones = [
            st.checkbox("Las cifras coinciden con la tabla por canal", key="r1"),
            st.checkbox("Las recomendaciones tienen sentido para este cliente", key="r2"),
            st.checkbox("El tono es adecuado para enviarlo al cliente", key="r3"),
            st.checkbox("No incluye datos confidenciales ni personales", key="r4"),
        ]
        st.session_state.revision_ok = sum(revisiones)
    with st.expander("Ver exactamente lo que se envía a la IA"):
        st.code(prompt, language="markdown")

with tab_desc:
    ia = st.session_state.get("ia")
    figuras_html = []
    for n, fig in enumerate(graficos.values()):
        figuras_html.append(fig.to_html(full_html=False, include_plotlyjs="cdn" if n == 0 else False))
    html_informe = inf.informe_html(
        cliente, totales, canales, tiene_ingresos, hallazgos, recomendaciones, figuras_html,
        ia["texto"] if ia else None, ia["sospechosas"] if ia else None)
    nombre_limpio = re.sub(r"[^a-z0-9]+", "-", cliente.lower()).strip("-") or "cliente"

    st.subheader("Descargar")
    c1, c2 = st.columns(2)
    c1.download_button("Descargar informe completo (HTML)", data=html_informe,
                       file_name=f"informe_{nombre_limpio}.html", mime="text/html", type="primary")
    tabla_csv = canales.round(4).to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    c2.download_button("Descargar tabla por canal (Excel/CSV)", data=tabla_csv,
                       file_name=f"kpis_{nombre_limpio}.csv", mime="text/csv")
    st.caption("El informe HTML se abre en cualquier navegador y se puede imprimir o guardar como PDF.")

    st.subheader("Registro de pruebas (evidencias)")
    st.markdown("Cada vez que probéis la herramienta, guardad aquí el resultado. "
                "Este registro es la evidencia de prueba y la comparación con el proceso manual.")
    c1, c2 = st.columns([1, 2])
    minutos_manual = c1.number_input("Minutos que tardaríais a mano", min_value=1, value=120, step=10)
    notas = c2.text_input("Notas (qué habéis comprobado o corregido)")
    if st.button("Guardar esta prueba en el registro"):
        fila = {
            "fecha_prueba": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "archivo": nombre_archivo,
            "cliente": cliente,
            "filas_leidas": len(crudo),
            "filas_validas": len(df),
            "incidencias_datos": len(incidencias),
            "segundos_informe": round(segundos_informe, 2),
            "ia_usada": "sí" if ia else "no",
            "modelo_ia": ia["modelo"] if ia else "",
            "segundos_ia": round(ia["segundos"], 1) if ia else "",
            "cifras_ia_a_revisar": len(ia["sospechosas"]) if ia else "",
            "revision_equipo_ok": f"{st.session_state.get('revision_ok', 0)}/4" if ia else "",
            "roas": round(totales["roas"], 2) if tiene_ingresos else "",
            "cpa": round(totales["cpa"], 2),
            "minutos_a_mano": minutos_manual,
            "notas": notas,
        }
        inf.guardar_registro(REGISTRO, fila)
        st.success("Prueba guardada en evidencias/registro_pruebas.csv")
    if REGISTRO.exists():
        registro = pd.read_csv(REGISTRO, sep=";", encoding="utf-8-sig")
        st.dataframe(registro, hide_index=True)
        st.download_button("Descargar el registro de pruebas", data=REGISTRO.read_bytes(),
                           file_name="registro_pruebas.csv", mime="text/csv")

with tab_datos:
    st.caption("Datos ya revisados y limpios, tal y como se han usado en el informe.")
    st.dataframe(df, hide_index=True)
