import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import qrcode
from io import BytesIO
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import io

# ============================================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Sostenibilidad Universitaria | UNAH",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# CONEXIÓN A FIREBASE
# ============================================================
if not firebase_admin._apps:
    cred_dict = dict(st.secrets["firebase"])
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()
COLLECTION_NAME = "respuestas_sostenibilidad"

# ============================================================
# PARES SEMÁNTICOS POR CATEGORÍA
# ============================================================
CATEGORIAS = {
    "Valor y relevancia": [
        ("Innecesaria", "Indispensable"),
        ("Irrelevante", "Fundamental"),
        ("Secundaria", "Prioritaria"),
        ("Superficial", "Profunda")
    ],
    "Aplicabilidad y utilidad": [
        ("Teórica", "Práctica"),
        ("Inútil", "Provechosa"),
        ("Abstracta", "Aplicable")
    ],
    "Carga y dificultad": [
        ("Compleja", "Sencilla"),
        ("Agobiante", "Estimulante"),
        ("Tediosa", "Ágil"),
        ("Inalcanzable", "Factible")
    ],
    "Compromiso ético y emocional": [
        ("Impuesta", "Voluntaria"),
        ("Aburrida", "Interesante"),
        ("Indiferente", "Comprometida")
    ]
}
PAIRS = [par for cat in CATEGORIAS.values() for par in cat]
TOTAL_PAIRS = len(PAIRS)

ADMIN_PASS = "admin1234"

# ============================================================
# ESTILOS CSS GLOBALES  (sin f-string → sin problemas de llaves)
# ============================================================
st.html("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root {
    --blue:   #002C9E;
    --navy:   #051461;
    --gold:   #D4A017;
    --gold2:  #F5C842;
    --teal:   #1A7A82;
    --white:  #FFFFFF;
    --bg:     #F4F6FB;
    --bg2:    #EEF1F8;
    --card:   #FFFFFF;
    --card2:  #F8FAFF;
    --text:   #1A2340;
    --muted:  #6B7A99;
}

*, *::before, *::after { box-sizing: border-box; }
html, body, .stApp {
    background: var(--bg) !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--text) !important;
}

/* ── HEADER ── */
.unah-header {
    background: linear-gradient(135deg, var(--navy) 0%, var(--blue) 55%, var(--teal) 100%);
    border-bottom: 4px solid var(--gold);
    padding: 20px 36px; border-radius: 0 0 20px 20px;
    margin-bottom: 28px;
    display: flex; align-items: center; gap: 22px;
    box-shadow: 0 6px 30px rgba(0,44,158,0.18);
}
.unah-header-text { flex: 1; }
.unah-header h1 {
    font-size: 1.55rem; font-weight: 800;
    color: #FFFFFF !important; margin: 0;
    letter-spacing: -0.01em;
}
.unah-header p {
    color: var(--gold2) !important; margin: 4px 0 0;
    font-size: 0.83rem; font-weight: 500; letter-spacing: 0.05em;
}
.unah-logo {
    width: 70px; height: 70px; border-radius: 50%;
    border: 2px solid var(--gold2);
    object-fit: contain; background: white; padding: 3px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
}

/* ── BADGE EN VIVO ── */
.live-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.5);
    color: #FFFFFF; font-weight: 700; font-size: 0.78rem;
    padding: 5px 16px; border-radius: 99px;
    animation: pulse-badge 2s ease-in-out infinite;
    white-space: nowrap;
}
.live-dot {
    width: 8px; height: 8px; background: #FF4444; border-radius: 50%;
    animation: blink 1s step-start infinite;
}
@keyframes blink { 50% { opacity: 0; } }
@keyframes pulse-badge {
    0%,100% { box-shadow: 0 0 0 0 rgba(255,255,255,0.3); }
    50%      { box-shadow: 0 0 0 6px rgba(255,255,255,0); }
}

