"""
Dashboard de Tráfico Urbano — Líneas 544 & 525
Versión adaptada a estructura de planilla real:
  A: Fecha (DD/MM)  B: ID Servicio  C: Interno  D: Salida Prog. (HH:MM)
  E: Salida Real (HH:MM)  F: Llegada Prog. (HH:MM)  G: Llegada Real (HH:MM)
  H: Km Reales  I: Incidente (Categoría)  J: Desvío Obras (observacion)
  K: Km Autorizados  ← columna agregada por el usuario
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import io, random

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Tráfico Urbano 544·525",
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
.kpi-value { font-family:'Syne',sans-serif; font-size:2.6rem; font-weight:800; line-height:1; margin:6px 0 4px; }
.kpi-value.green  { color: #2ea043; }
.kpi-value.yellow { color: #e3b341; }
.kpi-value.red    { color: #f85149; }
.kpi-label { font-size:0.75rem; letter-spacing:0.08em; text-transform:uppercase; color:#8b949e; font-weight:500; }
.kpi-delta { font-size:0.8rem; margin-top:5px; color:#8b949e; }
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
.section-header {
    font-family:'Syne',sans-serif; font-size:1.05rem; font-weight:700;
    color:#e6edf3; border-bottom:2px solid #21262d;
    padding-bottom:7px; margin-bottom:14px; letter-spacing:0.02em;
}
section[data-testid="stSidebar"] {
    background-color:#161b22 !important; border-right:1px solid #30363d;
}
.upload-hint {
    background:#161b22; border:1px dashed #30363d; border-radius:10px;
    padding:20px; text-align:center; color:#8b949e; font-size:0.9rem;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# COLUMNAS ESPERADAS (nombres internos)
# ─────────────────────────────────────────────
COLS_MAP = {
    "Fecha":          "Fecha",
    "ID Servicio":    "Linea",
    "Interno":        "Interno",
    "Salida Prog.":   "SalidaProg",
    "Salida Real":    "SalidaReal",
    "Llegada Prog.":  "LlegadaProg",
    "Llegada Real":   "LlegadaReal",
    "Km Reales":      "KM_Reales",
    "Incidente":      "Incidente",
    "Desvío Obras":   "DesvioObras",
    "Km Autorizados": "KM_Autorizados",   # columna extra que agrega el usuario
}

# KM autorizados por defecto si NO existe la columna K
KM_DEFAULT = {"544": 22.5, "525": 19.0}


# ─────────────────────────────────────────────
# HELPERS DE PARSING
# ─────────────────────────────────────────────
def parse_hhmm(serie):
    """Convierte HH:MM (string o timedelta) a minutos desde medianoche."""
    def _conv(v):
        if pd.isna(v): return np.nan
        if isinstance(v, (int, float)): return v * 1440  # Excel fracción de día
        s = str(v).strip()
        if ":" in s:
            parts = s.split(":")
            try: return int(parts[0]) * 60 + int(parts[1])
            except: return np.nan
        return np.nan
    return serie.apply(_conv)

def minutos_a_hhmm(minutos):
    """Convierte minutos desde medianoche a string HH:MM."""
    if pd.isna(minutos): return "—"
    h = int(minutos) // 60
    m = int(minutos) % 60
    return f"{h:02d}:{m:02d}"

def parse_fecha(serie):
    """Intenta parsear DD/MM, DD/MM/YY, DD/MM/YYYY. Asume año 2025 si falta."""
    def _conv(v):
        if pd.isna(v): return pd.NaT
        s = str(v).strip()
        for fmt in ["%d/%m/%Y", "%d/%m/%y", "%d/%m"]:
            try:
                d = datetime.strptime(s, fmt)
                if d.year == 1900: d = d.replace(year=2025)
                return d
            except: pass
        try: return pd.to_datetime(v)
        except: return pd.NaT
    return serie.apply(_conv)


# ─────────────────────────────────────────────
# CARGA Y PROCESAMIENTO
# ─────────────────────────────────────────────
@st.cache_data(show_spinner="Procesando planilla…")
def procesar_archivo(contenido_bytes, nombre_archivo):
    """Lee el archivo y devuelve el DataFrame procesado."""
    try:
        if nombre_archivo.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contenido_bytes))
        else:
            df = pd.read_excel(io.BytesIO(contenido_bytes), header=0)
    except Exception as e:
        return None, f"Error leyendo archivo: {e}"

    # ── Renombrar columnas al nombre interno ──────────────────────────────
    df.columns = [str(c).strip() for c in df.columns]

    # Fila 2 puede ser la fila de tipos (DD/MM, HH:MM…) — la saltamos si no hay datos
    if df.shape[0] > 0:
        primera = df.iloc[0]
        if primera.astype(str).str.contains("DD|HH|Num|Listado|Categoría|observacion",
                                              case=False, na=False).any():
            df = df.iloc[1:].reset_index(drop=True)

    col_rename = {}
    for col_orig, col_int in COLS_MAP.items():
        matches = [c for c in df.columns if c.strip().lower() == col_orig.lower()]
        if matches:
            col_rename[matches[0]] = col_int

    df = df.rename(columns=col_rename)

    # Verificar columnas mínimas
    requeridas = ["Fecha", "Linea", "Interno", "SalidaProg", "SalidaReal"]
    faltantes = [r for r in requeridas if r not in df.columns]
    if faltantes:
        return None, f"Columnas no encontradas: {faltantes}. Verificá los encabezados."

    # ── Parseo de fechas ──────────────────────────────────────────────────
    df["Fecha"] = parse_fecha(df["Fecha"])
    df = df.dropna(subset=["Fecha"])

    # ── Parseo de horarios → minutos ──────────────────────────────────────
    for col in ["SalidaProg", "SalidaReal", "LlegadaProg", "LlegadaReal"]:
        if col in df.columns:
            df[col + "_min"] = parse_hhmm(df[col])

    # ── Minutos de retraso en SALIDA ──────────────────────────────────────
    df["MinutosRetraso"] = (df["SalidaReal_min"] - df["SalidaProg_min"]).clip(lower=0)

    # ── Duración real del servicio ────────────────────────────────────────
    if "LlegadaReal_min" in df.columns and "SalidaReal_min" in df.columns:
        df["DuracionReal_min"] = (df["LlegadaReal_min"] - df["SalidaReal_min"]).clip(lower=1)
    else:
        df["DuracionReal_min"] = np.nan

    # ── KM Autorizados ────────────────────────────────────────────────────
    if "KM_Autorizados" not in df.columns:
        df["KM_Autorizados"] = df["Linea"].astype(str).str.strip().map(KM_DEFAULT).fillna(20.0)
    else:
        df["KM_Autorizados"] = pd.to_numeric(df["KM_Autorizados"], errors="coerce").fillna(20.0)

    df["KM_Reales"] = pd.to_numeric(df.get("KM_Reales", np.nan), errors="coerce")
    df["KM_Delta"]  = df["KM_Reales"] - df["KM_Autorizados"]

    # ── Velocidad comercial  (km/h) ───────────────────────────────────────
    df["VelocidadComercial"] = np.where(
        df["DuracionReal_min"] > 0,
        (df["KM_Reales"] / df["DuracionReal_min"] * 60).round(1),
        np.nan,
    )

    # ── Hora programada (para heatmap) ───────────────────────────────────
    df["HoraProg"] = (df["SalidaProg_min"] // 60).astype("Int64")

    # ── Puntual: retraso ≤ 5 min ─────────────────────────────────────────
    df["Puntual"] = df["MinutosRetraso"] <= 5

    # ── Estado de obra ────────────────────────────────────────────────────
    if "DesvioObras" in df.columns:
        df["EstadoObra"] = df["DesvioObras"].apply(
            lambda v: "Con Obra" if (pd.notna(v) and str(v).strip() not in ["", "nan", "-", "0"]) else "Sin Obra"
        )
    else:
        df["EstadoObra"] = "Sin Obra"

    # ── Vueltas perdidas: retraso > 15 min ────────────────────────────────
    df["VueltasPerdidas"] = (df["MinutosRetraso"] > 15).astype(int)

    # ── Normalizar campos de texto ────────────────────────────────────────
    df["Interno"] = df["Interno"].astype(str).str.strip().str.upper()
    df["Linea"]   = df["Linea"].astype(str).str.strip()
    df["DiaSemana"] = df["Fecha"].dt.day_name()

    return df, None


# ─────────────────────────────────────────────
# CARGA DESDE GOOGLE SHEETS
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Actualizando desde Google Sheets…")
def cargar_gsheets(url):
    """Lee el CSV publicado de Google Sheets y lo procesa igual que un archivo subido."""
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=10) as r:
            contenido = r.read()
        return procesar_archivo(contenido, "gsheets.csv")
    except Exception as e:
        return None, str(e)


# ─────────────────────────────────────────────
# DATOS DE DEMO (si no hay archivo)
# ─────────────────────────────────────────────
@st.cache_data
def datos_demo():
    rng = np.random.default_rng(42)
    lineas   = ["544", "525"]
    internos = ["500-055","500-063","500-071","500-082","500-094",
                "525-011","525-022","525-033","525-044"]
    incidentes = ["","","","Mecánica","Accidente de tránsito","","","Lluvia intensa",""]
    registros = []
    fecha_base = datetime(2025, 6, 1)
    for dia in range(14):
        fecha = fecha_base + timedelta(days=dia)
        hay_obra = dia in [2, 3, 7, 8, 9, 12]
        for _ in range(rng.integers(38, 55)):
            linea   = rng.choice(lineas)
            idx     = rng.integers(0,5) if linea=="544" else rng.integers(5,9)
            interno = internos[idx]
            hora_p  = rng.choice([7,8,9,13,14,18,19,20])
            min_p   = rng.choice([0,15,30,45])
            sp_min  = hora_p*60 + min_p
            retraso = int(np.clip(rng.normal(3,8),-2,35))
            if hay_obra: retraso += int(rng.integers(5,20))
            sr_min  = sp_min + max(0, retraso)
            km_aut  = KM_DEFAULT.get(linea, 20.0)
            km_rec  = km_aut + (round(float(rng.uniform(1,8)),1) if hay_obra else round(float(rng.uniform(-0.5,0.5)),1))
            dur     = int(rng.integers(40,90))
            vel     = round(km_rec / dur * 60, 1) if dur > 0 else 0
            desvio  = f"Desvío por obra calle {rng.integers(100,999)}" if hay_obra else ""
            inc     = incidentes[idx] if rng.random() < 0.1 else ""
            registros.append({
                "Fecha":         fecha,
                "Linea":         linea,
                "Interno":       interno,
                "SalidaProg_min": sp_min,
                "SalidaReal_min": sr_min,
                "LlegadaReal_min": sr_min + dur,
                "MinutosRetraso":  max(0, retraso),
                "KM_Autorizados":  km_aut,
                "KM_Reales":       round(km_rec,1),
                "KM_Delta":        round(km_rec - km_aut, 2),
                "VelocidadComercial": vel,
                "HoraProg":        hora_p,
                "Puntual":         retraso <= 5,
                "EstadoObra":      "Con Obra" if hay_obra else "Sin Obra",
                "VueltasPerdidas": 1 if retraso > 15 else 0,
                "Incidente":       inc,
                "DesvioObras":     desvio,
                "DiaSemana":       fecha.strftime("%A"),
                "DuracionReal_min": dur,
            })
    return pd.DataFrame(registros)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚌 Panel de Control")
    st.markdown("---")

    GSHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR0BjgSLvDcElS5jV3nbJWrl-G7cllcMal5OjKdM-mytmYaklubYex2Qn2K5soumVmPWMMh8CYDdpkK/pub?gid=1242609982&single=true&output=csv"

    fuente = st.radio("📡 Fuente de datos", ["Google Sheets (automático)", "Subir archivo manual"], index=0)

    archivo = None
    if fuente == "Subir archivo manual":
        archivo = st.file_uploader(
            "📂 Cargar planilla (.xlsx / .csv)",
            type=["xlsx", "xls", "csv"],
        )

    st.markdown("---")

    # Cargar datos
    if fuente == "Google Sheets (automático)":
        df_raw, error = cargar_gsheets(GSHEETS_URL)
        if error:
            st.warning(f"⚠️ No se pudo leer Google Sheets: {error}\nMostrando datos de demo.")
            df_raw = datos_demo()
            modo = "demo"
        else:
            modo = "real"
    elif archivo:
        df_raw, error = procesar_archivo(archivo.read(), archivo.name)
        if error:
            st.error(error)
            df_raw = datos_demo()
            modo = "demo"
        else:
            modo = "real"
    else:
        df_raw = datos_demo()
        modo = "demo"

    # Filtros
    fechas = st.date_input(
        "📅 Rango de Fechas",
        value=(df_raw["Fecha"].min().date(), df_raw["Fecha"].max().date()),
        min_value=df_raw["Fecha"].min().date(),
        max_value=df_raw["Fecha"].max().date(),
    )

    lineas_disp = ["Todas"] + sorted(df_raw["Linea"].dropna().unique().tolist())
    linea_sel   = st.selectbox("🔢 Línea / Servicio", lineas_disp)

    internos_disp = ["Todos"] + sorted(df_raw["Interno"].dropna().unique().tolist())
    interno_sel   = st.selectbox("🚍 Interno", internos_disp)

    obra_sel = st.selectbox("🚧 Estado de Obra", ["Todos", "Con Obra", "Sin Obra"])

    # Turno derivado del horario programado
    def turno_desde_hora(h):
        if pd.isna(h): return "Sin dato"
        if 5 <= h < 13:  return "Mañana"
        if 13 <= h < 20: return "Tarde"
        return "Noche"
    df_raw["Turno"] = df_raw["HoraProg"].apply(turno_desde_hora)
    turno_sel = st.selectbox("⏰ Turno", ["Todos", "Mañana", "Tarde", "Noche"])

    # Incidente
    if "Incidente" in df_raw.columns:
        incidentes_disp = ["Todos"] + sorted(
            df_raw["Incidente"].dropna().astype(str)
            .loc[lambda s: s.str.strip() != ""].unique().tolist()
        )
        incidente_sel = st.selectbox("⚠️ Tipo de Incidente", incidentes_disp)
    else:
        incidente_sel = "Todos"

    st.markdown("---")
    tag = "🟢 Datos reales" if modo == "real" else "🟡 Datos de demo"
    fuente_label = "Google Sheets" if fuente == "Google Sheets (automático)" else (archivo.name if archivo else "Sin archivo")
    st.markdown(
        f"<div style='font-size:0.75rem;color:#8b949e;text-align:center'>"
        f"{tag}<br><b style='color:#e6edf3'>{fuente_label}</b>"
        f"</div>", unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# FILTRADO
# ─────────────────────────────────────────────
df = df_raw.copy()
if len(fechas) == 2:
    df = df[(df["Fecha"].dt.date >= fechas[0]) & (df["Fecha"].dt.date <= fechas[1])]
if linea_sel   != "Todas":  df = df[df["Linea"]      == linea_sel]
if interno_sel != "Todos":  df = df[df["Interno"]    == interno_sel]
if obra_sel    != "Todos":  df = df[df["EstadoObra"] == obra_sel]
if turno_sel   != "Todos":  df = df[df["Turno"]      == turno_sel]
if incidente_sel != "Todos" and "Incidente" in df.columns:
    df = df[df["Incidente"].astype(str).str.strip() == incidente_sel]


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown(
    "<h1 style='font-family:Syne;font-size:1.9rem;font-weight:800;"
    "color:#e6edf3;margin-bottom:2px'>🚌 Dashboard de Tráfico Urbano</h1>"
    "<p style='color:#8b949e;font-size:0.88rem;margin-top:0'>"
    "Líneas 544 · 525 — Monitoreo Operativo · Salidas · Retrasos · KM · Desvíos</p>",
    unsafe_allow_html=True,
)

if modo == "demo":
    st.markdown(
        "<div class='info-banner'>ℹ️ Mostrando <b>datos de ejemplo</b>. "
        "Subí tu planilla desde el panel lateral para ver datos reales.</div>",
        unsafe_allow_html=True,
    )

# ── Alertas automáticas ───────────────────────────────────────────────────
alertas = []
if len(df) > 0:
    int_criticos = (
        df.groupby("Interno")["VueltasPerdidas"].sum()
        .reset_index().query("VueltasPerdidas > 3")
    )
    for _, r in int_criticos.iterrows():
        alertas.append(
            f"🟠 Interno <b>{r['Interno']}</b>: "
            f"<b>{int(r['VueltasPerdidas'])} vueltas perdidas</b> en el período seleccionado."
        )
    vel_baja = df[df["VelocidadComercial"].notna() & (df["VelocidadComercial"] < 15)]
    if not vel_baja.empty:
        n = vel_baja["Interno"].nunique()
        alertas.append(f"🔴 <b>{n} {'interno' if n==1 else 'internos'}</b> con velocidad comercial <b>< 15 km/h</b>.")
    km_exceso = df[df["KM_Delta"].notna() & (df["KM_Delta"] > 5)]
    if not km_exceso.empty:
        alertas.append(
            f"📏 <b>{km_exceso['Interno'].nunique()} internos</b> con desvío de KM superior a 5 km "
            f"(probable desvío por obra no registrado)."
        )

if alertas:
    st.markdown(
        "<div class='alert-banner'>" + "<br>".join(alertas) + "</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────
def kpi_color(val, umbrales, inv=False):
    """umbrales = (ok, warn). inv=True: menor es mejor."""
    if pd.isna(val): return "yellow", "warning"
    if not inv:
        if val >= umbrales[0]: return "green", ""
        if val >= umbrales[1]: return "yellow", "warning"
        return "red", "danger"
    else:
        if val <= umbrales[0]: return "green", ""
        if val <= umbrales[1]: return "yellow", "warning"
        return "red", "danger"

if len(df) > 0:
    pct_punt   = round(df["Puntual"].mean() * 100, 1)
    ret_prom   = round(df["MinutosRetraso"].mean(), 1)
    total_vp   = int(df["VueltasPerdidas"].sum())
    vel_prom   = round(df["VelocidadComercial"].mean(), 1) if df["VelocidadComercial"].notna().any() else 0
    km_delta   = round(df["KM_Delta"].mean(), 2) if df["KM_Delta"].notna().any() else 0
    total_sal  = len(df)
    dias_obra  = df[df["EstadoObra"]=="Con Obra"]["Fecha"].dt.date.nunique()
else:
    pct_punt = ret_prom = total_vp = vel_prom = km_delta = total_sal = dias_obra = 0

kpis = [
    ("% Puntualidad",       f"{pct_punt}%",
     *kpi_color(pct_punt,  (80,70)),        f"Umbral crítico: 70% · {total_sal} salidas"),
    ("Retraso Salida Prom", f"{ret_prom} min",
     *kpi_color(ret_prom,  (5,12), inv=True), "Minutos sobre horario programado"),
    ("Vueltas Perdidas",    str(total_vp),
     *kpi_color(total_vp,  (3,10), inv=True), "Retrasos > 15 min en el período"),
    ("Vel. Comercial Prom", f"{vel_prom} km/h",
     *kpi_color(vel_prom,  (17,15)),         "Umbral mínimo: 15 km/h"),
    ("Días con Obra",       str(dias_obra),
     ("yellow" if dias_obra>0 else "green"),
     ("warning" if dias_obra>0 else ""),     "Fechas con desvío activo"),
]

cols = st.columns(5)
for col, (label, val, vc, cc, delta) in zip(cols, kpis):
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
# FILA 1: Gauge + Heatmap
# ─────────────────────────────────────────────
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("<div class='section-header'>🚦 Semáforo de Salidas</div>", unsafe_allow_html=True)
    gc = "#2ea043" if pct_punt >= 80 else ("#e3b341" if pct_punt >= 70 else "#f85149")
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=pct_punt,
        number={"suffix":"%","font":{"size":50,"color":gc,"family":"Syne"}},
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
    st.markdown("<div class='section-header'>🌡️ Heatmap — Retraso Promedio por Hora y Día</div>", unsafe_allow_html=True)
    orden_dias = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    labels_dia = {"Monday":"Lun","Tuesday":"Mar","Wednesday":"Mié",
                  "Thursday":"Jue","Friday":"Vie","Saturday":"Sáb","Sunday":"Dom"}
    hm = (df.groupby(["DiaSemana","HoraProg"])["MinutosRetraso"]
            .mean().reset_index())
    hm["DiaLabel"] = hm["DiaSemana"].map(labels_dia)
    hm["DiaOrd"]   = hm["DiaSemana"].map({d:i for i,d in enumerate(orden_dias)})
    hm = hm.sort_values("DiaOrd")

    if len(hm) > 0:
        pivot = hm.pivot_table(index="DiaLabel",columns="HoraProg",
                               values="MinutosRetraso",aggfunc="mean")
        dias_ord = [labels_dia[d] for d in orden_dias if labels_dia[d] in pivot.index]
        pivot = pivot.reindex(dias_ord)
        fig_hm = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[f"{int(h):02d}:00" for h in pivot.columns],
            y=pivot.index.tolist(),
            colorscale=[[0,"#0d2114"],[0.4,"#e3b341"],[1,"#f85149"]],
            text=np.round(pivot.values,1),
            texttemplate="%{text}m",
            textfont={"size":10,"color":"#fff"},
            hoverongaps=False,
            colorbar=dict(
                title=dict(text="Min", font=dict(color="#8b949e")),
                tickfont=dict(color="#8b949e"),
            ),
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
        st.info("Sin datos para mostrar el heatmap.")


# ─────────────────────────────────────────────
# FILA 2: Barras por interno + KM comparador
# ─────────────────────────────────────────────
col3, col4 = st.columns([1,1])

with col3:
    st.markdown("<div class='section-header'>📊 Retraso Promedio en Salida por Interno</div>", unsafe_allow_html=True)
    atr = (df.groupby("Interno").agg(
        RetrasoPromedio=("MinutosRetraso","mean"),
        VueltasPerdidas=("VueltasPerdidas","sum"),
        Salidas=("Puntual","count"),
        Puntualidad=("Puntual",lambda x: round(x.mean()*100,1)),
    ).reset_index().sort_values("RetrasoPromedio",ascending=True))

    atr["Color"] = atr.apply(
        lambda r: "#f85149" if r["VueltasPerdidas"]>3 or r["RetrasoPromedio"]>12
        else ("#e3b341" if r["RetrasoPromedio"]>6 else "#2ea043"), axis=1)

    fig_bar = go.Figure(go.Bar(
        x=atr["RetrasoPromedio"].round(1), y=atr["Interno"],
        orientation="h", marker_color=atr["Color"],
        text=atr["RetrasoPromedio"].round(1).astype(str)+" min",
        textposition="outside", textfont=dict(color="#e6edf3",size=11),
        customdata=atr[["VueltasPerdidas","Salidas","Puntualidad"]],
        hovertemplate=(
            "<b>%{y}</b><br>Retraso prom: %{x:.1f} min<br>"
            "Vueltas perdidas: %{customdata[0]}<br>"
            "Salidas: %{customdata[1]}<br>"
            "Puntualidad: %{customdata[2]:.1f}%<extra></extra>"
        ),
    ))
    fig_bar.update_layout(
        paper_bgcolor="#0d1117",plot_bgcolor="#161b22",
        height=320,margin=dict(t=5,b=10,l=80,r=65),
        xaxis=dict(title="Min retraso prom",tickfont=dict(color="#8b949e"),
                   gridcolor="#21262d",color="#8b949e"),
        yaxis=dict(tickfont=dict(color="#e6edf3",size=11),gridcolor="#21262d"),
        font_color="#e6edf3",bargap=0.28,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col4:
    st.markdown("<div class='section-header'>📏 KM Autorizados vs KM Reales por Interno</div>", unsafe_allow_html=True)
    km_agg = (df.groupby("Interno").agg(
        KM_Aut=("KM_Autorizados","mean"),
        KM_Rec=("KM_Reales","mean"),
    ).reset_index().dropna().sort_values("KM_Rec",ascending=True))

    if len(km_agg) > 0:
        fig_km = go.Figure()
        fig_km.add_trace(go.Bar(
            name="KM Autorizados", x=km_agg["KM_Aut"].round(1), y=km_agg["Interno"],
            orientation="h", marker_color="#238636", opacity=0.9,
        ))
        fig_km.add_trace(go.Bar(
            name="KM Reales", x=km_agg["KM_Rec"].round(1), y=km_agg["Interno"],
            orientation="h", marker_color="#388bfd", opacity=0.9,
        ))
        fig_km.update_layout(
            barmode="group",paper_bgcolor="#0d1117",plot_bgcolor="#161b22",
            height=320,margin=dict(t=5,b=10,l=80,r=20),
            xaxis=dict(title="km promedio",tickfont=dict(color="#8b949e"),
                       gridcolor="#21262d",color="#8b949e"),
            yaxis=dict(tickfont=dict(color="#e6edf3",size=11),gridcolor="#21262d"),
            legend=dict(font=dict(color="#e6edf3"),bgcolor="#161b22",
                        bordercolor="#30363d",borderwidth=1),
            font_color="#e6edf3",bargap=0.2,bargroupgap=0.05,
        )
        st.plotly_chart(fig_km, use_container_width=True)
    else:
        st.info("Sin datos de KM para mostrar.")


# ─────────────────────────────────────────────
# FILA 3: Evolución temporal + Impacto obra
# ─────────────────────────────────────────────
col5, col6 = st.columns([2,1])

with col5:
    st.markdown("<div class='section-header'>📈 Evolución Diaria — Puntualidad y Retraso</div>", unsafe_allow_html=True)
    evol = df.groupby("Fecha").agg(
        Puntualidad=("Puntual",lambda x: round(x.mean()*100,1)),
        RetrasoMedio=("MinutosRetraso","mean"),
        EstadoObra=("EstadoObra",lambda x: "Con Obra" if "Con Obra" in x.values else "Sin Obra"),
        TotalSalidas=("Puntual","count"),
    ).reset_index()

    fig_ev = make_subplots(specs=[[{"secondary_y":True}]])
    shapes = []
    for _, row in evol[evol["EstadoObra"]=="Con Obra"].iterrows():
        shapes.append(dict(
            type="rect", xref="x", yref="paper",
            x0=row["Fecha"]-timedelta(hours=12),
            x1=row["Fecha"]+timedelta(hours=12),
            y0=0, y1=1, fillcolor="#e3b341",
            opacity=0.08, layer="below", line_width=0,
        ))
    fig_ev.add_trace(go.Scatter(
        x=evol["Fecha"],y=evol["Puntualidad"],
        name="% Puntualidad",line=dict(color="#2ea043",width=2.5),
        mode="lines+markers",marker=dict(size=6),
        customdata=evol[["TotalSalidas","EstadoObra"]],
        hovertemplate="<b>%{x|%d/%m}</b><br>Puntualidad: %{y}%<br>"
                      "Salidas: %{customdata[0]}<br>Obra: %{customdata[1]}<extra></extra>",
    ),secondary_y=False)
    fig_ev.add_trace(go.Scatter(
        x=evol["Fecha"],y=evol["RetrasoMedio"].round(1),
        name="Retraso prom (min)",line=dict(color="#f85149",width=2,dash="dot"),
        mode="lines+markers",marker=dict(size=5),
        hovertemplate="<b>%{x|%d/%m}</b><br>Retraso prom: %{y:.1f} min<extra></extra>",
    ),secondary_y=True)
    fig_ev.add_hline(y=70,line_dash="dash",line_color="#e3b341",
                     annotation_text="Umbral 70%",annotation_font_color="#e3b341",
                     secondary_y=False)
    fig_ev.update_layout(
        paper_bgcolor="#0d1117",plot_bgcolor="#161b22",
        height=280,margin=dict(t=10,b=30,l=20,r=20),
        legend=dict(font=dict(color="#e6edf3"),bgcolor="#161b22",
                    bordercolor="#30363d",borderwidth=1,x=0.01,y=0.99),
        font_color="#e6edf3",
        xaxis=dict(tickfont=dict(color="#8b949e"),gridcolor="#21262d",tickformat="%d/%m"),
        shapes=shapes,
    )
    fig_ev.update_yaxes(tickfont=dict(color="#8b949e"),gridcolor="#21262d",
                         title_text="% Puntualidad",title_font=dict(color="#8b949e"),secondary_y=False)
    fig_ev.update_yaxes(title_text="Minutos retraso",title_font=dict(color="#8b949e"),
                         tickfont=dict(color="#8b949e"),secondary_y=True)
    st.plotly_chart(fig_ev, use_container_width=True)

with col6:
    st.markdown("<div class='section-header'>🚧 Impacto de Obra vs Sin Obra</div>", unsafe_allow_html=True)
    oc = df.groupby("EstadoObra").agg(
        RetrasoMedio=("MinutosRetraso","mean"),
        Salidas=("Puntual","count"),
        Puntualidad=("Puntual",lambda x: round(x.mean()*100,1)),
    ).reset_index()

    fig_obra = go.Figure()
    for _, r in oc.iterrows():
        color = "#f85149" if r["EstadoObra"]=="Con Obra" else "#2ea043"
        fig_obra.add_trace(go.Bar(
            name=r["EstadoObra"],x=[r["EstadoObra"]],
            y=[round(r["RetrasoMedio"],1)],marker_color=color,
            text=f"{round(r['RetrasoMedio'],1)} min<br>({r['Salidas']} salidas)",
            textposition="outside",textfont=dict(color="#e6edf3",size=12),
        ))
    fig_obra.update_layout(
        paper_bgcolor="#0d1117",plot_bgcolor="#161b22",
        height=280,margin=dict(t=15,b=30,l=20,r=20),
        showlegend=False,
        xaxis=dict(tickfont=dict(color="#e6edf3",size=13),gridcolor="#21262d"),
        yaxis=dict(title="Min retraso prom",tickfont=dict(color="#8b949e"),
                   gridcolor="#21262d",title_font=dict(color="#8b949e")),
        font_color="#e6edf3",bargap=0.45,
    )
    st.plotly_chart(fig_obra, use_container_width=True)


# ─────────────────────────────────────────────
# TABLA RESUMEN POR INTERNO
# ─────────────────────────────────────────────
st.markdown("<div class='section-header'>📋 Resumen por Interno — Alertas y Estado</div>",
            unsafe_allow_html=True)

tabla = df.groupby(["Interno","Linea"]).agg(
    Salidas           = ("Puntual","count"),
    Puntualidad_pct   = ("Puntual",lambda x: round(x.mean()*100,1)),
    Retraso_prom      = ("MinutosRetraso","mean"),
    VueltasPerdidas   = ("VueltasPerdidas","sum"),
    KM_Aut_prom       = ("KM_Autorizados","mean"),
    KM_Real_prom      = ("KM_Reales","mean"),
    Vel_Comercial     = ("VelocidadComercial","mean"),
).reset_index()

tabla["Retraso_prom"]  = tabla["Retraso_prom"].round(1)
tabla["Vel_Comercial"] = tabla["Vel_Comercial"].round(1)
tabla["KM_Delta_prom"] = (tabla["KM_Real_prom"] - tabla["KM_Aut_prom"]).round(2)
tabla["KM_Aut_prom"]   = tabla["KM_Aut_prom"].round(1)
tabla["KM_Real_prom"]  = tabla["KM_Real_prom"].round(1)

def highlight_row(row):
    styles = [""] * len(row)
    names  = row.index.tolist()
    def idx(n):
        return names.index(n) if n in names else -1
    # Usar nombres YA renombrados (los que ve tabla_disp)
    if row["Vueltas Perdidas"] > 3:
        i = idx("Interno")
        if i >= 0: styles[i] = "background-color:#3d2200;color:#e3b341;font-weight:700"
    vc = row.get("Vel. Comercial (km/h)", None)
    if vc is not None and pd.notna(vc) and vc < 15:
        i = idx("Vel. Comercial (km/h)")
        if i >= 0: styles[i] = "background-color:#3d1a1a;color:#f85149;font-weight:700"
    if row["Puntualidad %"] < 70:
        i = idx("Puntualidad %")
        if i >= 0: styles[i] = "background-color:#3d1a1a;color:#f85149;font-weight:700"
    km_d = row.get("Desvío KM prom", None)
    if km_d is not None and pd.notna(km_d) and km_d > 5:
        i = idx("Desvío KM prom")
        if i >= 0: styles[i] = "background-color:#1a2a3d;color:#79c0ff;font-weight:700"
    return styles

tabla_disp = tabla.rename(columns={
    "Puntualidad_pct": "Puntualidad %",
    "Retraso_prom":    "Retraso prom (min)",
    "VueltasPerdidas": "Vueltas Perdidas",
    "Vel_Comercial":   "Vel. Comercial (km/h)",
    "KM_Aut_prom":     "KM Autorizados",
    "KM_Real_prom":    "KM Reales",
    "KM_Delta_prom":   "Desvío KM prom",
})

st.dataframe(
    tabla_disp.style
        .apply(highlight_row, axis=1)
        .format({
            "Puntualidad %":       "{:.1f}%",
            "Retraso prom (min)":  "{:.1f}",
            "Vel. Comercial (km/h)":"{:.1f}",
            "KM Autorizados":      "{:.1f}",
            "KM Reales":           "{:.1f}",
            "Desvío KM prom":      "{:+.2f}",
        }, na_rep="—"),
    use_container_width=True,
    height=340,
)

st.markdown(
    "<div style='font-size:0.74rem;color:#8b949e;margin-top:6px'>"
    "🟠 <b>Naranja</b>: interno con >3 vueltas perdidas &nbsp;|&nbsp; "
    "🔴 <b>Rojo</b>: vel. comercial <15 km/h o puntualidad <70% &nbsp;|&nbsp; "
    "🔵 <b>Azul</b>: desvío KM > 5 km (posible obra no reportada)"
    "</div>",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# INSTRUCCIONES DE CARGA
# ─────────────────────────────────────────────
with st.expander("📖 ¿Cómo preparar tu planilla para cargarla?"):
    st.markdown("""
**Encabezados esperados** (fila 1 del Excel — exactamente estos nombres):

| Columna | Nombre | Formato |
|---------|--------|---------|
| A | `Fecha` | DD/MM o DD/MM/YYYY |
| B | `ID Servicio` | Ej: 544, 525 |
| C | `Interno` | Ej: 500-055 |
| D | `Salida Prog.` | HH:MM |
| E | `Salida Real` | HH:MM |
| F | `Llegada Prog.` | HH:MM |
| G | `Llegada Real` | HH:MM |
| H | `Km Reales` | Número (ej: 22.5) |
| I | `Incidente` | Texto libre o categoría |
| J | `Desvío Obras` | Texto si hubo obra, vacío si no |
| K | `Km Autorizados` | Número (columna que agregás vos) |

**Tips:**
- La fila 2 con tipos de dato (`DD/MM`, `HH:MM`…) se ignora automáticamente.
- Si no agregás la columna **Km Autorizados**, el sistema usa valores por defecto: 544=22.5km / 525=19km.
- El campo **Desvío Obras** activa el estado "Con Obra" si tiene cualquier texto (no vacío).
- Las horas se pueden ingresar como `08:30` o como formato hora de Excel.
""")
