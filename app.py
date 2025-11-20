import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO

# --- CONFIGURACIÓN DE ÉLITE ---
st.set_page_config(page_title="PL Tactical OS", layout="wide")

st.markdown("""
    <style>
    .main {background-color: #0e1117;}
    h1 {color: #3b82f6;}
    .stMetric {background-color: #1e293b; border-radius: 10px; padding: 10px; border: 1px solid #334155;}
    .tactical-box {padding: 15px; background-color: #172554; border-radius: 8px; margin-bottom: 10px; border-left: 5px solid #3b82f6;}
    </style>
    """, unsafe_allow_html=True)

st.title("🧠 Tactical OS: Premier & Championship")

# --- 1. BASE DE DATOS HÍBRIDA (PL + CHAMPIONSHIP) ---
@st.cache_data(ttl=3600)
def load_all_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # Cargamos Premier (E0) y Championship (E1)
    urls = [
        "https://www.football-data.co.uk/mmz4281/2425/E0.csv", # Premier
        "https://www.football-data.co.uk/mmz4281/2425/E1.csv"  # Championship
    ]
    
    frames = []
    for url in urls:
        try:
            r = requests.get(url, headers=headers)
            if r.ok:
                data = StringIO(r.text)
                df = pd.read_csv(data)
                cols = ['Date', 'HomeTeam', 'AwayTeam', 'Referee', 'HC', 'AC', 'HF', 'AF', 'HY', 'AY', 'HR', 'AR']
                valid_cols = [c for c in cols if c in df.columns]
                frames.append(df[valid_cols].dropna())
        except:
            continue
            
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()

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
    except:
        return pd.DataFrame()

df_data = load_all_data()
df_fix = load_fixtures()

# --- 3. ADN TÁCTICO (BASE DE DATOS MANUAL) ---
tactical_dna = {
    "Man City": {"style": "Possession", "width": 6, "panic": 1, "aggression": 9},
    "Arsenal": {"style": "High Press", "width": 8, "panic": 2, "aggression": 9},
    "Liverpool": {"style": "Direct Attack", "width": 9, "panic": 3, "aggression": 10},
    "Aston Villa": {"style": "High Line", "width": 7, "panic": 4, "aggression": 8},
    "Tottenham": {"style": "Chaosball", "width": 7, "panic": 5, "aggression": 9},
    "Newcastle": {"style": "Physical", "width": 8, "panic": 4, "aggression": 8},
    "Man Utd": {"style": "Counter", "width": 6, "panic": 6, "aggression": 7},
    "West Ham": {"style": "Counter/SetPiece", "width": 5, "panic": 7, "aggression": 6},
    "Chelsea": {"style": "Possession", "width": 7, "panic": 4, "aggression": 8},
    "Brighton": {"style": "Build Up", "width": 8, "panic": 3, "aggression": 7},
    "Wolves": {"style": "Counter", "width": 8, "panic": 5, "aggression": 6},
    "Fulham": {"style": "Balanced", "width": 6, "panic": 5, "aggression": 6},
    "Bournemouth": {"style": "High Press", "width": 7, "panic": 5, "aggression": 7},
    "Crystal Palace": {"style": "Low Block", "width": 5, "panic": 6, "aggression": 5},
    "Brentford": {"style": "Set Piece/Direct", "width": 5, "panic": 6, "aggression": 6},
    "Everton": {"style": "Low Block/Physical", "width": 4, "panic": 8, "aggression": 5},
    "Nott'm Forest": {"style": "Low Block/Counter", "width": 7, "panic": 7, "aggression": 6},
    "Luton": {"style": "Physical/LongBall", "width": 4, "panic": 9, "aggression": 5},
    "Burnley": {"style": "Possession/Weak", "width": 5, "panic": 7, "aggression": 5},
    "Sheffield United": {"style": "Low Block", "width": 3, "panic": 9, "aggression": 4},
    "Leicester": {"style": "Possession", "width": 6, "panic": 5, "aggression": 7},
    "Southampton": {"style": "Possession", "width": 5, "panic": 6, "aggression": 6},
    "Ipswich": {"style": "Direct", "width": 6, "panic": 7, "aggression": 6},
    "Leeds": {"style": "High Press", "width": 8, "panic": 5, "aggression": 8}
}

def get_dna(team_name):
    for key in tactical_dna:
        if key.lower() in team_name.lower() or team_name.lower() in key.lower():
            return tactical_dna[key]
    return {"style": "Unknown", "width": 5, "panic": 5, "aggression": 5}

# --- 4. INTERFAZ ---
st.write("### 🛠️ Configuración Táctica")

if not df_fix.empty:
    opts = [f"{r['Date']} | {r['Home']} vs {r['Away']}" for i, r in df_fix.iterrows()]
    sel = st.selectbox("📅 Calendario", range(len(opts)), format_func=lambda x: opts[x])
    row = df_fix.iloc[sel]
    home, away = row['Home'], row['Away']
else:
    teams = sorted(list(tactical_dna.keys()))
    c1, c2 = st.columns(2)
    home = c1.selectbox("Local", teams, index=0)
    away = c2.selectbox("Visita", teams, index=1)