/* ── KPI GRID ── */
.kpi-grid {
    display: grid; grid-template-columns: repeat(4,1fr);
    gap: 16px; margin: 0 0 24px;
}
@media (max-width:900px) { .kpi-grid { grid-template-columns: repeat(2,1fr); } }
.kpi-card {
    background: var(--card);
    border: 1px solid rgba(0,44,158,0.12);
    border-radius: 16px; padding: 22px 18px;
    text-align: center; position: relative; overflow: hidden;
    transition: transform 0.25s, box-shadow 0.25s;
    box-shadow: 0 2px 12px rgba(0,44,158,0.08);
}
.kpi-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 4px; background: linear-gradient(90deg, var(--blue), var(--gold));
}
.kpi-card:hover { transform: translateY(-4px); box-shadow: 0 10px 28px rgba(0,44,158,0.15); }
.kpi-icon   { font-size: 2rem; margin-bottom: 8px; }
.kpi-value  { font-size: 2.2rem; font-weight: 800; color: var(--blue); line-height: 1; }
.kpi-label  { font-size: 0.8rem; color: var(--muted); margin-top: 6px; font-weight: 500; }
.kpi-sub    { font-size: 0.75rem; color: var(--teal); margin-top: 3px; font-weight: 600; }

/* ── SECCIÓN CARDS ── */
.section-card {
    background: var(--card);
    border: 1px solid rgba(0,44,158,0.1); border-radius: 16px;
    padding: 24px; margin-bottom: 20px;
    box-shadow: 0 2px 12px rgba(0,44,158,0.06);
}
.section-title {
    font-size: 0.95rem; font-weight: 700; color: var(--blue);
    text-transform: uppercase; letter-spacing: 0.08em;
    border-bottom: 2px solid var(--gold);
    padding-bottom: 10px; margin-bottom: 18px;
}

/* ── TABS ── */
button[data-baseweb="tab"] > div[data-testid="stMarkdownContainer"] > p {
    color: var(--muted) !important; font-weight: 600 !important;
    font-size: 0.95rem !important; font-family: 'Inter', sans-serif !important;
}
button[data-baseweb="tab"][aria-selected="true"] > div[data-testid="stMarkdownContainer"] > p {
    color: var(--blue) !important; font-weight: 700 !important;
}
div[data-baseweb="tab-highlight"] { background-color: var(--blue) !important; }
div[data-baseweb="tab-border"]    { background-color: rgba(0,44,158,0.15) !important; }

/* ── FORMULARIO ── */
.cat-header {
    background: linear-gradient(90deg, var(--blue), #1A45C8);
    border-left: 4px solid var(--gold); border-radius: 8px;
    padding: 10px 18px; margin: 24px 0 16px;
    font-size: 1rem; font-weight: 700; color: #FFFFFF;
    letter-spacing: 0.04em;
    box-shadow: 0 2px 8px rgba(0,44,158,0.2);
}
.word-left  { text-align: right; font-weight: 700; font-size: 1rem; color: #C0392B !important; padding-top: 10px; }
.word-right { text-align: left;  font-weight: 700; font-size: 1rem; color: #1A7A82 !important; padding-top: 10px; }
.instrucciones-box {
    background: linear-gradient(135deg, rgba(0,44,158,0.05), rgba(26,122,130,0.05));
    border: 1px solid rgba(0,44,158,0.15); border-left: 4px solid var(--gold);
    border-radius: 12px; padding: 20px 24px; margin-bottom: 24px;
    color: var(--text) !important;
}
.prog-label   { font-size: 0.78rem; color: var(--blue); font-weight: 600; text-align: right; margin-bottom: 4px; }
.prog-wrapper { background: rgba(0,44,158,0.1); border-radius: 99px; height: 8px; margin: 6px 0 20px; overflow: hidden; }
.prog-fill    { height: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--blue), var(--gold)); transition: width 0.4s ease; }

/* ── QR ── */
.qr-container {
    background: var(--card);
    border: 1px solid rgba(0,44,158,0.12); border-radius: 16px;
    padding: 20px; text-align: center; color: var(--text) !important;
    box-shadow: 0 2px 12px rgba(0,44,158,0.08);
}

/* ── BOTONES (todos los tipos) ── */
.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] > button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, var(--blue), var(--navy)) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 14px rgba(0,44,158,0.25) !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover,
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    background: linear-gradient(135deg, #1A45C8, var(--navy)) !important;
    color: #FFFFFF !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 22px rgba(0,44,158,0.35) !important;
}
/* Texto dentro del botón siempre blanco */
.stButton > button p,
.stDownloadButton > button p,
[data-testid="stFormSubmitButton"] > button p,
[data-testid="stBaseButton-secondary"] p,
[data-testid="stBaseButton-primary"] p {
    color: #FFFFFF !important;
}

