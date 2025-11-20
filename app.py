import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO
from datetime import datetime
from scipy.stats import poisson

# --- CONFIGURACIÓN DE LA MATRIZ ---
st.set_page_config(page_title="PREMIER GOD MODE", layout="wide", initial_sidebar_state="collapsed")

# Estilos CSS Avanzados
st.markdown("""
    <style>
    .main {background-color: #050505; color: #e0e0e0;}
    h1, h2, h3 {color: #00ff9d; font-family: 'Courier New', monospace; text-transform: uppercase;}
    .metric-card {background-color: #111; border: 1px solid #333; padding: 20px; border-radius: 5px; margin-bottom: 10px;}
    .highlight {color: #00ff9d; font-weight: bold;}
    .danger {color: #ff4b4b; font-weight: bold;}
    .warning {color: #ffa700; font-weight: bold;}
    div[data-testid="stExpander"] details summary {background-color: #1a1a1a !important; border-radius: 5px;}
    </style>
    """, unsafe_allow_html=True)

st.title("🧬 PREMIER LEAGUE: GOD MODE ENGINE")
st.markdown("`v.Final_Fixed` | Data Fusion: FPL API + FootballData + MeteoSat + Poisson Sims")

# ==============================================================================
# 1. CAPA DE DATOS (DATA LAYER)
# ==============================================================================

@st.cache_data(ttl=3600)
def load_comprehensive_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    urls = [
        "https://www.football-data.co.uk/mmz4281/2425/E0.csv", # PL Actual
        "https://www.football-data.co.uk/mmz4281/2425/E1.csv", # Championship
        "https://www.football-data.co.uk/mmz4281/2324/E0.csv"  # PL Año Pasado
    ]
    
    frames = []
    for u in urls:
        try:
            r = requests.get(u, headers=headers)
            if r.ok:
                df = pd.read_csv(StringIO(r.text))
                cols_needed = ['Date', 'HomeTeam', 'AwayTeam', 'Referee', 'FTHG', 'FTAG', 
                               'HS', 'AS', 'HST', 'AST', 'HC', 'AC', 'HF', 'AF', 'HY', 'AY', 'HR', 'AR']
                valid_cols = [c for c in cols_needed if c in df.columns]
                df = df[valid_cols].dropna()
                df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
                frames.append(df)
        except: continue
    
    if not frames: return pd.DataFrame()
    
    full_df = pd.concat(frames, ignore_index=True)
    full_df = full_df.sort_values('Date')
    return full_df

df_master = load_comprehensive_data()

# --- API FPL (Calendario Oficial) ---
@st.cache_data(ttl=3600)
def load_fpl_fixtures():
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

df_fix = load_fpl_fixtures()

# ==============================================================================
# 2. MOTOR DE INGENIERÍA DE CARACTERÍSTICAS
# ==============================================================================

def calculate_advanced_metrics(team, df, side='All', last_n=10):
    if side == 'Home':
        matches = df[df['HomeTeam'] == team].tail(last_n)
        corn = matches['HC']; fouls = matches['HF']; shots = matches['HS']; cards = matches['HY']
        conc_corn = matches['AC']; conc_shots = matches['AS']
    elif side == 'Away':
        matches = df[df['AwayTeam'] == team].tail(last_n)
        corn = matches['AC']; fouls = matches['AF']; shots = matches['AS']; cards = matches['AY']
        conc_corn = matches['HC']; conc_shots = matches['HS']
    else:
        # Fallback simple para 'All'
        return calculate_advanced_metrics(team, df, 'Home', last_n)

    if matches.empty:
        return {"corners": 4.5, "fouls": 10.0, "pressure_idx": 50, "width_idx": 50, "friction_idx": 20, "panic_idx": 50, "conc_corners": 4.5, "cards": 2.0}

    avg_shots = shots.mean()
    avg_corners = corn.mean()
    pressure_index = (avg_shots * 0.6) + (avg_corners * 1.5)
    
    width_ratio = (avg_corners / avg_shots) if avg_shots > 0 else 0.1
    width_index = width_ratio * 100
    
    avg_fouls = fouls.mean()
    avg_cards = cards.mean()
    friction = avg_fouls + (avg_cards * 3)
    
    avg_conc_shots = conc_shots.mean()
    avg_conc_corners = conc_corn.mean()
    panic_index = (avg_conc_corners / avg_conc_shots * 100) if avg_conc_shots > 0 else 50

    return {
        "corners": avg_corners,
        "fouls": avg_fouls,
        "cards": avg_cards,
        "shots": avg_shots,
        "pressure_idx": pressure_index,
        "width_idx": width_index,
        "friction_idx": friction,
        "panic_idx": panic_index,
        "conc_corners": avg_conc_corners
    }

