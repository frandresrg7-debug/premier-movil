import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="PL Auto Fixtures", layout="wide")
st.title("📅 Predicciones Premier League")

# --- 1. CARGA DE DATOS HISTÓRICOS (STATS) ---
@st.cache_data(ttl=3600)
def load_stats():
    url_csv = "https://www.football-data.co.uk/mmz4281/2425/E0.csv"
    try:
        df = pd.read_csv(url_csv)
        cols = ['Date', 'HomeTeam', 'AwayTeam', 'Referee', 'FTHG', 'FTAG', 'HC', 'AC', 'HY', 'AY', 'HF', 'AF']
        df = df[cols].dropna()
        return df
    except:
        return pd.DataFrame()

# --- 2. CARGA DEL CALENDARIO (FIXTURES) ---
@st.cache_data(ttl=3600)
def load_fixtures():
    # Usamos FBRef para ver los partidos que vienen
    url = "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
    try:
        dfs = pd.read_html(url)
        # La tabla de calendario suele ser la primera
        df_fix = dfs[0]
        # Filtramos los que NO tienen resultado (Score es NaN), o sea, partidos futuros
        upcoming = df_fix[df_fix['Score'].isna()].copy()
        upcoming = upcoming[['Date', 'Home', 'Away']].head(15) # Tomamos los próximos 15
        return upcoming
    except:
        return pd.DataFrame()

df_stats = load_stats()
df_fix = load_fixtures()

if df_stats.empty:
    st.error("Error cargando estadísticas históricas.")
    st.stop()

# --- 3. DICCIONARIO DE TRADUCCIÓN ---
# FBRef usa unos nombres y el CSV usa otros. Esto los unifica.
name_map = {
    "Manchester Utd": "Man United",
    "Manchester City": "Man City",
    "Nott'ham Forest": "Nott'm Forest",
    "Sheffield Utd": "Sheffield United",
    "Wolverhampton": "Wolves",
    "Brighton": "Brighton",
    "Tottenham": "Tottenham",
    "West Ham": "West Ham",
    "Newcastle Utd": "Newcastle",
    "Luton Town": "Luton"
}

def normalize_name(name):
    return name_map.get(name, name) # Si no está en la lista, devuelve el original

# --- 4. INTERFAZ DE SELECCIÓN ---
st.write("### ⚽ Próximos Partidos")

if df_fix.empty:
    st.warning("No se pudo cargar el calendario. Selección manual:")
    teams = sorted(df_stats['HomeTeam'].unique())
    home_team = st.selectbox("Local", teams)
    away_team = st.selectbox("Visita", teams)
else:
    # Crear lista bonita para el desplegable
    match_options = []
    match_data = [] # Guardamos los datos reales para usarlos luego
    
    for index, row in df_fix.iterrows():
        h_raw = row['Home']
        a_raw = row['Away']
        date = row['Date']
        
        label = f"{date} | {h_raw} vs {a_raw}"
        match_options.append(label)
        match_data.append((h_raw, a_raw))
    
    # EL DESPLEGABLE MÁGICO
    selected_idx = st.selectbox("Selecciona la Jornada:", range(len(match_options)), format_func=lambda x: match_options[x])
    
    # Obtener equipos seleccionados y traducirlos
    raw_home, raw_away = match_data[selected_idx]
    home_team = normalize_name(raw_home)
    away_team = normalize_name(raw_away)
    
    st.info(f"Analizando: **{home_team}** vs **{away_team}**")

# --- 5. LÓGICA DE PREDICCIÓN (Tu algoritmo) ---

def get_team_metrics(team, df):
    # Filtramos partidos previos
    games_h = df[df['HomeTeam'] == team]
    games_a = df[df['AwayTeam'] == team]
    
    # Si el nombre no coincide exacto, intentamos búsqueda parcial
    if games_h.empty and games_a.empty:
        # Intento de rescate por si el nombre está mal escrito
        team_options = df['HomeTeam'].unique()
        matches = [t for t in team_options if team[:4] in t]
        if matches:
            team = matches[0]
            games_h = df[df['HomeTeam'] == team]
            games_a = df[df['AwayTeam'] == team]
    
    # Promedios
    c_h = games_h['HC'].mean() if not games_h.empty else 4.5
    c_a = games_a['AC'].mean() if not games_a.empty else 4.0
    
    f_h = games_h['HF'].mean() if not games_h.empty else 10.5
    f_a = games_a['AF'].mean() if not games_a.empty else 10.5
    
    # Corners totales promedio del equipo
    avg_corners = (c_h + c_a) / 2
    avg_fouls = (f_h + f_a) / 2
    
    return avg_corners, avg_fouls

# Obtener stats
c1, f1 = get_team_metrics(home_team, df_stats)
c2, f2 = get_team_metrics(away_team, df_stats)

# Selector de Árbitro (Aún manual porque no se sabe hasta el final)
refs = sorted(df_stats['Referee'].unique())
ref_idx = 0
try:
    # Intentar poner por defecto a Michael Oliver si existe (ejemplo)
    ref_idx = refs.index('M Oliver')
except:
    pass
referee = st.selectbox("Árbitro (Selecciona si lo sabes)", refs, index=ref_idx)

# Obtener dureza árbitro
ref_data = df_stats[df_stats['Referee'] == referee]
ref_strictness = 1.0
if not ref_data.empty:
    cards_pg = (ref_data['HY'].sum() + ref_data['AY'].sum()) / len(ref_data)
    league_avg_cards = (df_stats['HY'].sum() + df_stats['AY'].sum()) / len(df_stats)
    ref_strictness = cards_pg / league_avg_cards

# --- 6. CÁLCULOS Y RESULTADOS ---

# Predicción Matemática
pred_corners = c1 + c2 + 1.0 # Ajuste base liga
pred_cards = ((f1 + f2) / 6.5) * ref_strictness

# Simulación
sim_corn = np.random.poisson(pred_corners, 2000)
prob_over_9 = (sim_corn > 9.5).mean() * 100

sim_card = np.random.poisson(pred_cards, 2000)
prob_over_4 = (sim_card > 4.5).mean() * 100

st.divider()
t1, t2 = st.tabs(["🚩 Córners", "🟨 Tarjetas"])

with t1:
    c_col1, c_col2 = st.columns(2)
    c_col1.metric("Línea Esperada", f"{pred_corners:.2f}")
    c_col2.metric("Probabilidad +9.5", f"{prob_over_9:.1f}%")
    
    if prob_over_9 > 65:
        st.success(f"🔥 **ALTA PROBABILIDAD:** El modelo sugiere OVER en {home_team} vs {away_team}.")
    elif prob_over_9 < 40:
        st.error("🧊 **BAJA PROBABILIDAD:** Partido tiende al Under.")
    else:
        st.info("⚖️ **NEUTRO:** No hay valor claro.")

with t2:
    k_col1, k_col2 = st.columns(2)
    k_col1.metric("Tarjetas Est.", f"{pred_cards:.2f}")
    k_col2.metric("Prob +4.5", f"{prob_over_4:.1f}%")
    
    st.caption(f"Factor Árbitro ({referee}): x{ref_strictness:.2f}")