/* ── ALERTS — texto siempre oscuro ── */
.stAlert { border-radius: 12px !important; }
.stAlert p,
.stAlert span,
.stAlert div,
[data-testid="stNotification"] p,
[data-testid="stNotification"] span,
[role="alert"] p,
[role="alert"] span {
    color: #1A2340 !important;
}

/* ── PRESENTACIÓN ── */
.pres-kpi-value {
    font-size: 4rem; font-weight: 900; color: var(--blue);
    text-align: center;
}
.pres-kpi-label { font-size: 1.1rem; color: var(--muted); text-align: center; }

/* ── ADMIN ── */
.admin-card {
    background: rgba(192,57,43,0.06); border: 1px solid rgba(192,57,43,0.2);
    border-radius: 12px; padding: 20px; margin-top: 16px;
}

/* Ocultar elementos de Streamlit */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }

/* Fondo de columnas y contenedores */
[data-testid="stVerticalBlock"] { gap: 12px; }
[data-testid="column"] { background: transparent !important; }

/* Sliders más limpios */
[data-testid="stSlider"] > div > div > div > div {
    background: var(--blue) !important;
}

/* Input en admin */
[data-testid="stTextInput"] input {
    background: var(--card) !important;
    color: var(--text) !important;
    border: 1.5px solid rgba(0,44,158,0.25) !important;
    border-radius: 8px !important;
}

/* Labels de inputs y widgets — siempre color oscuro */
[data-testid="stTextInput"] label,
[data-testid="stTextInput"] label p,
[data-testid="stTextInput"] label span,
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] span,
[data-testid="stToggle"] label p,
label[data-baseweb="label"] p,
.stTextInput label,
.stMarkdown p {
    color: var(--text) !important;
}

/* DataFrame */
[data-testid="stDataFrame"] { border-radius: 12px !important; overflow: hidden; }

