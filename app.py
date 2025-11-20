import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="PL Betting Sniper Auto", layout="wide")

st.markdown("""
    <style>
    .main {background-color: #09090b;}
    h1, h2, h3 {color: #e2e8f0;}
    .metric-card {background-color: #18181b; border: 1px solid #27272a; padding: 15px; border-radius: 10px;}
    .bet-box {background-color: #14532d; color: #dcfce7; padding: 15px; border-radius: 8px; border-left: 5px solid #4ade80;}
    .warn-box {background-color: #450a0a; color: #fee2e2; padding: 15px; border-radius: 8px; border-left: 5px solid #f87171;}
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 PL Sniper: Análisis 100% Automático")

# --- 1. MOTOR DE DATOS (PREMIER + CHAMPIONSHIP) ---
@st.cache_data(ttl=3600)
def load_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    urls = [
        "https://www.football-data.co.uk/mmz4281/2425/E0.csv", # PL
        "https://www.football-data.co.uk/mmz4281/2425/E1.csv"  # Champ
    ]
    frames = []
    for u in urls:
        try:
            r = requests.get(u, headers=headers)
            if r.ok:
                df = pd.read_csv(StringIO(r.text))
                cols = ['Date', 'HomeTeam', 'AwayTeam', 'Referee', 'HC', 'AC', 'HF', 'AF', 'HY', 'AY', 'HR', 'AR', 'FTHG', 'FTAG']
                valid = [c for c in cols if c in df.columns]
                frames.append(df[valid].dropna())
        except: continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

df_data = load_data()

# --- 2. CALENDARIO OFICIAL (FPL API) ---
@st.cache_data(ttl=3600)
def load_fixtures():
    try:
        r_teams = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/")
        teams = r_teams.json()['teams']
        id_map = {t['id']: t['name'] for t in teams}
        
        r_fix = requests.get("https://fantasy.premierleague.com/api/fixtures/")
        fixtures = r_fix.json()
        
        future = []
        for f in fixtures:
            if not f['finished'] and f['event']:
                future.append({
                    "Date": f['kickoff_time'][:10],
                    "Home": id_map.get(f['team_h'], "Unknown"),
                    "Away": id_map.get(f['team_a'], "Unknown")
                })
        return pd.DataFrame(future).head(20)
    except: return pd.DataFrame()

df_fix = load_fixtures()

# --- 3. INTELIGENCIA AUTOMÁTICA (CONTEXTO) ---

# A. Coordenadas Estadios (Para el Clima)
stadium_coords = {
    "Arsenal": (51.55, -0.10), "Aston Villa": (52.50, -1.88),
    "Bournemouth": (50.73, -1.83), "Brentford": (51.49, -0.28),
    "Brighton": (50.86, -0.08), "Burnley": (53.78, -2.23),
    "Chelsea": (51.48, -0.19), "Crystal Palace": (51.39, -0.08),
    "Everton": (53.43, -2.96), "Fulham": (51.47, -0.22),
    "Liverpool": (53.43, -2.96), "Luton": (51.88, -0.42),
    "Man City": (53.48, -2.20), "Man Utd": (53.46, -2.29),
    "Newcastle": (54.97, -1.62), "Nott'm Forest": (52.94, -1.13),
    "Sheffield Utd": (53.37, -1.47), "Tottenham": (51.60, -0.06),
    "West Ham": (51.53, 0.01), "Wolves": (52.59, -2.13),
    "Leicester": (52.62, -1.14), "Leeds": (53.77, -1.57),
    "Southampton": (50.90, -1.39), "Ipswich": (52.05, 1.14)
}

# B. Base de Datos de Rivalidades (Para la Intensidad)
derbies = [
    {"Man Utd", "Liverpool"}, {"Arsenal", "Tottenham"}, {"Everton", "Liverpool"},
    {"Man City", "Man Utd"}, {"Chelsea", "Tottenham"}, {"Arsenal", "Chelsea"},
    {"Brighton", "Crystal Palace"}, {"Aston Villa", "Wolves"}, {"Newcastle", "Sunderland"},
    {"Leeds", "Man Utd"}, {"Millwall", "West Ham"}
]

def get_auto_context(home_team, away_team, match_date):
    context = {"rain": False, "wind": False, "derby": False, "temp": 15}
    
    # 1. Detectar Clima (API Open-Meteo)
    coords = stadium_coords.get(home_team, (51.5, -0.1)) # Default London
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords[0]}&longitude={coords[1]}&daily=precipitation_sum,wind_speed_10m_max&forecast_days=3"
        w = requests.get(url).json()
        if 'daily' in w:
            rain = w['daily']['precipitation_sum'][0]
            wind = w['daily']['wind_speed_10m_max'][0]
            if rain > 2.0: context['rain'] = True
            if wind > 25.0: context['wind'] = True
    except: pass
    
    # 2. Detectar Derbi
    match_set = {home_team, away_team}
    for d in derbies:
        if d.issubset(match_set):
            context['derby'] = True
            break
            
    return context

# --- 4. MOTOR TÁCTICO AVANZADO ---
tactical_dna = {
    "Man City": {"style": "Possession", "w": 8, "agg": 9},
    "Arsenal": {"style": "Pressure", "w": 9, "agg": 9},
    "Liverpool": {"style": "Direct", "w": 10, "agg": 10},
    "Tottenham": {"style": "Chaos", "w": 8, "agg": 9},
    "Aston Villa": {"style": "HighLine", "w": 7, "agg": 8},
    "Newcastle": {"style": "Physical", "w": 8, "agg": 8},
    "Man Utd": {"style": "Counter", "w": 6, "agg": 7},
    "Chelsea": {"style": "Possession", "w": 7, "agg": 7},
    "Brighton": {"style": "BuildUp", "w": 7, "agg": 6},
    "West Ham": {"style": "SetPiece", "w": 5, "agg": 6},
    "Burnley": {"style": "Possession", "w": 5, "agg": 5},
    "Luton": {"style": "Direct", "w": 4, "agg": 6},
    "Sheffield Utd": {"style": "LowBlock", "w": 3, "agg": 4},
    "Everton": {"style": "Physical", "w": 4, "agg": 6},
    "Brentford": {"style": "Direct", "w": 6, "agg": 7},
    "Nott'm Forest": {"style": "Counter", "w": 7, "agg": 6},
    "Crystal Palace": {"style": "LowBlock", "w": 5, "agg": 5},
    "Wolves": {"style": "Counter", "w": 7, "agg": 6},
    "Fulham": {"style": "Balanced", "w": 6, "agg": 6},
    "Bournemouth": {"style": "Pressure", "w": 7, "agg": 8},
    "Leicester": {"style": "Possession", "w": 7, "agg": 7},
    "Ipswich": {"style": "Direct", "w": 6, "agg": 7},
    "Leeds": {"style": "Chaos", "w": 8, "agg": 9},
    "Southampton": {"style": "Possession", "w": 6, "agg": 6}
}

# --- 5. INTERFAZ ---
if df_fix.empty:
    st.warning("Modo Manual")
    teams = sorted(list(tactical_dna.keys()))
    c1, c2 = st.columns(2)
    home = c1.selectbox("Local", teams)
    away = c2.selectbox("Visita", teams)
    date_match = datetime.today().strftime('%Y-%m-%d')
else:
    opts = [f"{r['Date']} | {r['Home']} vs {r['Away']}" for i, r in df_fix.iterrows()]
    sel = st.selectbox("📅 Selecciona Partido", range(len(opts)), format_func=lambda x: opts[x])
    row = df_fix.iloc[sel]
    home, away, date_match = row['Home'], row['Away'], row['Date']

# --- 6. ANÁLISIS "SNIPER" ---
ctx = get_auto_context(home, away, date_match)

# A. Stats Históricas (Forma)
def get_form(team, df):
    # Últimos 5 partidos
    matches = df[(df['HomeTeam'].str.contains(team, na=False)) | (df['AwayTeam'].str.contains(team, na=False))].tail(5)
    if matches.empty: return 5, 10, 2 # Default corners, fouls, goals
    
    c_avg = (matches['HC'].mean() + matches['AC'].mean()) / 2
    f_avg = (matches['HF'].mean() + matches['AF'].mean()) / 2
    g_avg = (matches['FTHG'].mean() + matches['FTAG'].mean()) / 2
    return c_avg, f_avg, g_avg

h_corn, h_foul, h_goals = get_form(home, df_data)
a_corn, a_foul, a_goals = get_form(away, df_data)

# B. ADN
dna_h = tactical_dna.get(home, {"w": 5, "agg": 5})
dna_a = tactical_dna.get(away, {"w": 5, "agg": 5})

# C. Cálculo Corners
base_corners = (h_corn + a_corn) / 2 + 1.0
tactical_boost = 0
if dna_h['w'] > 7 and dna_a['style'] == "LowBlock": tactical_boost += 1.5
if ctx['rain']: tactical_boost += 1.2 # Lluvia = más despejes
if ctx['wind']: tactical_boost -= 1.0 # Viento = menos precisión

pred_corners = base_corners + tactical_boost

# D. Cálculo Tarjetas
base_cards = 3.8
card_boost = 0
if ctx['derby']: card_boost += 1.5 # Rivalidad
if h_foul + a_foul > 24: card_boost += 1.0 # Equipos sucios
if ctx['rain']: card_boost += 0.5 # Entradas deslizantes

pred_cards = base_cards + card_boost

# --- 7. DASHBOARD INTELIGENTE ---

st.divider()
c1, c2 = st.columns([3, 1])
with c1:
    st.subheader(f"⚔️ {home} vs {away}")
    tags = []
    if ctx['derby']: tags.append("🔥 DERBI")
    if ctx['rain']: tags.append("🌧️ LLUVIA")
    if ctx['wind']: tags.append("💨 VIENTO")
    if not tags: tags.append("☁️ NORMAL")
    st.caption(" | ".join(tags))

# --- 8. LA APUESTA RECOMENDADA (THE BEST BET) ---
st.subheader("🎯 El Veredicto del Sniper")

# Lógica de Decisión
bet_found = False

# 1. Estrategia Córners
if pred_corners > 11.0:
    st.markdown(f"""
    <div class="bet-box">
    <b>💰 APUESTA RECOMENDADA: OVER CÓRNERS</b><br>
    Línea sugerida: <b>Más de 9.5</b> o <b>10.5</b><br>
    <i>Por qué:</i> {home} tiene extremos muy anchos ({dna_h['w']}/10) y el clima/estilo favorece despejes.
    </div>
    """, unsafe_allow_html=True)
    bet_found = True
elif pred_corners < 8.5:
    st.markdown(f"""
    <div class="warn-box">
    <b>📉 APUESTA RECOMENDADA: UNDER CÓRNERS</b><br>
    Línea sugerida: <b>Menos de 10.5</b><br>
    <i>Por qué:</i> Juego trabado en mediocampo. Baja amplitud de ataque.
    </div>
    """, unsafe_allow_html=True)
    bet_found = True

# 2. Estrategia Tarjetas
if pred_cards > 5.2:
    st.markdown(f"""<br>
    <div class="bet-box">
    <b>🟨 APUESTA RECOMENDADA: OVER TARJETAS</b><br>
    Línea sugerida: <b>Más de 4.5</b><br>
    <i>Por qué:</i> {'¡Es un Derbi! ' if ctx['derby'] else ''}Alta fricción esperada ({h_foul+a_foul:.0f} faltas recientes).
    </div>
    """, unsafe_allow_html=True)
    bet_found = True

if not bet_found:
    st.info("⚖️ No hay valor claro pre-partido. Se recomienda esperar al Live (Minuto 15).")

# Estadísticas de Soporte
st.divider()
col1, col2, col3 = st.columns(3)
col1.metric("Corners Estimados", f"{pred_corners:.2f}")
col2.metric("Tarjetas Estimadas", f"{pred_cards:.2f}")
col3.metric("Goles Esperados (Total)", f"{(h_goals + a_goals):.2f}")

with st.expander("🔍 Ver Datos de Rastreo (Debug)"):
    st.json({
        "Clima Detectado": ctx,
        "Stats Local (5 últimos)": {"Corners": h_corn, "Faltas": h_foul},
        "Stats Visita (5 últimos)": {"Corners": a_corn, "Faltas": a_foul},
        "ADN Táctico Local": dna_h,
        "ADN Táctico Visita": dna_a
    })