def analyze_referee(ref_name, df):
    if not ref_name: return {"strictness": 1.0, "avg_cards": 3.8}
    matches = df[df['Referee'] == ref_name]
    if matches.empty: return {"strictness": 1.0, "avg_cards": 3.8}
    
    total_cards = matches['HY'].sum() + matches['AY'].sum() + (matches['HR'].sum() + matches['AR'].sum())*2
    avg = total_cards / len(matches)
    league_cards = (df['HY'] + df['AY']).mean()
    strictness = avg / league_cards if league_cards > 0 else 1.0
    
    return {"strictness": strictness, "avg_cards": avg}

# ==============================================================================
# 3. CONTEXTO AMBIENTAL
# ==============================================================================

stadiums = {
    "Arsenal": (51.55, -0.10), "Aston Villa": (52.50, -1.88), "Man City": (53.48, -2.20), 
    "Liverpool": (53.43, -2.96), "Man Utd": (53.46, -2.29), "Chelsea": (51.48, -0.19),
    "Newcastle": (54.97, -1.62), "Tottenham": (51.60, -0.06), "West Ham": (51.53, 0.01)
}

def get_weather(home_team):
    coords = stadiums.get(home_team, (51.5, -0.1))
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords[0]}&longitude={coords[1]}&current=rain,wind_speed_10m"
        data = requests.get(url).json()['current']
        return {"rain": data['rain'], "wind": data['wind_speed_10m']}
    except:
        return {"rain": 0.0, "wind": 10.0}

# ==============================================================================
# 4. INTERFAZ Y SELECCIÓN
# ==============================================================================

name_map = {
    "Man Utd": "Man United", "Nott'm Forest": "Nott'm Forest", "Sheffield Utd": "Sheffield United",
    "Luton": "Luton", "Spurs": "Tottenham", "Man City": "Man City", "Wolves": "Wolves"
}
def normalize(n): return name_map.get(n, n)

if df_fix.empty:
    st.error("⚠️ API FPL Offline. Modo Manual Activado.")
    all_teams = sorted(df_master['HomeTeam'].unique())
    c1, c2 = st.columns(2)
    home_team = c1.selectbox("Local", all_teams)
    away_team = c2.selectbox("Visita", all_teams)
else:
    options = [f"{r['Date']} | {r['Home']} vs {r['Away']}" for i, r in df_fix.iterrows()]
    selection = st.selectbox("📅 SELECCIONA PARTIDO (API OFICIAL)", range(len(options)), format_func=lambda x: options[x])
    sel_row = df_fix.iloc[selection]
    home_team = normalize(sel_row['Home'])
    away_team = normalize(sel_row['Away'])

referees = sorted(df_master['Referee'].dropna().unique())
ref_idx = referees.index("Michael Oliver") if "Michael Oliver" in referees else 0
selected_ref = st.selectbox("👮 Árbitro Designado (Opcional)", referees, index=ref_idx)

# ==============================================================================
# 5. EL CEREBRO (THE REASONING ENGINE)
# ==============================================================================

st.divider()
st.markdown(f"### 🛰️ ANÁLISIS PROFUNDO: {home_team} vs {away_team}")