/* ── EXPANDER — fondo claro siempre ── */
[data-testid="stExpander"],
[data-testid="stExpander"] details,
[data-testid="stExpander"] summary,
[data-testid="stExpander"] > details > summary,
[data-testid="stExpander"] > details[open],
[data-testid="stExpander"] > details[open] > div {
    background: var(--card) !important;
    color: var(--text) !important;
    border-color: rgba(0,44,158,0.15) !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary:hover {
    background: var(--bg2) !important;
}
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] details p,
[data-testid="stExpander"] details span {
    color: var(--text) !important;
}
</style>
""")


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def get_logo_b64():
    try:
        with open("unah_logo.png", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


def render_header():
    logo_b64 = get_logo_b64()
    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" style="height:90px;width:auto;max-width:80px;border-radius:6px;object-fit:contain;background:transparent;flex-shrink:0;filter:drop-shadow(0 2px 10px rgba(0,0,0,0.4));">'
        if logo_b64 else '<span style="font-size:3rem;">🎓</span>'
    )
    fecha = datetime.now().strftime("%d de %B, %Y")
    st.html(f"""
    <div style="background:linear-gradient(135deg,#051461 0%,#002C9E 60%,#3F888F 100%);border-bottom:3px solid #F9D003;padding:18px 32px;border-radius:0 0 18px 18px;margin-bottom:24px;display:flex;align-items:center;gap:20px;box-shadow:0 8px 32px rgba(0,44,158,0.5);">
        {logo_html}
        <div style="flex:1;">
            <h1 style="font-size:1.6rem;font-weight:800;color:#ffffff;margin:0;text-shadow:0 2px 8px rgba(0,0,0,0.4);font-family:Inter,sans-serif;">Día de la Sostenibilidad Universitaria</h1>
            <p style="color:#F9D003;margin:4px 0 0;font-size:0.85rem;font-weight:500;letter-spacing:0.05em;font-family:Inter,sans-serif;">UNIVERSIDAD NACIONAL AUTÓNOMA DE HONDURAS &nbsp;·&nbsp; Diferencial Semántico &nbsp;·&nbsp; {fecha}</p>
        </div>
        <div style="display:inline-flex;align-items:center;gap:6px;background:rgba(249,208,3,0.15);border:1px solid #F9D003;color:#F9D003;font-weight:700;font-size:0.8rem;padding:4px 14px;border-radius:99px;font-family:Inter,sans-serif;">
            <span style="width:8px;height:8px;background:#FF4444;border-radius:50%;display:inline-block;"></span>&nbsp;EN VIVO
        </div>
    </div>
    """)


def get_data():
    try:
        docs = db.collection(COLLECTION_NAME).stream()
        data = [doc.to_dict() for doc in docs]
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        cols_num = [c for c in df.columns if c != "timestamp"]
        df[cols_num] = df[cols_num].apply(pd.to_numeric, errors="coerce")
        return df
    except Exception as e:
        st.error(f"Error de conexión a Firebase: {e}")
        return pd.DataFrame()


def get_promedios(df):
    promedios = {}
    for left, right in PAIRS:
        key = f"{left}_{right}"
        if key in df.columns:
            promedios[key] = {"left": left, "right": right, "avg": df[key].mean()}
    return promedios


def color_bar(val):
    if val < 4:   return "#FF4444"
    elif val < 6: return "#FFA500"
    elif val < 8: return "#F9D003"
    else:         return "#44DD88"


def render_kpis(df, promedios):
    total      = len(df)
    global_avg = sum(v["avg"] for v in promedios.values()) / len(promedios) if promedios else 0
    cat_avgs   = {}
    for cat_name, pairs in CATEGORIAS.items():
        keys = [f"{l}_{r}" for l, r in pairs]
        vals = [promedios[k]["avg"] for k in keys if k in promedios and not pd.isna(promedios[k]["avg"])]
        cat_avgs[cat_name] = sum(vals) / len(vals) if vals else 0

    best_cat  = max(cat_avgs, key=cat_avgs.get)
    worst_cat = min(cat_avgs, key=cat_avgs.get)

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-icon">👥</div>
            <div class="kpi-value">{total}</div>
            <div class="kpi-label">Participantes</div>
            <div class="kpi-sub">Respuestas totales</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon">📊</div>
            <div class="kpi-value">{global_avg:.1f}</div>
            <div class="kpi-label">Promedio Global</div>
            <div class="kpi-sub">Escala 1–10</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon">🏆</div>
            <div class="kpi-value">{cat_avgs[best_cat]:.1f}</div>
            <div class="kpi-label">Mejor Categoría</div>
            <div class="kpi-sub">{best_cat}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon">⚠️</div>
            <div class="kpi-value">{cat_avgs[worst_cat]:.1f}</div>
            <div class="kpi-label">Cat. a Fortalecer</div>
            <div class="kpi-sub">{worst_cat}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def radar_chart(promedios):
    labels = [v["right"] for v in promedios.values()]
    values = [v["avg"]   for v in promedios.values()]
    labels.append(labels[0]); values.append(values[0])

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=labels, fill="toself",
        fillcolor="rgba(0,44,158,0.35)",
        line=dict(color="#F9D003", width=2.5),
        name="Promedio Colectivo",
        hovertemplate="<b>%{theta}</b><br>Promedio: %{r:.2f}<extra></extra>"
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[1, 10],
                            tickfont=dict(color="#6B7A99", size=10),
                            gridcolor="rgba(0,44,158,0.15)"),
            angularaxis=dict(tickfont=dict(color="#1A2340", size=11),
                             gridcolor="rgba(0,44,158,0.12)")
        ),
        showlegend=False, height=480,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=60, r=60, t=40, b=40),
        font=dict(family="Inter", color="#1A2340")
    )
    return fig


def bar_chart(promedios):
    labels = [f"{v['left']} ↔ {v['right']}" for v in promedios.values()]
    values = [v["avg"] for v in promedios.values()]
    colors = [color_bar(v) for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=colors),
        text=[f"{v:.2f}" for v in values], textposition="outside",
        textfont=dict(color="#1A2340", size=11),
        hovertemplate="<b>%{y}</b><br>Promedio: %{x:.2f}<extra></extra>"
    ))
    fig.add_vline(x=5, line_dash="dot", line_color="#D4A017", line_width=1.5)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(range=[0, 11], gridcolor="rgba(0,44,158,0.12)", color="#1A2340",
                   tickfont=dict(color="#6B7A99")),
        yaxis=dict(color="#1A2340", tickfont=dict(color="#1A2340", size=10)),
        height=480, margin=dict(l=10, r=70, t=10, b=10),
        font=dict(family="Inter", color="#1A2340")
    )
    return fig


def heatmap_chart(df, promedios):
    keys   = list(promedios.keys())
    labels = [f"{promedios[k]['left'][:10]}↔{promedios[k]['right'][:10]}" for k in keys]
    matrix = []
    for k in keys:
        row = [int((df[k] == i).sum()) if k in df.columns else 0 for i in range(1, 11)]
        matrix.append(row)

    fig = go.Figure(go.Heatmap(
        z=matrix, x=list(range(1, 11)), y=labels,
        colorscale=[
            [0,   "#EEF1F8"],
            [0.3, "rgba(0,44,158,0.35)"],
            [0.7, "rgba(212,160,23,0.75)"],
            [1,   "#002C9E"]
        ],
        showscale=True,
        hovertemplate="Par: %{y}<br>Valor: %{x}<br>Respuestas: %{z}<extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Valor en la escala", color="#1A2340",
                   tickfont=dict(color="#1A2340"), gridcolor="rgba(0,44,158,0.1)"),
        yaxis=dict(color="#1A2340", tickfont=dict(color="#1A2340", size=9)),
        height=480, margin=dict(l=10, r=10, t=10, b=40),
        font=dict(family="Inter", color="#1A2340")
    )
    return fig


def gauge_chart(value, title):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 12, "color": "#1A2340", "family": "Inter"}},
        number={"font": {"size": 24, "color": "#002C9E", "family": "Inter"}, "suffix": "/10"},
        gauge=dict(
            axis=dict(range=[1, 10], tickwidth=1, tickcolor="#1A2340",
                      tickfont=dict(color="#6B7A99")),
            bar=dict(color="#002C9E", thickness=0.3),
            bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,44,158,0.2)",
            steps=[
                dict(range=[1, 4], color="rgba(255,68,68,0.15)"),
                dict(range=[4, 7], color="rgba(255,165,0,0.15)"),
                dict(range=[7, 10], color="rgba(26,122,130,0.15)")
            ],
            threshold=dict(line=dict(color="#1A7A82", width=3), thickness=0.75, value=7)
        )
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", height=210,
        margin=dict(l=20, r=20, t=40, b=10),
        font=dict(family="Inter", color="#1A2340")
    )
    return fig


def df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Respuestas", index=False)
        if not df.empty:
            cols_num = [c for c in df.columns if c != "timestamp"]
            df[cols_num].describe().T.to_excel(writer, sheet_name="Estadísticas")
    output.seek(0)
    return output.getvalue()


# ============================================================
# RENDER HEADER
# ============================================================
render_header()

# ============================================================
# NAVEGACIÓN Y AUTO-REFRESCO GLOBAL
# ============================================================
if "show_admin" not in st.session_state:
    st.session_state["show_admin"] = False
if "auto_refresh" not in st.session_state:
    st.session_state["auto_refresh"] = True

_col_toggle, _col_space, _col_admin = st.columns([1, 3, 1])
with _col_toggle:
    st.session_state["auto_refresh"] = st.toggle(
        "🔄 Actualización automática",
        value=st.session_state["auto_refresh"],
        help="Desactívalo mientras llenas el formulario para que los sliders no se reinicien."
    )
with _col_admin:
    btn_label = "⬅️ Volver a Público" if st.session_state["show_admin"] else "🔐 Panel Admin"
    if st.button(btn_label, use_container_width=True):
        st.session_state["show_admin"] = not st.session_state["show_admin"]
        st.rerun()

if st.session_state["auto_refresh"] and not st.session_state["show_admin"]:
    st_autorefresh(interval=5000, limit=None, key="global_refresh")

if st.session_state["show_admin"]:
    st.StopException = st.script_runner.StopException if hasattr(st, "script_runner") else Exception
    # Hack to just let the code fall through to the admin section below
    pass

if not st.session_state["show_admin"]:
    # ============================================================
    # TABS PÚBLICOS
    # ============================================================
    tab1, tab2 = st.tabs([
        "📋 Formulario",
        "📽️ Modo Presentación"
    ])


# ============================================================
# PESTAÑA 1 — FORMULARIO
# ============================================================
if not st.session_state["show_admin"]:
    with tab1:
        st.markdown("""
    <div class="instrucciones-box">
        <b>📌 Instrucciones:</b><br><br>
        Mediante este instrumento se explora la percepción y actitudes que tiene la comunidad universitaria sobre
        la <b>formación en sostenibilidad</b>.<br><br>
        Se presentan pares de adjetivos:
        <span style="color:#C0392B;font-weight:700;">negativos a la izquierda</span> y
        <span style="color:#1A7A82;font-weight:700;">positivos a la derecha</span>.
        La escala es de <b>1 a 10</b>.<br><br>
        Su participación es <b>completamente anónima</b>. Deslice el marcador al número que mejor represente su opinión.
    </div>
    """, unsafe_allow_html=True)

    with st.form("semantic_form", clear_on_submit=True):
        respuestas = {}
        answered = 0

        for cat_name, pares_cat in CATEGORIAS.items():
            st.markdown(f'<div class="cat-header">📂 {cat_name}</div>', unsafe_allow_html=True)

            for left_word, right_word in pares_cat:
                col1, col2, col3 = st.columns([2.5, 5, 2.5])
                with col1:
                    st.markdown(f"<div class='word-left'>{left_word}</div>", unsafe_allow_html=True)
                with col2:
                    key_name = f"{left_word}_{right_word}"
                    val = st.slider("", min_value=1, max_value=10, value=5,
                                    key=key_name, label_visibility="collapsed")
                    respuestas[key_name] = val
                    if val != 5:
                        answered += 1
                with col3:
                    st.markdown(f"<div class='word-right'>{right_word}</div>", unsafe_allow_html=True)

        pct = int((answered / TOTAL_PAIRS) * 100)
        st.markdown(f"""
        <div class="prog-label">{answered}/{TOTAL_PAIRS} pares respondidos &nbsp;·&nbsp; {pct}%</div>
        <div class="prog-wrapper"><div class="prog-fill" style="width:{pct}%"></div></div>
        """, unsafe_allow_html=True)

        st.write("")
        submitted = st.form_submit_button("✅ Enviar mis Respuestas", use_container_width=True)

        if submitted:
            respuestas["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.collection(COLLECTION_NAME).add(respuestas)
            st.success("🎉 ¡Respuestas enviadas exitosamente! Muchas gracias por su participación.")
            st.balloons()



# ============================================================
# PESTAÑA 2 — MODO PRESENTACIÓN
# ============================================================
if not st.session_state["show_admin"]:
    with tab2:
        st.markdown('<div class="section-title">📊 Dashboard en Vivo</div>', unsafe_allow_html=True)

        st.markdown("""
        <div style="text-align:center; margin-bottom:20px;">
            <span style="display:inline-flex;align-items:center;gap:6px;background:#002C9E;color:#ffffff;font-weight:700;font-size:0.82rem;padding:6px 18px;border-radius:99px;font-family:Inter,sans-serif;letter-spacing:0.05em;"><span style="width:8px;height:8px;background:#FF4444;border-radius:50%;display:inline-block;"></span>&nbsp;TRANSMISIÓN EN VIVO &nbsp;·&nbsp; Auto-actualiza cada 5s</span>
        </div>
        """, unsafe_allow_html=True)

        df_p   = get_data()
        prom_p = get_promedios(df_p) if not df_p.empty else {}

        if not df_p.empty and prom_p:
            # ── KPIs siempre en la parte superior ──────────────────────
            render_kpis(df_p, prom_p)

            st.write("")

            col_rp, col_bp, col_qrp = st.columns([2, 2, 1])
            with col_rp:
                st.markdown('<div class="section-title">🕸️ Perfil de Percepción Colectiva</div>', unsafe_allow_html=True)
                fig_r = radar_chart(prom_p)
                fig_r.update_layout(height=540)
                st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar": False})

            with col_bp:
                st.markdown('<div class="section-title">📊 Promedios por Par Semántico</div>', unsafe_allow_html=True)
                fig_b = bar_chart(prom_p)
                fig_b.update_layout(height=540)
                st.plotly_chart(fig_b, use_container_width=True, config={"displayModeBar": False})

            with col_qrp:
                st.markdown('<div class="section-title">📱 Participa aquí</div>', unsafe_allow_html=True)
                st.markdown('<div class="qr-container">', unsafe_allow_html=True)
                url_pres = st.text_input("URL:", value="https://diferencial-docente.streamlit.app", key="qr_url_pres")
                if url_pres:
                    qr_p = qrcode.QRCode(version=1, box_size=10, border=2)
                    qr_p.add_data(url_pres)
                    qr_p.make(fit=True)
                    img_qrp = qr_p.make_image(fill_color="#002C9E", back_color="white")
                    buf_p = BytesIO()
                    img_qrp.save(buf_p, format="PNG")
                    st.image(buf_p, use_container_width=True)
                st.markdown("""
                <div style="font-size:0.78rem;color:#6B7A99;text-align:center;margin-top:8px;">Escanea y
                completa el diferencial semántico</div>""", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        else:
            col_wait, col_qr_wait = st.columns([3, 1])
            with col_wait:
                st.markdown("""
                <div style="text-align:center;padding:80px 20px;">
                    <div style="font-size:6rem">📡</div>
                    <h1 style="font-size:3rem;color:#002C9E">Esperando participantes...</h1>
                    <p style="font-size:1.3rem;color:#6B7A99">Las visualizaciones aparecerán automáticamente.</p>
                </div>
                """, unsafe_allow_html=True)
            with col_qr_wait:
                st.markdown('<div class="section-title" style="margin-top:60px;">📱 Participa aquí</div>', unsafe_allow_html=True)
                st.markdown('<div class="qr-container">', unsafe_allow_html=True)
                url_wait = st.text_input("URL:", value="https://diferencial-docente.streamlit.app", key="qr_url_wait")
                if url_wait:
                    qr_w = qrcode.QRCode(version=1, box_size=10, border=2)
                    qr_w.add_data(url_wait)
                    qr_w.make(fit=True)
                    img_qrw = qr_w.make_image(fill_color="#002C9E", back_color="white")
                    buf_w = BytesIO()
                    img_qrw.save(buf_w, format="PNG")
                    st.image(buf_w, use_container_width=True)
                st.markdown("""
                <div style="font-size:0.78rem;color:#6B7A99;text-align:center;margin-top:8px;">Escanea y
                completa el diferencial semántico</div>""", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# PESTAÑA 3 — PANEL ADMIN
# ============================================================
if st.session_state.get("show_admin", False):
    st.markdown('<div class="section-title">🔐 Acceso Restringido — Panel de Administrador</div>', unsafe_allow_html=True)

    if "admin_auth" not in st.session_state:
        st.session_state["admin_auth"] = False

    if not st.session_state["admin_auth"]:
        col_login, _, _ = st.columns([1, 1, 1])
        with col_login:
            pwd = st.text_input("Contraseña de administrador:", type="password", key="admin_pwd_input")
            if st.button("Ingresar", use_container_width=True):
                if pwd == ADMIN_PASS:
                    st.session_state["admin_auth"] = True
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta.")
    else:
        st.success("✅ Sesión de administrador activa.")

        # ── DASHBOARD EN VIVO (dentro del admin) ──────────────────
        df_dash = get_data()
        promedios = get_promedios(df_dash) if not df_dash.empty else {}

        if not df_dash.empty and promedios:
            render_kpis(df_dash, promedios)

            # Gauges por categoría
            st.markdown('<div class="section-title">🎯 Percepción por Categoría</div>', unsafe_allow_html=True)
            gauge_cols = st.columns(4)
            for idx, (cat_name, pairs) in enumerate(CATEGORIAS.items()):
                keys = [f"{l}_{r}" for l, r in pairs]
                vals = [promedios[k]["avg"] for k in keys if k in promedios and not pd.isna(promedios[k]["avg"])]
                cat_avg = sum(vals) / len(vals) if vals else 0
                with gauge_cols[idx]:
                    short_name = cat_name.replace(" y ", "/").replace(" ético", "")
                    st.plotly_chart(gauge_chart(cat_avg, short_name[:20]),
                                    use_container_width=True, config={"displayModeBar": False})

            # Radar + Barras
            col_radar, col_bar = st.columns(2)
            with col_radar:
                st.markdown('<div class="section-card"><div class="section-title">🕸️ Perfil de Percepción (Radar)</div>', unsafe_allow_html=True)
                st.plotly_chart(radar_chart(promedios), use_container_width=True, config={"displayModeBar": False})
                st.markdown("</div>", unsafe_allow_html=True)
            with col_bar:
                st.markdown('<div class="section-card"><div class="section-title">📊 Promedios por Par Semántico</div>', unsafe_allow_html=True)
                st.plotly_chart(bar_chart(promedios), use_container_width=True, config={"displayModeBar": False})
                st.markdown("</div>", unsafe_allow_html=True)

            # Heatmap
            st.markdown('<div class="section-card"><div class="section-title">🔥 Mapa de Calor — Distribución de Respuestas</div>', unsafe_allow_html=True)
            st.plotly_chart(heatmap_chart(df_dash, promedios), use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

            # Exportación
            st.markdown('<div class="section-card"><div class="section-title">📥 Exportar Datos</div>', unsafe_allow_html=True)
            excel_data = df_to_excel(df_dash)
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    label="⬇️ Descargar Excel — Respuestas completas",
                    data=excel_data,
                    file_name=f"sostenibilidad_UNAH_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with col_dl2:
                cols_num_dash = [c for c in df_dash.columns if c != "timestamp"]
                summary_df = df_dash[cols_num_dash].describe().T.reset_index()
                csv = summary_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇️ Descargar Resumen Estadístico (CSV)",
                    data=csv,
                    file_name=f"resumen_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center; padding:40px 20px;">
                <div style="font-size:3rem">⏳</div>
                <h3 style="color:#002C9E">Esperando las primeras respuestas...</h3>
                <p style="color:#6B7A99">El dashboard se actualizará automáticamente cada 5 segundos.</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="section-title">🗄️ Gestión de Datos</div>', unsafe_allow_html=True)

        df_admin = get_data()

        if df_admin.empty:
            st.info("No hay respuestas registradas aún.")
        else:
            st.markdown(f"**Total de respuestas:** `{len(df_admin)}`")

            with st.expander("📋 Ver todas las respuestas individuales"):
                display_df = df_admin.copy()
                if "timestamp" in display_df.columns:
                    display_df = display_df[["timestamp"] + [c for c in display_df.columns if c != "timestamp"]]
                st.dataframe(display_df, use_container_width=True, height=350)

            excel_admin = df_to_excel(df_admin)
            st.download_button(
                "⬇️ Descargar Excel completo",
                data=excel_admin,
                file_name=f"admin_export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            st.markdown('<div class="admin-card">', unsafe_allow_html=True)
            st.markdown("### ⚠️ Zona de Peligro")
            st.warning("Esta acción **eliminará permanentemente** todas las respuestas de Firebase.")
            confirm = st.text_input("Escribe **ELIMINAR** para confirmar:", key="confirm_delete")
            if st.button("🗑️ Borrar TODAS las respuestas", use_container_width=True):
                if confirm == "ELIMINAR":
                    docs = db.collection(COLLECTION_NAME).stream()
                    deleted = 0
                    for doc in docs:
                        doc.reference.delete()
                        deleted += 1
                    st.success(f"✅ Se eliminaron {deleted} respuestas correctamente.")
                    st.rerun()
                else:
                    st.error("Escribe exactamente ELIMINAR para confirmar.")
            st.markdown("</div>", unsafe_allow_html=True)

        if st.button("🚪 Cerrar sesión"):
            st.session_state["admin_auth"] = False
            st.rerun()