# --- 5. CONTEXTO AVANZADO ---
with st.expander("🎛️ Ajustar Variables de Contexto (¡IMPORTANTE!)", expanded=True):
    c1, c2, c3 = st.columns(3)
    weather = c1.selectbox("🌦️ Clima", ["Normal", "Lluvia (Cancha Rápida)", "Viento Fuerte"])
    importance = c2.selectbox("🏆 Importancia", ["Liga Normal", "Partido a Muerte/Derbi", "Intrascendente"])
    missing_key = c3.checkbox("🚑 ¿Falta Jugador Clave en Defensa?")

# --- 6. MOTOR DE CÁLCULO ---
def analyze_game(h, a, context_weather, context_imp, context_miss):
    
    # 1. Stats Históricas
    def get_stats(team, df):
        matches = df[(df['HomeTeam'].str.contains(team, na=False)) | (df['AwayTeam'].str.contains(team, na=False))]
        if matches.empty: return 5.0, 10.0
        c_avg = (matches['HC'].mean() + matches['AC'].mean()) / 2
        f_avg = (matches['HF'].mean() + matches['AF'].mean()) / 2
        return c_avg, f_avg

    h_corn, h_foul = get_stats(h, df_data)
    a_corn, a_foul = get_stats(a, df_data)
    
    # 2. ADN Táctico
    dna_h = get_dna(h)
    dna_a = get_dna(a)
    
    # 3. ALGORITMO CORNERS
    pressure_h = (dna_h['width'] * 0.6) + (dna_h['aggression'] * 0.4)
    resistance_a = dna_a['panic']
    pressure_a = (dna_a['width'] * 0.6) + (dna_a['aggression'] * 0.4)
    resistance_h = dna_h['panic']
    
    base_corners = (h_corn + a_corn) / 2 + 1.5
    
    tactical_factor = 1.0
    if pressure_h > 7 and resistance_a > 6: tactical_factor += 0.15
    if pressure_a > 7 and resistance_h > 6: tactical_factor += 0.10
    if dna_h['style'] == "Possession" and dna_a['style'] == "Low Block": tactical_factor += 0.2
        
    # 4. Ajustes Contexto (Corrección del error anterior)
    weather_mod = 1.0
    if context_weather == "Lluvia (Cancha Rápida)": 
        weather_mod = 1.1 
    elif context_weather == "Viento Fuerte": 
        weather_mod = 0.85 
    
    final_corners = base_corners * tactical_factor * weather_mod
    
    # 5. ALGORITMO TARJETAS
    base_cards = 3.8
    intensity_mod = 1.0
    if context_imp == "Partido a Muerte/Derbi": intensity_mod = 1.3
    if context_miss: intensity_mod += 0.1 
    if dna_h['style'] == "Physical" or dna_a['style'] == "Physical": intensity_mod += 0.1
    
    final_cards = base_cards * intensity_mod
    
    return {
        "corners": final_corners,
        "cards": final_cards,
        "dna_h": dna_h,
        "dna_a": dna_a,
        "tactical_factor": tactical_factor
    }

res = analyze_game(home, away, weather, importance, missing_key)

# --- 7. DASHBOARD ---
st.divider()

c1, c2 = st.columns([1, 3])
with c1:
    st.image("https://upload.wikimedia.org/wikipedia/en/f/f2/Premier_League_Logo.svg", width=80)
with c2:
    st.header(f"{home} vs {away}")
    st.caption(f"Choque de Estilos: {res['dna_h']['style']} vs {res['dna_a']['style']}")

k1, k2, k3 = st.columns(3)
k1.metric("🎯 Córners Esperados", f"{res['corners']:.2f}")
k2.metric("⚠️ Intensidad (Tarjetas)", f"{res['cards']:.2f}")
prob_c = (np.random.poisson(res['corners'], 1000) > 9.5).mean() * 100
k3.metric("Prob. Over 9.5 Corners", f"{prob_c:.1f}%", delta="High Value" if prob_c > 60 else None)

st.markdown("### 🕵️ Informe Táctico Detallado")

with st.container():
    st.markdown(f"""
    <div class="tactical-box">
    <b>1. Análisis de Geometría del Partido:</b><br>
    El <b>{home}</b> juega con un estilo <i>{res['dna_h']['style']}</i> y amplitud <b>{res['dna_h']['width']}/10</b>. 
    Se enfrenta a <b>{away}</b> con Pánico Defensivo de <b>{res['dna_a']['panic']}/10</b>.
    </div>
    """, unsafe_allow_html=True)
    
    reasons = []
    
    if res['tactical_factor'] > 1.1:
        reasons.append(f"🔥 **Mismatch Táctico:** {home} atacará por bandas y {away} tiende a despejar a córner bajo presión.")
    elif res['tactical_factor'] < 1.0:
        reasons.append(f"🛡️ **Bloqueo Mutuo:** Los estilos sugieren que el balón se atascará en mediocampo.")
        
    if weather == "Lluvia (Cancha Rápida)":
        reasons.append("🌧️ **Factor Clima:** La lluvia provoca más despejes de seguridad (más corners).")
    
    if missing_key:
        reasons.append("🚑 **Debilidad:** Falta de defensa clave = Más desorden y faltas.")

    for r in reasons:
        st.write(r)

st.write("#### 📊 Distribución de Probabilidades")
sim_data = pd.DataFrame(np.random.poisson(res['corners'], 1000), columns=["Corners"])
st.bar_chart(sim_data['Corners'].value_counts().sort_index())

st.caption("Datos: FPL API + Football-Data Hybrid (E0/E1). Modelo: V4.")