with st.spinner("Procesando puntos de datos..."):
    
    stats_h = calculate_advanced_metrics(home_team, df_master, 'Home', last_n=8)
    stats_a = calculate_advanced_metrics(away_team, df_master, 'Away', last_n=8)
    weather = get_weather(home_team)
    ref_data = analyze_referee(selected_ref, df_master)
    
    # --- ALGORITMO DE PREDICCIÓN ---
    
    # A. CÓRNERS
    style_mismatch = 1.0
    if stats_h['width_idx'] > 25 and stats_a['panic_idx'] > 30:
        style_mismatch += 0.15 
    
    weather_factor = 1.0
    if weather['rain'] > 0.5: weather_factor += 0.10 # Lluvia
    if weather['wind'] > 25: weather_factor -= 0.15 # Viento
    
    exp_corners = ((stats_h['corners'] + stats_a['conc_corners']) / 2) + \
                  ((stats_a['corners'] + stats_h['conc_corners']) / 2) 
    
    final_corners = exp_corners * style_mismatch * weather_factor
    
    # B. TARJETAS
    exp_cards = ((stats_h['cards'] + stats_a['cards']) / 2) + 1.5 
    friction_total = stats_h['friction_idx'] + stats_a['friction_idx']
    friction_factor = friction_total / 30 
    
    final_cards = exp_cards * friction_factor * ref_data['strictness']
    
    # --- SIMULACIÓN MONTECARLO ---
    sim_corners = poisson.rvs(final_corners, size=5000)
    prob_over_9 = (sim_corners > 9.5).mean() * 100
    
    sim_cards = poisson.rvs(final_cards, size=5000)
    prob_over_4 = (sim_cards > 4.5).mean() * 100

# ==============================================================================
# 6. REPORTE VISUAL
# ==============================================================================

tab1, tab2, tab3 = st.tabs(["🧠 ANÁLISIS TÁCTICO", "📊 DATA CRUDA", "🤖 AI VERDICT"])

with tab1:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Córners Esperados", f"{final_corners:.2f}", delta=f"Clima: {weather['rain']}mm")
    k2.metric("Prob Over 9.5", f"{prob_over_9:.1f}%", delta="Umbral Clave")
    k3.metric("Tarjetas Esperadas", f"{final_cards:.2f}", delta=f"Ref: {ref_data['strictness']:.2f}x")
    k4.metric("Prob Over 4.5", f"{prob_over_4:.1f}%")
    
    st.write("#### 🧬 ADN del Partido")
    c_style1, c_style2 = st.columns(2)
    
    with c_style1:
        st.markdown(f"**{home_team} (Local)**")
        st.progress(min(int(stats_h['width_idx']), 100))
        st.caption(f"Amplitud de Ataque: {stats_h['width_idx']:.1f}/100")

    with c_style2:
        st.markdown(f"**{away_team} (Visita)**")
        st.progress(min(int(stats_a['panic_idx']), 100))
        st.caption(f"Pánico Defensivo: {stats_a['panic_idx']:.1f}/100")

with tab2:
    st.dataframe(df_master[(df_master['HomeTeam'] == home_team) | (df_master['AwayTeam'] == home_team)].tail(5))

with tab3:
    st.markdown("### 📝 REPORTE DETALLADO")
    
    # Análisis de Córners
    st.markdown("#### 🚩 Geometría del Campo (Córners)")
    reason_c = []
    if stats_h['width_idx'] > 30:
        reason_c.append(f"• El **{home_team}** tiene una Amplitud ALTA ({stats_h['width_idx']:.1f}). Ataca mucho por las bandas.")
    if stats_a['panic_idx'] > 35:
        reason_c.append(f"• El **{away_team}** tiene Pánico Defensivo ALTO ({stats_a['panic_idx']:.1f}). Despeja mucho a córner.")
    if weather['rain'] > 0.0:
        reason_c.append(f"• **Lluvia Detectada:** {weather['rain']}mm. Aumenta probabilidad de despejes.")
    
    if not reason_c: st.write("• Partido con métricas estándar.")
    else: 
        for r in reason_c: st.write(r)
        
    # Veredicto
    if prob_over_9 > 65:
        st.markdown(f"<div class='metric-card highlight'>🚀 <b>CONCLUSIÓN:</b> Alta probabilidad de OVER CÓRNERS.</div>", unsafe_allow_html=True)
    elif prob_over_9 < 40:
        st.markdown(f"<div class='metric-card warning'>🛑 <b>CONCLUSIÓN:</b> Escenario de UNDER CÓRNERS.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='metric-card'>⚖️ <b>CONCLUSIÓN:</b> Mercado sin valor claro.</div>", unsafe_allow_html=True)
        
    # Análisis Disciplinario
    st.markdown("#### 🟨 Disciplina")
    st.write(f"• Árbitro **{selected_ref}**. Severidad: **{ref_data['strictness']:.2f}**.")
    
    if prob_over_4 > 60:
         st.markdown(f"<div class='metric-card highlight'>⚔️ <b>ALERTA:</b> Probable partido con muchas tarjetas.</div>", unsafe_allow_html=True)

st.caption("System ID: GOD_MODE_V2 | Powered by Python")
