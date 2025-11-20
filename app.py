import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO
from datetime import datetime
from scipy.stats import poisson, norm

# ==============================================================================
# 1. CONFIGURACIÓN Y ESTÉTICA (CYBERPUNK PRO)
# ==============================================================================
st.set_page_config(page_title="PL GOD MODE V3", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main {background-color: #050505; color: #e0e0e0;}
    h1, h2, h3 {color: #00ff9d; font-family: 'Courier New', monospace; text-transform: uppercase; letter-spacing: 2px;}
    .value-box {background-color: #064e3b; border: 1px solid #34d399; padding: 15px; border-radius: 8px; color: #d1fae5;}
    .no-value-box {background-color: #450a0a; border: 1px solid #f87171; padding: 15px; border-radius: 8px; color: #fecaca;}
    .metric-card {background-color: #111; border: 1px solid #333; padding: 15px; border-radius: 8px; text-align: center;}
    .big-num {font-size: 24px; font-weight: bold; color: #fff;}
    .sub-text {font-size: 12px; color: #888;}
    </style>
    """, unsafe_allow_html=True)

st.title("🧬 PREMIER LEAGUE: GOD MODE V3")
st.markdown("**Engine:** Poisson Hybrid + Game State Simulation + Fair Odds Calc")

# ==============================================================================
# 2. MOTOR DE DATOS (DATA ENGINE)
# ==============================================================================
@st.cache_data(ttl=3600)
def load_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    urls = [
        "https://www.football-data.co.uk/mmz4281/2425/E0.csv", # PL Actual
        "https://www.football-data.co.uk/mmz4281/2425/E1.csv", # Championship
        "https://www.football-data.co.uk/mmz4281/2324/E0.csv"  # PL Anterior (Contexto)
    ]
    frames = []
    for u in urls:
        try:
            r = requests.get(u, headers=headers)
            if r.ok:
                df = pd.read_csv(StringIO(r.text))
                # Limpieza de columnas críticas
                cols = ['Date', 'HomeTeam', 'AwayTeam', 'Referee', 'FTHG', 'FTAG', 
                        'HS', 'AS', 'HST', 'AST', 'HC', 'AC', 'HF', 'AF', 'HY', 'AY', 'HR', 'AR']
                valid = [c for c in cols if c in df.columns]
                df = df[valid].dropna()
                df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
                frames.append(df)
        except: continue
    
    if not frames: return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values('Date')

df_master = load_data()

@st.cache_data(ttl=3600)
def load_fixtures():
    try:
        bootstrap = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/").json()
        teams = {t['id']: t['name'] for t in bootstrap['teams']}
        fixtures = requests.get("https://fantasy.premierleague.com/api/fixtures/").json()
        future = []
        for f in fixtures:
            if not f['finished'] and f['event']:
                future.append({
                    "Date": f['kickoff_time'][:10],
                    "Home": teams.get(f['team_h'], "Unknown"),
                    "Away": teams.get(f['team_a'], "Unknown")
                })
        return pd.DataFrame(future).head(20)
    except: return pd.DataFrame()

df_fix = load_fixtures()

# ==============================================================================
# 3. BASES DE DATOS TÁCTICAS (MANUAL OVERRIDE)
# ==============================================================================

# ADN Táctico extendido con "Aerial Threat" (Juego Aéreo)
# width: 0-10 (Uso de bandas), aggression: 0-10, panic: 0-10, aerial: 0-10
tactical_dna = {
    "Man City": {"style": "Possession", "w": 7, "panic": 1, "agg": 9, "aerial": 4},
    "Arsenal": {"style": "Pressure", "w": 8, "panic": 2, "agg": 9, "aerial": 8},
    "Liverpool": {"style": "Direct", "w": 9, "panic": 3, "agg": 10, "aerial": 7},
    "Everton": {"style": "Physical", "w": 4, "panic": 8, "agg": 6, "aerial": 10}, # Everton busca corners por altura
    "Brentford": {"style": "SetPiece", "w": 6, "panic": 6, "agg": 7, "aerial": 9},
    "West Ham": {"style": "Counter", "w": 5, "panic": 7, "agg": 6, "aerial": 9},
    "Aston Villa": {"style": "HighLine", "w": 7, "panic": 4, "agg": 8, "aerial": 6},
    "Tottenham": {"style": "Chaos", "w": 7, "panic": 5, "agg": 9, "aerial": 6},
    "Newcastle": {"style": "Physical", "w": 8, "panic": 4, "agg": 8, "aerial": 8},
    "Man Utd": {"style": "Transition", "w": 6, "panic": 6, "agg": 7, "aerial": 5},
    "Chelsea": {"style": "Chaos", "w": 7, "panic": 5, "agg": 8, "aerial": 5},
    "Brighton": {"style": "BuildUp", "w": 8, "panic": 3, "agg": 6, "aerial": 5},
    "Wolves": {"style": "Counter", "w": 7, "panic": 5, "agg": 6, "aerial": 4},
    "Fulham": {"style": "Balanced", "w": 6, "panic": 5, "agg": 6, "aerial": 6},
    "Bournemouth": {"style": "Pressure", "w": 7, "panic": 5, "agg": 7, "aerial": 6},
    "Crystal Palace": {"style": "LowBlock", "w": 5, "panic": 6, "agg": 5, "aerial": 7},
    "Nott'm Forest": {"style": "Counter", "w": 7, "panic": 7, "agg": 6, "aerial": 7},
    "Luton": {"style": "LongBall", "w": 4, "panic": 9, "agg": 5, "aerial": 9},
    "Burnley": {"style": "Weak", "w": 5, "panic": 7, "agg": 5, "aerial": 4},
    "Sheffield United": {"style": "LowBlock", "w": 3, "panic": 9, "agg": 4, "aerial": 6},
    "Leicester": {"style": "Possession", "w": 6, "panic": 5, "agg": 7, "aerial": 5},
    "Southampton": {"style": "Possession", "w": 5, "panic": 6, "agg": 6, "aerial": 4},
    "Ipswich": {"style": "Direct", "w": 6, "panic": 7, "agg": 6, "aerial": 6}
}

# Coordenadas GPS para Clima
stadiums = {
    "Arsenal": (51.55, -0.10), "Man City": (53.48, -2.20), "Liverpool": (53.43, -2.96),
    "Newcastle": (54.97, -1.62), "Man Utd": (53.46, -2.29), "Aston Villa": (52.50, -1.88),
    "Everton": (53.43, -2.96), "Chelsea": (51.48, -0.19), "Tottenham": (51.60, -0.06)
}

# ==============================================================================
# 4. MOTORES DE CÁLCULO (THE BRAINS)
# ==============================================================================

def get_advanced_stats(team, df, n=6):
    """Calcula forma reciente, volatilidad y métricas sintéticas"""
    # Filtrar últimos N partidos
    matches = df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)].sort_values('Date').tail(n)
    if matches.empty: return None
    
    # Lógica para extraer stats correctas (si jugó de local o visita)
    corners, shots, goals, cards, fouls = [], [], [], [], []
    
    for _, row in matches.iterrows():
        if row['HomeTeam'] == team:
            corners.append(row['HC']); shots.append(row['HS']); goals.append(row['FTHG']); cards.append(row['HY']); fouls.append(row['HF'])
        else:
            corners.append(row['AC']); shots.append(row['AS']); goals.append(row['FTAG']); cards.append(row['AY']); fouls.append(row['AF'])
            
    # Volatilidad (Desviación Estándar): ¿Es un equipo predecible?
    volatility = np.std(corners) 
    
    return {
        "avg_corn": np.mean(corners),
        "avg_foul": np.mean(fouls),
        "avg_card": np.mean(cards),
        "volatility": volatility,
        "momentum": np.mean(goals) # Goles recientes como proxy de estado de forma
    }

def get_weather(team):
    coords = stadiums.get(team, (51.5, -0.1)) # Default London
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords[0]}&longitude={coords[1]}&current=rain,wind_speed_10m"
        d = requests.get(url).json()['current']
        return d['rain'], d['wind_speed_10m']
    except: return 0.0, 10.0

def calculate_fair_odds(prob_percentage):
    """Convierte probabilidad en Cuota Decimal (Fair Value)"""
    if prob_percentage <= 0: return 999.0
    return round(100 / prob_percentage, 2)

# ==============================================================================
# 5. INTERFAZ DE CONTROL
# ==============================================================================

# Normalizador de nombres
name_map = {
    "Man Utd": "Man United", "Nott'm Forest": "Nott'm Forest", "Sheffield Utd": "Sheffield United",
    "Luton": "Luton", "Spurs": "Tottenham", "Man City": "Man City", "Wolves": "Wolves"
}
def normalize(n): return name_map.get(n, n)

# Sidebar: Simulación de Escenario
st.sidebar.header("🎮 SIMULADOR DE ESCENARIO")
st.sidebar.write("¿Qué pasa si el partido cambia?")
sim_minute = st.sidebar.slider("Minuto del Partido", 0, 90, 0)
sim_score_diff = st.sidebar.selectbox("Marcador (Desde el pto de vista Local)", ["Empate", "Local Gana por 1", "Local Gana por 2+", "Visita Gana por 1", "Visita Gana por 2+"])

# Selección de Partido
if df_fix.empty:
    st.warning("⚠️ Modo Manual Activado")
    teams_list = sorted(list(tactical_dna.keys()))
    c1, c2 = st.columns(2)
    home = c1.selectbox("Local", teams_list)
    away = c2.selectbox("Visita", teams_list)
else:
    opts = [f"{r['Date']} | {r['Home']} vs {r['Away']}" for i, r in df_fix.iterrows()]
    sel = st.selectbox("📅 PRÓXIMOS PARTIDOS", range(len(opts)), format_func=lambda x: opts[x])
    row = df_fix.iloc[sel]
    home, away = normalize(row['Home']), normalize(row['Away'])

# ==============================================================================
# 6. EL NÚCLEO DE PREDICCIÓN (CORE ENGINE)
# ==============================================================================

# 1. Carga de Datos
stats_h = get_advanced_stats(home, df_master)
stats_a = get_advanced_stats(away, df_master)
rain, wind = get_weather(home)

# Default values if stats missing
if not stats_h: stats_h = {"avg_corn": 5.0, "avg_foul": 10.0, "avg_card": 1.5, "volatility": 1.5, "momentum": 1.0}
if not stats_a: stats_a = {"avg_corn": 4.5, "avg_foul": 10.5, "avg_card": 1.8, "volatility": 1.5, "momentum": 0.8}

dna_h = tactical_dna.get(home, {"w": 5, "panic": 5, "aerial": 5})
dna_a = tactical_dna.get(away, {"w": 5, "panic": 5, "aerial": 5})

# 2. CÁLCULO DE CÓRNERS (Con Ajuste de Game State)
base_corners = (stats_h['avg_corn'] + stats_a['avg_corn']) / 2 + 1.0

# Factor Táctico (Mismatch)
tactical_boost = 0
# Local Ancho vs Visita Pánico
if dna_h['w'] > 7 and dna_a['panic'] > 6: tactical_boost += 1.0 
# Visita Ancho vs Local Pánico
if dna_a['w'] > 7 and dna_h['panic'] > 6: tactical_boost += 1.0
# Duelo Aéreo (Equipos altos buscan balón parado)
if dna_h['aerial'] > 8 or dna_a['aerial'] > 8: tactical_boost += 0.8

# Factor Clima
weather_boost = 0
if rain > 1.0: weather_boost += 0.8 # Despejes por lluvia
if wind > 25.0: weather_boost -= 1.2 # Dificultad para centrar

# Factor Game State (Simulación)
state_boost = 0
if sim_minute > 15:
    # Si hay empate, el ritmo suele mantenerse
    if sim_score_diff == "Empate": state_boost += 0
    # Si el favorito pierde, ataca a muerte (Corners UP)
    elif sim_score_diff == "Visita Gana por 1" and dna_h['agg'] > 7: state_boost += 2.5
    elif sim_score_diff == "Local Gana por 2+": state_boost -= 1.5 (Partido muerto)

final_corners = base_corners + tactical_boost + weather_boost + state_boost

# 3. CÁLCULO DE TARJETAS
base_cards = (stats_h['avg_card'] + stats_a['avg_card']) / 2 + 1.5 # +Base arbitral
# Ajuste por Fricción
friction = (stats_h['avg_foul'] + stats_a['avg_foul']) / 22 # Ratio faltas
final_cards = base_cards * friction

# 4. CÁLCULO DE ODDS JUSTAS (VALUE ENGINE)
prob_over_9 = (poisson.rvs(final_corners, size=10000) > 9.5).mean() * 100
prob_over_10 = (poisson.rvs(final_corners, size=10000) > 10.5).mean() * 100
fair_odd_9 = calculate_fair_odds(prob_over_9)
fair_odd_10 = calculate_fair_odds(prob_over_10)

prob_card_4 = (poisson.rvs(final_cards, size=10000) > 4.5).mean() * 100
fair_odd_card = calculate_fair_odds(prob_card_4)

# ==============================================================================
# 7. DASHBOARD DE RESULTADOS
# ==============================================================================

st.divider()
c_main1, c_main2 = st.columns([3, 1])
with c_main1:
    st.subheader(f"{home} vs {away}")
    if sim_score_diff != "Empate": st.caption(f"🔮 SIMULANDO ESCENARIO: {sim_score_diff} (Min {sim_minute})")
with c_main2:
    st.metric("Lluvia", f"{rain}mm", delta="Rápida" if rain>0 else "Seca")

# --- TARJETAS DE ODDS (VALUE DETECTOR) ---
st.write("### 💰 CALCULADORA DE VALOR (FAIR ODDS)")
col_val1, col_val2, col_val3 = st.columns(3)

with col_val1:
    st.markdown(f"""
    <div class="metric-card">
    <div class="sub-text">Córners Over 9.5</div>
    <div class="big-num">{fair_odd_9}</div>
    <div class="sub-text">Prob: {prob_over_9:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)
    
with col_val2:
    st.markdown(f"""
    <div class="metric-card">
    <div class="sub-text">Córners Over 10.5</div>
    <div class="big-num">{fair_odd_10}</div>
    <div class="sub-text">Prob: {prob_over_10:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col_val3:
    st.markdown(f"""
    <div class="metric-card">
    <div class="sub-text">Tarjetas Over 4.5</div>
    <div class="big-num">{fair_odd_card}</div>
    <div class="sub-text">Prob: {prob_card_4:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

st.info("💡 **Cómo usar:** Mira la cuota en tu casa de apuestas. Si es MAYOR que la 'Fair Odd' mostrada arriba, tienes una Apuesta de Valor (Value Bet).")

# --- ANÁLISIS PROFUNDO ---
tab1, tab2 = st.tabs(["📊 ESTADÍSTICAS", "🧠 EL RAZONAMIENTO"])

with tab1:
    k1, k2 = st.columns(2)
    k1.metric("Proyección Córners", f"{final_corners:.2f}")
    k2.metric("Proyección Tarjetas", f"{final_cards:.2f}")
    
    st.write("#### Volatilidad del Partido")
    vol_avg = (stats_h['volatility'] + stats_a['volatility']) / 2
    st.progress(min(int(vol_avg * 20), 100))
    if vol_avg > 3.0: st.caption("⚠️ Partido Caótico (Alta varianza en stats recientes)")
    else: st.caption("🛡️ Partido Estable (Equipos predecibles)")

with tab2:
    st.write("#### 🕵️ ¿Por qué estos números?")
    
    # Narrativa Automática
    reasons = []
    
    # 1. Táctica
    if dna_h['w'] > 7: reasons.append(f"• **{home}** usa extremos muy abiertos (Width {dna_h['w']}/10), forzando córners.")
    if dna_a['panic'] > 6: reasons.append(f"• **{away}** sufre en defensa (Pánico {dna_a['panic']}/10), concediendo balón parado.")
    if dna_h['aerial'] > 8: reasons.append(f"• **{home}** es una Amenaza Aérea ({dna_h['aerial']}/10). Buscarán córners deliberadamente.")
    
    # 2. Clima
    if rain > 2.0: reasons.append(f"• **Lluvia intensa ({rain}mm):** El balón resbala, los porteros rechazan más y las defensas no se complican.")
    
    # 3. Game State
    if state_boost > 1.0: reasons.append(f"• **Escenario Simulado:** Al ir perdiendo, el equipo local entra en 'Modo Asedio', disparando la proyección.")
    elif state_boost < -1.0: reasons.append(f"• **Escenario Simulado:** Con ventaja amplia, el ritmo del partido decae.")
    
    if not reasons: st.write("• Partido equilibrado sin anomalías estadísticas graves.")
    else: 
        for r in reasons: st.write(r)

st.caption("System ID: GOD_MODE_V3 | Data: FPL + FootballData | Engine: Poisson")
