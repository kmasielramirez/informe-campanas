"""
clientes.py — Pestaña "Clientes (CRM)" de la app.

Lee el CRM que rellena el formulario de Google (a través del enlace CSV publicado
de Google Sheets, de un Excel descargado o del archivo de ejemplo) y muestra:
  - Indicadores y embudo de clientes.
  - Seguimientos pendientes (a quién hay que llamar hoy).
  - El listado completo, con los datos de contacto ocultos por defecto.
  - Un botón para preparar el informe de campaña de un cliente con sus objetivos.
"""

import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import informe as inf

ESTADOS = ["Nuevo", "Contactado", "Reunión", "Propuesta enviada", "Ganado", "Perdido"]
ORDEN_PRIORIDAD = {"Alta": 0, "Media": 1, "Baja": 2}
NUMERICAS = ["Presupuesto (€/mes)", "Precio medio (€)", "Puntuación", "CPA objetivo (€)", "ROAS objetivo"]
FECHAS = ["Fecha", "Próximo seguimiento"]
NECESARIAS = ["Empresa", "Prioridad", "Estado"]


@st.cache_data(ttl=60, show_spinner=False)
def _leer_enlace(url: str) -> pd.DataFrame:
    return pd.read_csv(url, dtype=str)


def _preparar(df: pd.DataFrame):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    faltan = [c for c in NECESARIAS if c not in df.columns]
    if faltan:
        return None, ("El archivo no tiene las columnas del CRM (" + ", ".join(faltan) + "). "
                      "Comprobad que habéis publicado la pestaña **CRM** y no otra.")
    df = df[df["Empresa"].notna() & (df["Empresa"].astype(str).str.strip() != "")]
    for c in NUMERICAS:
        if c in df.columns:
            df[c] = inf._a_numero(df[c])
    for c in FECHAS:
        if c in df.columns and not pd.api.types.is_datetime64_any_dtype(df[c]):
            texto = df[c].astype(str).str.strip()
            fechas = pd.to_datetime(texto, format="ISO8601", errors="coerce")
            faltan = fechas.isna()
            fechas[faltan] = pd.to_datetime(texto[faltan], dayfirst=True, errors="coerce")
            df[c] = fechas
    df["Estado"] = df["Estado"].fillna("Nuevo").replace("", "Nuevo")
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].fillna("")
    return df.reset_index(drop=True), None


def _ocultar_email(email: str) -> str:
    email = str(email or "")
    if "@" not in email:
        return email
    usuario, dominio = email.split("@", 1)
    return usuario[:2] + "•••@" + dominio


def _ocultar_telefono(tel: str) -> str:
    tel = str(tel or "").strip()
    return ("••• ••• " + tel[-3:]) if len(tel) > 3 else tel


def _ir_a_informe(empresa, cpa, roas):
    st.session_state.cliente_crm = {"empresa": empresa, "cpa": cpa, "roas": roas}
    st.session_state.seccion = "Informes de campañas"


