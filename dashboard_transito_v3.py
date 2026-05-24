"""
Dashboard de Tráfico Urbano — Versión 4
Autotransportes Presidente Alvear S.A.
Conectado a Google Sheets — HOJA BARRIDO
Columnas reales:
  TURNO · VUELTA · UNIDAD · DOMINIO · SERVICIO · CHOFER/ERES
  SALIDA PLANIFICADA · SALIDA REAL · SALIDA ADELANTO · SALIDA ATRASO
  LLEGADA PLANIFICADA · LLEGADA REAL · LLEGADA ADELANTO · LLEGADA ATRASO
  KM Recorrido · KM autorizado · Velocidad · CUMPLIMIENTO DEL SERVICIO · observaciones
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import re

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Tráfico Urbano — Presidente Alvear",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Syne', sans-serif !important; }
.main, .stApp { background-color: #0d1117; color: #e6edf3; }
.kpi-card {
    background: linear-gradient(135deg, #161b22 0%, #1c2128 100%);
    border: 1px solid #30363d; border-radius: 12px;
    padding: 18px 20px; text-align: center;
    position: relative; overflow: hidden;
}
.kpi-card::before {
    content:''; position:absolute; top:0; left:0; right:0; height:3px;
    background: linear-gradient(90deg, #238636, #2ea043);
}
.kpi-card.warning::before { background: linear-gradient(90deg, #d29922, #e3b341); }
.kpi-card.danger::before  { background: linear-gradient(90deg, #da3633, #f85149); }
.kpi-value { font-family:'Syne',sans-serif; font-size:2.4rem; font-weight:800; line-height:1; margin:6px 0 4px; }
.kpi-value.green  { color: #2ea043; }
.kpi-value.yellow { color: #e3b341; }
.kpi-value.red    { color: #f85149; }
.kpi-label { font-size:0.74rem; letter-spacing:0.08em; text-transform:uppercase; color:#8b949e; font-weight:500; }
.kpi-delta { font-size:0.79rem; margin-top:5px; color:#8b949e; }
.alert-banner {
    background: linear-gradient(90deg,#3d1a1a,#2d1b1b);
    border:1px solid #f8514930; border-left:4px solid #f85149;
    border-radius:8px; padding:10px 16px; margin-bottom:14px;
    font-size:0.87rem; color:#ffa198;
}
.info-banner {
    background: linear-gradient(90deg,#0d2114,#122a1a);
    border:1px solid #2ea04330; border-left:4px solid #2ea043;
    border-radius:8px; padding:10px 16px; margin-bottom:14px;
    font-size:0.87rem; color:#7ee787;
}
.success-banner {
    background: linear-gradient(90deg,#0d2114,#122a1a);
    border:1px solid #2ea04360; border-left:4px solid #2ea043;
    border-radius:8px; padding:10px 16px; margin-bottom:14px;
    font-size:0.87rem; color:#7ee787;
}
.section-header {
    font-family:'Syne',sans-serif; font-size:1.05rem; font-weight:700;
    color:#e6edf3; border-bottom:2px solid #21262d;
    padding-bottom:7px; margin-bottom:14px; letter-spacing:0.02em;
}
section[data-testid="stSidebar"] {
    background-color:#161b22 !important; border-right:1px solid #30363d;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# URL DE GOOGLE SHEETS — HOJA BARRIDO
# ─────────────────────────────────────────────
GSHEETS_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "15edBYCaxYgIqPWTBfCiPxcZabRLIt9nai7fxbrhpAZM"
    "/export?format=csv"
)

# ─────────────────────────────────────────────
# MAPEO DE COLUMNAS
# ─────────────────────────────────────────────
COLS_MAP = {
    "turno":                        "Turno",
    "tr turno":                     "Turno",
    "vuelta":                       "Vuelta",
    "unidad":                       "Unidad",
    "dominio":                      "Dominio",
    "tr dominio":                   "Dominio",
    "servicio":                     "Servicio",
    "chofer/eres":                  "Chofer",
    "choferes":                     "Chofer",
    "chofer":                       "Chofer",
    "salida planificada":           "SalidaPlan",
    "salida_planificada":           "SalidaPlan",
    "salida real":                  "SalidaReal",
    "salida-real":                  "SalidaReal",
    "salida adelanto":              "SalidaAdelanto",
    "salida - adelanto":            "SalidaAdelanto",
    "salida atraso":                "SalidaAtraso",
    "salida - atraso":              "SalidaAtraso",
    "llegada planificada":          "LlegadaPlan",
    "llegada - planificada":        "LlegadaPlan",
    "llegada real":                 "LlegadaReal",
    "llegada - real":               "LlegadaReal",
    "legada - real":                "LlegadaReal",
    "llegada adelanto":             "LlegadaAdelanto",
    "llegada - adelanto":           "LlegadaAdelanto",
    "llegada atraso":               "LlegadaAtraso",
    "llegada - atraso":             "LlegadaAtraso",
    "km recorrido":                 "KM_Recorrido",
    "km recorridos":                "KM_Recorrido",
    "km autorizado":                "KM_Autorizado",
    "km autorizados":               "KM_Autorizado",
    "velocidad":                    "VelocidadComercial",
    "velocidad comercial":          "VelocidadComercial",
    "velocidad c. planificada":     "VelocidadComercial",
    "velocidad o.":                 "VelocidadComercial",
    "cumplimiento del servicio":    "Cumplimiento",
    "tr cumplimiento del servicio": "Cumplimiento",
    "cumplimiento":                 "Cumplimiento",
    "observaciones":                "Observaciones",
    "observacion":                  "Observaciones",
}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def parse_datetime_col(serie):
    def _conv(v):
        if pd.isna(v): return pd.NaT
        s = str(v).strip()
        for fmt in ["%d/%m/%Y %H:%M", "%d/%m/%y %H:%M", "%d/%m/%Y %H:%M:%S",
                    "%d/%m/%y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d/%m/%y"]:
            try: return datetime.strptime(s, fmt)
            except: pass
        try: return pd.to_datetime(v, dayfirst=True)
        except: return pd.NaT
    return serie.apply(_conv)

def parse_delta_min(serie):
    def _conv(v):
        if pd.isna(v): return 0.0
        s = str(v).strip()
        if s in ["", "—", "-", "nan", "0:00:00", "0:00"]: return 0.0
        negativo = s.startswith("-")
        s = s.lstrip("-").strip()
        parts = s.split(":")
        try:
            if len(parts) == 3:
                val = int(parts[0])*60 + int(parts[1]) + int(parts[2])/60
            elif len(parts) == 2:
                val = int(parts[0])*60 + int(parts[1])
            else:
                val = float(s)
            return -val if negativo else val
        except: return 0.0
    return serie.apply(_conv)

def parse_km(serie):
    return pd.to_numeric(
        serie.astype(str).str.replace("km","",case=False)
             .str.replace(",",".").str.strip(),
        errors="coerce"
    )

def parse_velocidad(serie):
    return pd.to_numeric(
        serie.astype(str).str.replace("km/h","",case=False)
             .str.replace(",",".").str.strip(),
        errors="coerce"
    )

def parse_cumplimiento(serie):
    return pd.to_numeric(
        serie.astype(str).str.replace("%","")
             .str.replace(",",".").str.strip(),
        errors="coerce"
    )

# ─────────────────────────────────────────────
# PROCESAMIENTO PRINCIPAL
# ─────────────────────────────────────────────
def procesar_df(df):
    # Limpiar nombres de columnas
    df.columns = [
        re.sub(r"\s+", " ", str(c).replace("\n"," ").replace("\r"," ")).strip()
        for c in df.columns
    ]

    # Eliminar fila de encabezado secundario si existe (BARRIDO tiene a veces fila 2 duplicada)
    if len(df) > 0:
        primera = df.iloc[0]
        palabras_enc = ["turno","vuelta","unidad","dominio","servicio","salida","llegada","km","chofer"]
        matches = sum(1 for v in primera.astype(str).str.lower()
                     if any(p in v for p in palabras_enc))
        if matches >= 3:
            df = df.iloc[1:].reset_index(drop=True)

    # Renombrar columnas
    col_rename = {}
    for c in df.columns:
        key = re.sub(r"\s+", " ", str(c).lower().replace("\n"," ").replace("\r"," ")).strip()
        if key in COLS_MAP:
            col_rename[c] = COLS_MAP[key]
    df = df.rename(columns=col_rename)

    # Verificar columna mínima
    if "SalidaPlan" not in df.columns:
        cols_disp = list(df.columns)[:15]
        return None, f"No se encontró columna 'SALIDA PLANIFICADA'. Columnas disponibles: {cols_disp}"

    if len(df) == 0:
        return None, "La hoja no tiene datos."

    # Parseo de fechas
    df["SalidaPlan_dt"] = parse_datetime_col(df["SalidaPlan"])
    if "SalidaReal" in df.columns:
        df["SalidaReal_dt"] = parse_datetime_col(df["SalidaReal"])
    if "LlegadaPlan" in df.columns:
        df["LlegadaPlan_dt"] = parse_datetime_col(df["LlegadaPlan"])
    if "LlegadaReal" in df.columns:
        df["LlegadaReal_dt"] = parse_datetime_col(df["LlegadaReal"])

    df = df.dropna(subset=["SalidaPlan_dt"])
    if len(df) == 0:
        return None, "No se pudo parsear ninguna fecha en 'SalidaPlan'. Verificá el formato."

    df["Fecha"]     = df["SalidaPlan_dt"].dt.normalize()
    df["HoraProg"]  = df["SalidaPlan_dt"].dt.hour
    df["DiaSemana"] = df["Fecha"].dt.day_name()

    # Retraso salida — usa columna SalidaAtraso o calcula desde real-plan
    if "SalidaAtraso" in df.columns and df["SalidaAtraso"].notna().sum() > 0:
        df["RetrasoSalida_min"] = parse_delta_min(df["SalidaAtraso"])
    elif "SalidaReal_dt" in df.columns and df["SalidaReal_dt"].notna().any():
        df["RetrasoSalida_min"] = (
            (df["SalidaReal_dt"] - df["SalidaPlan_dt"]).dt.total_seconds() / 60
        ).fillna(0)
    else:
        df["RetrasoSalida_min"] = 0.0

    # Retraso llegada — usa columna LlegadaAtraso o calcula desde real-plan
    if "LlegadaAtraso" in df.columns and df["LlegadaAtraso"].notna().sum() > 0:
        df["RetrasoLlegada_min"] = parse_delta_min(df["LlegadaAtraso"])
    elif "LlegadaReal_dt" in df.columns and "LlegadaPlan_dt" in df.columns and df["LlegadaReal_dt"].notna().any():
        df["RetrasoLlegada_min"] = (
            (df["LlegadaReal_dt"] - df["LlegadaPlan_dt"]).dt.total_seconds() / 60
        ).fillna(0)
    else:
        df["RetrasoLlegada_min"] = df["RetrasoSalida_min"].copy()

    # KM
    if "KM_Recorrido" in df.columns:
        df["KM_Recorrido"] = parse_km(df["KM_Recorrido"])
    else:
        df["KM_Recorrido"] = np.nan
    if "KM_Autorizado" in df.columns:
        df["KM_Autorizado"] = parse_km(df["KM_Autorizado"])
    else:
        df["KM_Autorizado"] = df["KM_Recorrido"].copy()
    df["KM_Delta"] = df["KM_Recorrido"] - df["KM_Autorizado"]

    # Velocidad
    if "VelocidadComercial" in df.columns:
        df["VelocidadComercial"] = parse_velocidad(df["VelocidadComercial"])
    else:
        df["VelocidadComercial"] = np.nan

    # Cumplimiento
    if "Cumplimiento" in df.columns:
        df["Cumplimiento_num"] = parse_cumplimiento(df["Cumplimiento"])
    else:
        df["Cumplimiento_num"] = np.nan

    # Flags
    df["Puntual"]       = df["RetrasoSalida_min"] <= 5
    df["VueltaPerdida"] = (df["RetrasoSalida_min"] > 15).astype(int)

    # Estado obra desde observaciones
    if "Observaciones" in df.columns:
        df["EstadoObra"] = df["Observaciones"].apply(
            lambda v: "Con Obra" if (
                pd.notna(v) and
                str(v).strip() not in ["", "nan", "-", "0", "..."] and
                any(w in str(v).lower() for w in ["obra","desvío","desvio","corte","calle"])
            ) else "Sin Obra"
        )
    else:
        df["EstadoObra"] = "Sin Obra"

    # Turno derivado si no existe
    if "Turno" not in df.columns:
        def _turno(h):
            if pd.isna(h): return "Sin dato"
            if 5 <= h < 13:  return "Mañana"
            if 13 <= h < 20: return "Tarde"
            return "Noche"
        df["Turno"] = df["HoraProg"].apply(_turno)

    # Normalizar texto
    for col, fn in [("Unidad", lambda x: x.strip().upper()),
                    ("Servicio", lambda x: x.strip()),
                    ("Chofer", lambda x: x.strip().title()),
                    ("Dominio", lambda x: x.strip().upper())]:
        if col in df.columns:
            df[col] = df[col].astype(str).apply(fn)

    return df, None

# ─────────────────────────────────────────────
# CARGA GOOGLE SHEETS — con reintento y ttl
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="⏳ Actualizando desde Google Sheets…")
def cargar_gsheets(url):
    try:
        df = pd.read_csv(url)
        return procesar_df(df)
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────
# DATOS DE DEMO
# ─────────────────────────────────────────────
@st.cache_data
def datos_demo():
    rng = np.random.default_rng(42)
    servicios = ["544","525","532","540","548","523","549","560","570"]
    unidades  = [f"M500-{str(i).zfill(3)}" for i in range(50,130,5)]
    choferes  = ["García R.","López M.","Martínez J.","Rodríguez A.",
                 "Fernández C.","González L.","Pérez H.","Díaz S."]
    registros = []
    fecha_base = datetime(2026,1,30)
    for dia in range(14):
        fecha = fecha_base + timedelta(days=dia)
        hay_obra = dia in [2,3,7,8,9,12]
        for _ in range(rng.integers(45,70)):
            serv   = rng.choice(servicios)
            unidad = rng.choice(unidades)
            turno  = rng.choice(["Mañana","Tarde","Noche"])
            hora_p = {"Mañana":rng.integers(5,13),"Tarde":rng.integers(13,20),"Noche":rng.integers(20,24)}[turno]
            sal_plan = fecha.replace(hour=int(hora_p), minute=int(rng.choice([0,15,30,45])))
            retraso  = float(np.clip(rng.normal(2,6),-5,30))
            if hay_obra: retraso += float(rng.integers(5,18))
            km_aut = round(float(rng.uniform(18,35)),1)
            km_rec = km_aut + (round(float(rng.uniform(1,8)),1) if hay_obra else round(float(rng.uniform(-0.3,0.3)),1))
            vel    = round(km_rec / max(40,1)*60,1)
            registros.append({
                "Fecha":              fecha, "Turno": turno,
                "Unidad":             unidad, "Servicio": serv,
                "Chofer":             rng.choice(choferes),
                "SalidaPlan_dt":      sal_plan,
                "RetrasoSalida_min":  round(retraso,1),
                "RetrasoLlegada_min": round(retraso*0.8,1),
                "KM_Recorrido":       round(km_rec,1),
                "KM_Autorizado":      km_aut,
                "KM_Delta":           round(km_rec-km_aut,2),
                "VelocidadComercial": vel,
                "Cumplimiento_num":   float(max(60,round(100-retraso*1.5)) if retraso>5 else 100),
                "Observaciones":      f"Desvío obra calle {rng.integers(100,999)}" if hay_obra else "...",
                "EstadoObra":         "Con Obra" if hay_obra else "Sin Obra",
                "Puntual":            retraso<=5,
                "VueltaPerdida":      1 if retraso>15 else 0,
                "HoraProg":           int(hora_p),
                "DiaSemana":          fecha.strftime("%A"),
            })
    return pd.DataFrame(registros)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚌 Presidente Alvear")
    st.markdown("---")

    fuente = st.radio(
        "📡 Fuente de datos",
        ["Google Sheets (automático)", "Subir archivo manual"],
        index=0,
    )

    archivo = None
    if fuente == "Subir archivo manual":
        archivo = st.file_uploader("📂 Cargar planilla (.xlsx / .csv)", type=["xlsx","xls","csv"])

    st.markdown("---")

    # ── Cargar datos ──────────────────────────────────────────────────────
    if fuente == "Google Sheets (automático)":
        with st.spinner("Conectando con Google Sheets..."):
            df_raw, error = cargar_gsheets(GSHEETS_URL)
        if error:
            st.warning(f"⚠️ {error}\n\nMostrando datos de demo.")
            df_raw = datos_demo()
            modo = "demo"
        else:
            modo = "real"
            st.success(f"✅ {len(df_raw)} vueltas cargadas")
    elif archivo:
        try:
            raw = pd.read_csv(archivo) if archivo.name.endswith(".csv") else pd.read_excel(archivo)
            df_raw, error = procesar_df(raw)
            if error:
                st.error(error); df_raw = datos_demo(); modo = "demo"
            else:
                modo = "real"
        except Exception as e:
            st.error(str(e)); df_raw = datos_demo(); modo = "demo"
    else:
        df_raw = datos_demo(); modo = "demo"

    # ── Filtros ───────────────────────────────────────────────────────────
    st.markdown("### Filtros")

    fecha_min = df_raw["Fecha"].min().date()
    fecha_max = df_raw["Fecha"].max().date()

    col_d, col_h = st.columns(2)
    with col_d:
        fecha_desde = st.date_input("Desde", value=fecha_min, key="f_desde")
    with col_h:
        fecha_hasta = st.date_input("Hasta", value=fecha_max, key="f_hasta")

    if "Servicio" in df_raw.columns:
        servs = ["Todos"] + sorted(df_raw["Servicio"].dropna().unique().tolist())
        serv_sel = st.selectbox("🔢 Servicio / Línea", servs)
    else:
        serv_sel = "Todos"

    if "Unidad" in df_raw.columns:
        unids = ["Todas"] + sorted(df_raw["Unidad"].dropna().unique().tolist())
        unid_sel = st.selectbox("🚍 Unidad", unids)
    else:
        unid_sel = "Todas"

    if "Turno" in df_raw.columns:
        turnos_d = ["Todos"] + sorted(df_raw["Turno"].dropna().unique().tolist())
        turno_sel = st.selectbox("⏰ Turno", turnos_d)
    else:
        turno_sel = "Todos"

    obra_sel = st.selectbox("🚧 Estado de Obra", ["Todos","Con Obra","Sin Obra"])

    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    tag = "🟢 Datos reales · Google Sheets" if modo == "real" else "🟡 Datos de demo"
    st.markdown(
        f"<div style='font-size:0.75rem;color:#8b949e;text-align:center'>{tag}</div>",
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# FILTRADO
# ─────────────────────────────────────────────
df = df_raw.copy()
df = df[(df["Fecha"].dt.date >= fecha_desde) & (df["Fecha"].dt.date <= fecha_hasta)]
if serv_sel  != "Todos"  and "Servicio" in df.columns: df = df[df["Servicio"] == serv_sel]
if unid_sel  != "Todas"  and "Unidad"   in df.columns: df = df[df["Unidad"]   == unid_sel]
if turno_sel != "Todos"  and "Turno"    in df.columns: df = df[df["Turno"]    == turno_sel]
if obra_sel  != "Todos":                               df = df[df["EstadoObra"] == obra_sel]

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown(
    "<h1 style='font-family:Syne;font-size:1.9rem;font-weight:800;"
    "color:#e6edf3;margin-bottom:2px'>🚌 Dashboard Operativo — Presidente Alvear</h1>"
    "<p style='color:#8b949e;font-size:0.88rem;margin-top:0'>"
    "Salidas · Llegadas · KM · Velocidad · Cumplimiento</p>",
    unsafe_allow_html=True,
)

if modo == "demo":
    st.markdown(
        "<div class='info-banner'>ℹ️ Mostrando <b>datos de ejemplo</b>. "
        "Seleccioná Google Sheets para ver datos reales.</div>",
        unsafe_allow_html=True,
    )
else:
    rango = f"{fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}"
    st.markdown(
        f"<div class='success-banner'>✅ Datos reales desde Google Sheets · "
        f"<b>{len(df)} vueltas</b> en el período {rango} · "
        f"Se actualiza cada 5 min · Presioná '🔄 Actualizar datos' para forzar.</div>",
        unsafe_allow_html=True,
    )

# ── Alertas automáticas ───────────────────────────────────────────────────
alertas = []
if len(df) > 0:
    vp = df.groupby("Unidad")["VueltaPerdida"].sum().reset_index().query("VueltaPerdida > 3")
    for _, r in vp.iterrows():
        alertas.append(f"🟠 Unidad <b>{r['Unidad']}</b>: <b>{int(r['VueltaPerdida'])} vueltas perdidas</b> en el período.")
    vel_baja = df[df["VelocidadComercial"].notna() & (df["VelocidadComercial"] < 15)]
    if not vel_baja.empty:
        alertas.append(f"🔴 <b>{vel_baja['Unidad'].nunique()} unidades</b> con velocidad comercial < 15 km/h.")
    km_exc = df[df["KM_Delta"].notna() & (df["KM_Delta"] > 5)]
    if not km_exc.empty:
        alertas.append(f"📏 <b>{km_exc['Unidad'].nunique()} unidades</b> con desvío KM > 5 km.")
    cum_bajo = df[df["Cumplimiento_num"].notna() & (df["Cumplimiento_num"] < 80)]
    if not cum_bajo.empty:
        alertas.append(f"⚠️ <b>{cum_bajo['Unidad'].nunique()} unidades</b> con cumplimiento < 80%.")

if alertas:
    st.markdown(
        "<div class='alert-banner'>" + "<br>".join(alertas) + "</div>",
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────
def semaforo(val, ok, warn, inv=False):
    try:
        v = float(val)
        if np.isnan(v): return "yellow","warning"
    except: return "yellow","warning"
    if not inv:
        if v >= ok:   return "green",""
        if v >= warn: return "yellow","warning"
        return "red","danger"
    else:
        if v <= ok:   return "green",""
        if v <= warn: return "yellow","warning"
        return "red","danger"

if len(df) > 0:
    pct_punt = round(df["Puntual"].mean()*100,1)
    ret_sal  = round(df["RetrasoSalida_min"].mean(),1)
    ret_ll   = round(df["RetrasoLlegada_min"].mean(),1)
    vel_prom = round(df["VelocidadComercial"].mean(),1) if df["VelocidadComercial"].notna().any() else 0
    cum_prom = round(df["Cumplimiento_num"].mean(),1) if df["Cumplimiento_num"].notna().any() else 0
    total_sal = len(df)
    total_vp  = int(df["VueltaPerdida"].sum())
    km_total  = round(df["KM_Recorrido"].sum(),1) if df["KM_Recorrido"].notna().any() else 0
else:
    pct_punt=ret_sal=ret_ll=vel_prom=cum_prom=total_sal=total_vp=km_total=0

kpis = [
    ("% Puntualidad Salida", f"{pct_punt}%",    *semaforo(pct_punt,80,70),       f"Umbral: 70% · {total_sal} servicios"),
    ("Retraso Salida Prom",  f"{ret_sal} min",  *semaforo(ret_sal,5,12,True),    "Min sobre hora planificada"),
    ("Retraso Llegada Prom", f"{ret_ll} min",   *semaforo(ret_ll,5,15,True),     "Min sobre llegada planificada"),
    ("Vel. Comercial Prom",  f"{vel_prom} km/h",*semaforo(vel_prom,17,15),       "Umbral mínimo: 15 km/h"),
    ("Cumplimiento Servicio",f"{cum_prom}%",    *semaforo(cum_prom,95,80),       "Promedio del período"),
]

cols = st.columns(5)
for col, (label,val,vc,cc,delta) in zip(cols,kpis):
    with col:
        st.markdown(
            f"<div class='kpi-card {cc}'>"
            f"<div class='kpi-label'>{label}</div>"
            f"<div class='kpi-value {vc}'>{val}</div>"
            f"<div class='kpi-delta'>{delta}</div>"
            f"</div>", unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# NUEVAS TARJETAS KM + RANKING UNIDADES
# ─────────────────────────────────────────────
st.markdown("<div class='section-header'>📏 Kilómetros del período</div>", unsafe_allow_html=True)

km_rec_total = round(df["KM_Recorrido"].sum(),1) if df["KM_Recorrido"].notna().any() else 0
km_aut_total = round(df["KM_Autorizado"].sum(),1) if df["KM_Autorizado"].notna().any() else 0
km_dif       = round(km_rec_total - km_aut_total, 1)
km_prom_v    = round(df["KM_Recorrido"].mean(),1) if df["KM_Recorrido"].notna().any() else 0

c1,c2,c3,c4 = st.columns(4)
with c1:
    st.metric("Km recorridos totales", f"{km_rec_total:,.1f} km", help="Suma total de KM recorridos en el período")
with c2:
    st.metric("Km autorizados totales", f"{km_aut_total:,.1f} km", help="Suma total de KM autorizados en el período")
with c3:
    st.metric("Diferencia (rec. − aut.)", f"{km_dif:+,.1f} km",
              delta=f"{(km_dif/km_aut_total*100):.1f}%" if km_aut_total>0 else None)
with c4:
    st.metric("Km promedio por vuelta", f"{km_prom_v:.1f} km", help="Promedio de km recorridos por vuelta")

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# RANKING DE UNIDADES POR KM
# ─────────────────────────────────────────────
st.markdown("<div class='section-header'>🏆 Ranking de unidades por kilometraje</div>", unsafe_allow_html=True)

if "Unidad" in df.columns and df["KM_Recorrido"].notna().any():
    rank_df = df.groupby("Unidad").agg(
        KM_Total   =("KM_Recorrido","sum"),
        KM_Aut     =("KM_Autorizado","sum"),
        Vueltas    =("KM_Recorrido","count"),
        Puntualidad=("Puntual",lambda x: round(x.mean()*100,1)),
        SalAtraso  =("RetrasoSalida_min","mean"),
    ).reset_index()
    rank_df["KM_Delta"] = rank_df["KM_Total"] - rank_df["KM_Aut"]
    rank_df["KM_xVuelta"] = (rank_df["KM_Total"] / rank_df["Vueltas"]).round(1)
    rank_df = rank_df.sort_values("KM_Total", ascending=False).reset_index(drop=True)

    # Podio top 3
    top3 = rank_df.head(3)
    medals = ["🥇","🥈","🥉"]
    cols_podio = st.columns(3)
    for i,(_, row) in enumerate(top3.iterrows()):
        with cols_podio[i]:
            delta_col = "normal" if row["KM_Delta"] >= 0 else "inverse"
            st.metric(
                f"{medals[i]} {row['Unidad']}",
                f"{row['KM_Total']:,.1f} km",
                f"{row['KM_Delta']:+.1f} km vs autorizado",
                delta_color=delta_col,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Gráfico horizontal top N
    top_n = st.slider("Mostrar top N unidades", 5, min(30, len(rank_df)), 10)
    top_data = rank_df.head(top_n)

    colors = []
    for _, r in top_data.iterrows():
        if r["KM_Delta"] > 5:       colors.append("#388bfd")
        elif r["KM_Delta"] < -5:    colors.append("#f85149")
        else:                        colors.append("#2ea043")

    fig_rank = go.Figure(go.Bar(
        x=top_data["KM_Total"].round(1),
        y=top_data["Unidad"],
        orientation="h",
        marker_color=colors,
        text=top_data["KM_Total"].round(1).astype(str)+" km",
        textposition="outside",
        textfont=dict(color="#e6edf3", size=10),
        customdata=top_data[["Vueltas","KM_xVuelta","Puntualidad","KM_Delta","SalAtraso"]],
        hovertemplate=(
            "<b>%{y}</b><br>"
            "KM total: %{x:.1f} km<br>"
            "Vueltas: %{customdata[0]}<br>"
            "KM/vuelta: %{customdata[1]:.1f}<br>"
            "Puntualidad: %{customdata[2]:.1f}%<br>"
            "Δ KM: %{customdata[3]:+.1f} km<br>"
            "Retraso prom: %{customdata[4]:.1f} min<extra></extra>"
        ),
    ))
    fig_rank.update_layout(
        paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
        height=max(300, top_n*32+60),
        margin=dict(t=10,b=10,l=90,r=80),
        xaxis=dict(title="KM recorridos",tickfont=dict(color="#8b949e"),
                   gridcolor="#21262d",color="#8b949e"),
        yaxis=dict(tickfont=dict(color="#e6edf3",size=11),gridcolor="#21262d"),
        font_color="#e6edf3",
    )
    st.plotly_chart(fig_rank, use_container_width=True)
    st.markdown(
        "<small style='color:#8b949e'>🟢 Dentro de rango · 🔵 KM extra > 5 km · 🔴 KM faltante > 5 km</small>",
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────
# FILA: Semáforo + Heatmap
# ─────────────────────────────────────────────
col1, col2 = st.columns([1,2])
with col1:
    st.markdown("<div class='section-header'>🚦 Semáforo de Puntualidad</div>", unsafe_allow_html=True)
    gc = "#2ea043" if pct_punt >= 80 else ("#e3b341" if pct_punt >= 70 else "#f85149")
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=pct_punt,
        number={"suffix":"%","font":{"size":48,"color":gc,"family":"Syne"}},
        delta={"reference":80,"increasing":{"color":"#2ea043"},"decreasing":{"color":"#f85149"}},
        gauge={
            "axis":{"range":[0,100],"tickwidth":1,"tickcolor":"#30363d","tickfont":{"color":"#8b949e"}},
            "bar":{"color":gc,"thickness":0.25},
            "bgcolor":"#161b22","borderwidth":0,
            "steps":[{"range":[0,70],"color":"#2d1b1b"},
                     {"range":[70,80],"color":"#2d2200"},
                     {"range":[80,100],"color":"#0d2114"}],
            "threshold":{"line":{"color":"#e3b341","width":3},"value":70},
        },
        title={"text":"Puntualidad en Salidas","font":{"size":13,"color":"#8b949e"}},
    ))
    fig_g.update_layout(paper_bgcolor="#0d1117",plot_bgcolor="#0d1117",
                        height=255,margin=dict(t=30,b=5,l=20,r=20),font_color="#e6edf3")
    st.plotly_chart(fig_g, use_container_width=True)

with col2:
    st.markdown("<div class='section-header'>🌡️ Heatmap — Retraso de Salida por Hora y Día</div>", unsafe_allow_html=True)
    orden_dias  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    labels_dia  = {"Monday":"Lun","Tuesday":"Mar","Wednesday":"Mié",
                   "Thursday":"Jue","Friday":"Vie","Saturday":"Sáb","Sunday":"Dom"}
    hm = df.groupby(["DiaSemana","HoraProg"])["RetrasoSalida_min"].mean().reset_index()
    hm["DiaLabel"] = hm["DiaSemana"].map(labels_dia)
    hm["DiaOrd"]   = hm["DiaSemana"].map({d:i for i,d in enumerate(orden_dias)})
    hm = hm.sort_values("DiaOrd")
    if len(hm) > 0:
        pivot = hm.pivot_table(index="DiaLabel",columns="HoraProg",
                               values="RetrasoSalida_min",aggfunc="mean")
        dias_ord = [labels_dia[d] for d in orden_dias if labels_dia[d] in pivot.index]
        pivot = pivot.reindex(dias_ord)
        fig_hm = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[f"{int(h):02d}:00" for h in pivot.columns],
            y=pivot.index.tolist(),
            colorscale=[[0,"#0d2114"],[0.4,"#e3b341"],[1,"#f85149"]],
            text=np.round(pivot.values,1),texttemplate="%{text}m",
            textfont={"size":10,"color":"#fff"},hoverongaps=False,
            colorbar=dict(title=dict(text="Min",font=dict(color="#8b949e")),
                          tickfont=dict(color="#8b949e")),
        ))
        fig_hm.update_layout(
            paper_bgcolor="#0d1117",plot_bgcolor="#161b22",
            height=255,margin=dict(t=5,b=30,l=55,r=20),
            xaxis=dict(tickfont=dict(color="#8b949e"),gridcolor="#21262d"),
            yaxis=dict(tickfont=dict(color="#8b949e"),gridcolor="#21262d"),
            font_color="#e6edf3",
        )
        st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.info("Sin datos para el heatmap.")

# ─────────────────────────────────────────────
# FILA: Retraso por Unidad + KM por Servicio
# ─────────────────────────────────────────────
col3, col4 = st.columns([1,1])
with col3:
    st.markdown("<div class='section-header'>📊 Retraso Promedio por Unidad</div>", unsafe_allow_html=True)
    atr = df.groupby("Unidad").agg(
        RetrasoSalida=("RetrasoSalida_min","mean"),
        RetrasoLlegada=("RetrasoLlegada_min","mean"),
        VueltasPerdidas=("VueltaPerdida","sum"),
        Servicios=("Puntual","count"),
        Puntualidad=("Puntual",lambda x: round(x.mean()*100,1)),
    ).reset_index().sort_values("RetrasoSalida",ascending=True)
    atr["Color"] = atr.apply(
        lambda r: "#f85149" if r["VueltasPerdidas"]>3 or r["RetrasoSalida"]>12
        else ("#e3b341" if r["RetrasoSalida"]>5 else "#2ea043"), axis=1)
    fig_bar = go.Figure(go.Bar(
        x=atr["RetrasoSalida"].round(1), y=atr["Unidad"],
        orientation="h", marker_color=atr["Color"],
        text=atr["RetrasoSalida"].round(1).astype(str)+" min",
        textposition="outside", textfont=dict(color="#e6edf3",size=10),
        customdata=atr[["VueltasPerdidas","Servicios","Puntualidad","RetrasoLlegada"]],
        hovertemplate=(
            "<b>%{y}</b><br>Retraso salida: %{x:.1f} min<br>"
            "Retraso llegada: %{customdata[3]:.1f} min<br>"
            "Vueltas perdidas: %{customdata[0]}<br>"
            "Puntualidad: %{customdata[2]:.1f}%<extra></extra>"
        ),
    ))
    fig_bar.update_layout(
        paper_bgcolor="#0d1117",plot_bgcolor="#161b22",
        height=340,margin=dict(t=5,b=10,l=80,r=65),
        xaxis=dict(title="Min retraso prom",tickfont=dict(color="#8b949e"),
                   gridcolor="#21262d",color="#8b949e"),
        yaxis=dict(tickfont=dict(color="#e6edf3",size=10),gridcolor="#21262d"),
        font_color="#e6edf3",bargap=0.25,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col4:
    st.markdown("<div class='section-header'>📏 KM Autorizado vs Recorrido por Servicio</div>", unsafe_allow_html=True)
    if "Servicio" in df.columns:
        km_agg = df.groupby("Servicio").agg(
            KM_Aut=("KM_Autorizado","mean"),
            KM_Rec=("KM_Recorrido","mean"),
        ).reset_index().dropna().sort_values("KM_Rec",ascending=True)
        if len(km_agg) > 0:
            fig_km = go.Figure()
            fig_km.add_trace(go.Bar(name="KM Autorizado",x=km_agg["KM_Aut"].round(1),y=km_agg["Servicio"],
                orientation="h",marker_color="#238636",opacity=0.9))
            fig_km.add_trace(go.Bar(name="KM Recorrido",x=km_agg["KM_Rec"].round(1),y=km_agg["Servicio"],
                orientation="h",marker_color="#388bfd",opacity=0.9))
            fig_km.update_layout(
                barmode="group",paper_bgcolor="#0d1117",plot_bgcolor="#161b22",
                height=340,margin=dict(t=5,b=10,l=60,r=20),
                xaxis=dict(title="km promedio",tickfont=dict(color="#8b949e"),
                           gridcolor="#21262d",color="#8b949e"),
                yaxis=dict(tickfont=dict(color="#e6edf3",size=11),gridcolor="#21262d"),
                legend=dict(font=dict(color="#e6edf3"),bgcolor="#161b22",bordercolor="#30363d",borderwidth=1),
                font_color="#e6edf3",bargap=0.2,bargroupgap=0.05,
            )
            st.plotly_chart(fig_km, use_container_width=True)
    else:
        st.info("Sin datos de servicio.")

# ─────────────────────────────────────────────
# EVOLUCIÓN TEMPORAL + IMPACTO OBRA
# ─────────────────────────────────────────────
col5, col6 = st.columns([2,1])
with col5:
    st.markdown("<div class='section-header'>📈 Evolución Diaria — Puntualidad y Retraso</div>", unsafe_allow_html=True)
    evol = df.groupby("Fecha").agg(
        Puntualidad=("Puntual",lambda x: round(x.mean()*100,1)),
        RetrasoSalida=("RetrasoSalida_min","mean"),
        RetrasoLlegada=("RetrasoLlegada_min","mean"),
        EstadoObra=("EstadoObra",lambda x: "Con Obra" if "Con Obra" in x.values else "Sin Obra"),
    ).reset_index()
    fig_ev = make_subplots(specs=[[{"secondary_y":True}]])
    shapes = []
    for _, row in evol[evol["EstadoObra"]=="Con Obra"].iterrows():
        shapes.append(dict(type="rect",xref="x",yref="paper",
            x0=row["Fecha"]-timedelta(hours=12),x1=row["Fecha"]+timedelta(hours=12),
            y0=0,y1=1,fillcolor="#e3b341",opacity=0.08,layer="below",line_width=0))
    fig_ev.add_trace(go.Scatter(x=evol["Fecha"],y=evol["Puntualidad"],name="% Puntualidad",
        line=dict(color="#2ea043",width=2.5),mode="lines+markers",marker=dict(size=6)),secondary_y=False)
    fig_ev.add_trace(go.Scatter(x=evol["Fecha"],y=evol["RetrasoSalida"].round(1),name="Retraso salida",
        line=dict(color="#f85149",width=2,dash="dot"),mode="lines+markers",marker=dict(size=5)),secondary_y=True)
    fig_ev.add_trace(go.Scatter(x=evol["Fecha"],y=evol["RetrasoLlegada"].round(1),name="Retraso llegada",
        line=dict(color="#e3b341",width=2,dash="dash"),mode="lines+markers",marker=dict(size=5)),secondary_y=True)
    fig_ev.add_hline(y=70,line_dash="dash",line_color="#e3b341",
                     annotation_text="Umbral 70%",annotation_font_color="#e3b341",secondary_y=False)
    fig_ev.update_layout(
        paper_bgcolor="#0d1117",plot_bgcolor="#161b22",height=290,
        margin=dict(t=10,b=30,l=20,r=20),shapes=shapes,
        legend=dict(font=dict(color="#e6edf3"),bgcolor="#161b22",bordercolor="#30363d",borderwidth=1),
        font_color="#e6edf3",
        xaxis=dict(tickfont=dict(color="#8b949e"),gridcolor="#21262d",tickformat="%d/%m"),
    )
    fig_ev.update_yaxes(tickfont=dict(color="#8b949e"),gridcolor="#21262d",
                        title_text="% Puntualidad",title_font=dict(color="#8b949e"),secondary_y=False)
    fig_ev.update_yaxes(title_text="Min retraso",title_font=dict(color="#8b949e"),
                        tickfont=dict(color="#8b949e"),secondary_y=True)
    st.plotly_chart(fig_ev, use_container_width=True)

with col6:
    st.markdown("<div class='section-header'>🚧 Retraso: Con Obra vs Sin Obra</div>", unsafe_allow_html=True)
    oc = df.groupby("EstadoObra").agg(
        RetrasoSalida=("RetrasoSalida_min","mean"),
        Servicios=("Puntual","count"),
    ).reset_index()
    fig_obra = go.Figure()
    for _, r in oc.iterrows():
        color = "#f85149" if r["EstadoObra"]=="Con Obra" else "#2ea043"
        fig_obra.add_trace(go.Bar(name=r["EstadoObra"],x=[r["EstadoObra"]],
            y=[round(r["RetrasoSalida"],1)],marker_color=color,
            text=f"{round(r['RetrasoSalida'],1)} min\n({r['Servicios']} servicios)",
            textposition="outside",textfont=dict(color="#e6edf3",size=12)))
    fig_obra.update_layout(
        paper_bgcolor="#0d1117",plot_bgcolor="#161b22",height=290,
        margin=dict(t=15,b=30,l=20,r=20),showlegend=False,
        xaxis=dict(tickfont=dict(color="#e6edf3",size=13),gridcolor="#21262d"),
        yaxis=dict(title="Min retraso prom",tickfont=dict(color="#8b949e"),
                   gridcolor="#21262d",title_font=dict(color="#8b949e")),
        font_color="#e6edf3",bargap=0.45,
    )
    st.plotly_chart(fig_obra, use_container_width=True)

# ─────────────────────────────────────────────
# TABLA RESUMEN POR UNIDAD
# ─────────────────────────────────────────────
st.markdown("<div class='section-header'>📋 Resumen por Unidad — Alertas y Estado</div>",
            unsafe_allow_html=True)

grp_cols = ["Unidad"]
if "Servicio" in df.columns: grp_cols.append("Servicio")
if "Chofer"   in df.columns: grp_cols.append("Chofer")

tabla = df.groupby(grp_cols).agg(
    Servicios        =("Puntual","count"),
    Puntualidad_pct  =("Puntual",lambda x: round(x.mean()*100,1)),
    RetrasoSalida    =("RetrasoSalida_min","mean"),
    RetrasoLlegada   =("RetrasoLlegada_min","mean"),
    VueltasPerdidas  =("VueltaPerdida","sum"),
    KM_Aut           =("KM_Autorizado","mean"),
    KM_Rec           =("KM_Recorrido","mean"),
    KM_Delta         =("KM_Delta","mean"),
    Vel_Comercial    =("VelocidadComercial","mean"),
    Cumplimiento     =("Cumplimiento_num","mean"),
).reset_index()

for c,r in [("RetrasoSalida",1),("RetrasoLlegada",1),("Vel_Comercial",1),
            ("KM_Aut",1),("KM_Rec",1),("KM_Delta",2),("Cumplimiento",1)]:
    tabla[c] = tabla[c].round(r)

tabla_disp = tabla.rename(columns={
    "Puntualidad_pct":  "Puntualidad %",
    "RetrasoSalida":    "Retraso Salida",
    "RetrasoLlegada":   "Retraso Llegada",
    "VueltasPerdidas":  "Vueltas Perdidas",
    "KM_Aut":           "KM Autorizado",
    "KM_Rec":           "KM Recorrido",
    "KM_Delta":         "Desvío KM",
    "Vel_Comercial":    "Vel. km/h",
    "Cumplimiento":     "Cumplimiento %",
})

def highlight_tabla(row):
    styles = [""] * len(row)
    names = row.index.tolist()
    def idx(n): return names.index(n) if n in names else -1
    if row.get("Vueltas Perdidas", 0) > 3:
        i = idx("Unidad")
        if i >= 0: styles[i] = "background-color:#3d2200;color:#e3b341;font-weight:700"
    vc = row.get("Vel. km/h", None)
    if vc is not None and pd.notna(vc) and vc < 15:
        i = idx("Vel. km/h")
        if i >= 0: styles[i] = "background-color:#3d1a1a;color:#f85149;font-weight:700"
    if row.get("Puntualidad %", 100) < 70:
        i = idx("Puntualidad %")
        if i >= 0: styles[i] = "background-color:#3d1a1a;color:#f85149;font-weight:700"
    km_d = row.get("Desvío KM", None)
    if km_d is not None and pd.notna(km_d) and km_d > 5:
        i = idx("Desvío KM")
        if i >= 0: styles[i] = "background-color:#1a2a3d;color:#79c0ff;font-weight:700"
    cum = row.get("Cumplimiento %", None)
    if cum is not None and pd.notna(cum) and cum < 80:
        i = idx("Cumplimiento %")
        if i >= 0: styles[i] = "background-color:#3d1a1a;color:#f85149;font-weight:700"
    return styles

fmt_tabla = {
    "Puntualidad %":  "{:.1f}%",
    "Retraso Salida": "{:.1f}",
    "Retraso Llegada":"{:.1f}",
    "KM Autorizado":  "{:.1f}",
    "KM Recorrido":   "{:.1f}",
    "Desvío KM":      "{:+.2f}",
    "Vel. km/h":      "{:.1f}",
    "Cumplimiento %": "{:.1f}%",
}
st.dataframe(
    tabla_disp.style.apply(highlight_tabla,axis=1).format(fmt_tabla,na_rep="—"),
    use_container_width=True, height=360,
)
st.markdown(
    "<small style='color:#8b949e'>"
    "🟠 Naranja: >3 vueltas perdidas &nbsp;|&nbsp; "
    "🔴 Rojo: vel <15 km/h, puntualidad <70% o cumplimiento <80% &nbsp;|&nbsp; "
    "🔵 Azul: desvío KM > 5 km</small>",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# EXPANDER: Observaciones recientes
# ─────────────────────────────────────────────
if "Observaciones" in df.columns:
    with st.expander("📝 Observaciones y Desvíos recientes"):
        obs_df = df[
            df["Observaciones"].notna() &
            (~df["Observaciones"].astype(str).str.strip().isin(["","...","nan","0","-"]))
        ].copy()
        if len(obs_df) > 0:
            cols_obs = ["Fecha"]
            for c in ["Turno","Servicio","Unidad","Chofer","RetrasoSalida_min","Observaciones"]:
                if c in obs_df.columns: cols_obs.append(c)
            obs_df = obs_df[cols_obs].sort_values("Fecha",ascending=False).head(50)
            obs_df["Fecha"] = obs_df["Fecha"].dt.strftime("%d/%m/%Y")
            if "RetrasoSalida_min" in obs_df.columns:
                obs_df = obs_df.rename(columns={"RetrasoSalida_min":"Retraso (min)"})
            st.dataframe(obs_df, use_container_width=True, height=280)
        else:
            st.info("No hay observaciones registradas en el período.")

st.markdown(
    "<div style='text-align:center;color:#30363d;font-size:0.75rem;margin-top:30px;'>"
    "Autotransportes Presidente Alvear S.A. · Dashboard Operativo v4 · "
    "Conectado a Google Sheets</div>",
    unsafe_allow_html=True,
)