def mostrar(carpeta, datos):
    st.title("Clientes potenciales (CRM)")
    st.caption("Datos que llegan desde el formulario de Google y se organizan en Google Sheets.")

    # --- De dónde salen los datos ---
    with st.sidebar:
        st.header("Origen de los clientes")
        url_env = os.getenv("CRM_URL", "").strip()
        opciones = ["Google Sheets (en directo)", "Subir Excel o CSV", "Ejemplo"]
        origen = st.radio("¿De dónde leemos los clientes?", opciones, index=0 if url_env else 2)
        url = archivo = None
        if origen == opciones[0]:
            url = st.text_input("Enlace CSV publicado de la pestaña CRM", value=url_env,
                                help="En Google Sheets: Archivo > Compartir > Publicar en la web > pestaña CRM > CSV.")
            if st.button("Actualizar datos", type="primary"):
                _leer_enlace.clear()
        elif origen == opciones[1]:
            archivo = st.file_uploader("Excel o CSV descargado de Google Sheets", type=["xlsx", "csv"])
        mostrar_contacto = st.toggle("Mostrar emails y teléfonos", value=False,
                                     help="Ocultos por defecto para proteger los datos de los clientes.")

    if origen == opciones[0] and not url:
        st.info("Pega en la barra lateral el enlace CSV publicado de la pestaña CRM "
                "(o guárdalo como CRM_URL en el archivo .env). Mientras tanto, puedes elegir «Ejemplo».")
        st.stop()
    if origen == opciones[0] and "output=csv" not in url:
        st.error("Ese enlace no es el CSV publicado. En Google Sheets: Archivo > Compartir > Publicar en la web, "
                 "elige la pestaña CRM y el formato CSV, y copia el enlace que termina en output=csv.")
        st.stop()
    if origen == opciones[1] and archivo is None:
        st.info("En Google Sheets: Archivo > Descargar > Microsoft Excel, y sube aquí el archivo.")
        st.stop()

    crudo = None
    error_lectura = ""
    try:
        if origen == opciones[0]:
            crudo = _leer_enlace(url)
            leido = f"Leído de Google Sheets a las {datetime.now():%H:%M}. Se actualiza solo cada minuto o con el botón."
        elif origen == opciones[1]:
            if archivo.name.lower().endswith(".xlsx"):
                hojas = pd.read_excel(archivo, sheet_name=None, dtype=str)   # todas las pestañas
                crudo = hojas.get("CRM", next(iter(hojas.values())))
            else:
                crudo = inf.leer_archivo(archivo, archivo.name)
            leido = f"Leído del archivo {archivo.name}."
        else:
            crudo = inf.leer_archivo(datos / "crm_ejemplo.csv", "crm_ejemplo.csv")
            leido = "Datos de ejemplo (8 clientes ficticios)."
    except Exception as e:  # noqa: BLE001
        error_lectura = str(e)
    if crudo is None:
        st.error("No se han podido leer los clientes. Comprueba el enlace o el archivo y la conexión a internet. "
                 f"Detalle: {error_lectura}")
        st.stop()

    df, error = _preparar(crudo)
    if error:
        st.error(error)
        st.stop()
    st.caption(f"{leido} {len(df)} contactos.")
    if df.empty:
        st.info("Todavía no hay ningún cliente. Rellena el formulario y pulsa «Actualizar datos».")
        st.stop()

    # --- Indicadores ---
    abiertos = ~df["Estado"].isin(["Ganado", "Perdido"])
    ganados = int((df["Estado"] == "Ganado").sum())
    perdidos = int((df["Estado"] == "Perdido").sum())
    en_juego = df.loc[df["Estado"] != "Perdido", "Presupuesto (€/mes)"].sum() if "Presupuesto (€/mes)" in df else 0
    c = st.columns(5)
    c[0].metric("Contactos", len(df))
    c[1].metric("Prioridad alta", int((df["Prioridad"] == "Alta").sum()))
    c[2].metric("Presupuesto mensual en juego", inf.eur(en_juego))
    c[3].metric("Clientes ganados", ganados)
    c[4].metric("Tasa de cierre", inf.pct(ganados / (ganados + perdidos), 0) if (ganados + perdidos) else "–",
                help="Ganados entre ganados y perdidos.")

    # --- A quién hay que llamar ---
    st.subheader("Seguimientos pendientes")
    if "Próximo seguimiento" in df:
        hoy = pd.Timestamp.today().normalize()
        pend = df[abiertos & df["Próximo seguimiento"].notna() & (df["Próximo seguimiento"] <= hoy + pd.Timedelta(days=1))].copy()
        if pend.empty:
            st.success("No hay seguimientos pendientes para hoy.")
        else:
            pend["orden"] = pend["Prioridad"].map(ORDEN_PRIORIDAD).fillna(3)
            pend = pend.sort_values(["orden", "Próximo seguimiento"])
            vencidos = int((pend["Próximo seguimiento"] < hoy).sum())
            st.warning(f"{len(pend)} cliente(s) para contactar hoy o mañana, {vencidos} con el seguimiento ya vencido.")
            vista = pd.DataFrame({
                "Empresa": pend["Empresa"],
                "Prioridad": pend["Prioridad"],
                "Estado": pend["Estado"],
                "Seguimiento": pend["Próximo seguimiento"].dt.strftime("%d/%m/%Y"),
            })
            if "Responsable" in pend:
                vista["Responsable"] = pend["Responsable"]
            if "Teléfono" in pend:
                vista["Teléfono"] = pend["Teléfono"] if mostrar_contacto else pend["Teléfono"].map(_ocultar_telefono)
            st.dataframe(vista, hide_index=True)

    # --- Gráficos ---
    g1, g2 = st.columns(2)
    embudo = df["Estado"].value_counts().reindex(ESTADOS, fill_value=0).reset_index()
    embudo.columns = ["Estado", "Clientes"]
    g1.plotly_chart(px.bar(embudo, x="Clientes", y="Estado", orientation="h", title="Clientes por estado",
                           category_orders={"Estado": ESTADOS}, labels={"Estado": ""}))
    if "Origen" in df:
        origenes = df["Origen"].replace("", "Sin dato").value_counts().reset_index()
        origenes.columns = ["Origen", "Clientes"]
        g2.plotly_chart(px.pie(origenes, names="Origen", values="Clientes", hole=0.45, title="¿Cómo nos conocen?"))
    if "Sector" in df and "Presupuesto (€/mes)" in df:
        sectores = df.groupby("Sector", as_index=False).agg(Clientes=("Empresa", "count"),
                                                            Presupuesto=("Presupuesto (€/mes)", "sum"))
        st.plotly_chart(px.bar(sectores.sort_values("Presupuesto"), x="Presupuesto", y="Sector", orientation="h",
                               text="Clientes", title="Presupuesto mensual por sector (el número es la cantidad de clientes)",
                               labels={"Presupuesto": "€ al mes", "Sector": ""}))

    # --- Listado completo ---
    st.subheader("Todos los contactos")
    f1, f2 = st.columns(2)
    estados_sel = f1.multiselect("Estado", ESTADOS, default=[e for e in ESTADOS if e in set(df["Estado"])])
    prior_sel = f2.multiselect("Prioridad", ["Alta", "Media", "Baja"], default=["Alta", "Media", "Baja"])
    lista = df[df["Estado"].isin(estados_sel) & df["Prioridad"].isin(prior_sel)].copy()
    lista["orden"] = lista["Prioridad"].map(ORDEN_PRIORIDAD).fillna(3)
    if "Puntuación" in lista:
        lista = lista.sort_values(["orden", "Puntuación"], ascending=[True, False])
    else:
        lista = lista.sort_values("orden")
    columnas = [c for c in ["Empresa", "Contacto", "Email", "Teléfono", "Sector", "Servicios", "Presupuesto",
                            "Puntuación", "Prioridad", "Estado", "Responsable", "Próximo seguimiento", "Notas"] if c in lista]
    tabla = lista[columnas].copy()
    if not mostrar_contacto:
        if "Email" in tabla:
            tabla["Email"] = tabla["Email"].map(_ocultar_email)
        if "Teléfono" in tabla:
            tabla["Teléfono"] = tabla["Teléfono"].map(_ocultar_telefono)
    if "Próximo seguimiento" in tabla:
        tabla["Próximo seguimiento"] = tabla["Próximo seguimiento"].dt.strftime("%d/%m/%Y")
    if "Puntuación" in tabla:
        tabla["Puntuación"] = tabla["Puntuación"].map(lambda v: inf.num(v))
    st.dataframe(tabla, hide_index=True)
    st.download_button("Descargar este listado (CSV para Excel)",
                       data=tabla.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name="clientes.csv", mime="text/csv")
    if not mostrar_contacto:
        st.caption("Emails y teléfonos ocultos para proteger los datos. Actívalos en la barra lateral solo si los necesitas.")

    # --- Puente con la herramienta de informes ---
    st.subheader("Preparar el informe de campaña de un cliente")
    candidatos = df[df["Estado"] == "Ganado"]
    if candidatos.empty:
        candidatos = df
        st.caption("Todavía no hay clientes ganados: se muestran todos.")
    empresa = st.selectbox("Cliente", candidatos["Empresa"].tolist())
    fila = candidatos[candidatos["Empresa"] == empresa].iloc[0]
    cpa = fila.get("CPA objetivo (€)")
    roas = fila.get("ROAS objetivo")
    cpa = float(cpa) if pd.notna(cpa) and cpa != "" else None
    roas = float(roas) if pd.notna(roas) and roas != "" else 3.0
    st.markdown(f"Objetivos que se pasarán al informe: **CPA objetivo {inf.eur(cpa, 2) if cpa else 'sin definir'}** "
                f"y **ROAS objetivo {inf.ratio(roas, 1)}**. Salen del precio medio que indicó el cliente en el formulario.")
    st.button("Ir al informe de este cliente", type="primary", on_click=_ir_a_informe, args=(empresa, cpa, roas))
