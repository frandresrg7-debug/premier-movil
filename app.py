import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="PL Fixtures Pro", layout="wide")
st.title("📅 Predicciones Premier League")

# --- 1. CARGA DE DATOS HISTÓRICOS (STATS) ---
@st.cache_data(ttl=3600)
def load_stats():
    # CSV Histórico de Football-Data.co.uk
    url_csv = "https://www.football-data.co.uk/mmz4281/2425/E0.csv"
    try:
        # Usamos requests para bajarlo seguro
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url_csv, headers=headers)
        r.raise_for_status()
        
        data = StringIO(r.text)
        df = pd.read_csv(data)
        
        cols = ['Date', 'HomeTeam', 'AwayTeam', 'Referee', 'FTHG', 'FTAG', 'HC', 'AC', 'HY', 'AY', 'HF', 'AF']
        # Filtramos solo columnas que existan (evita errores si cambia el formato)
        existing_cols = [c for c in cols if c in df.columns]
        df = df[existing_cols].dropna()
        return df
    except Exception as e:
        return pd.DataFrame()

# --- 2. CARGA DEL CALENDARIO (FIXTURES) - VERSIÓN BLINDADA ---
@st.cache_data(ttl=3600)
def load_fixtures():
    # URL de Fixtures de FBRef
    url = "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
    
    # EL DISFRAZ: Headers completos de Chrome
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    try:
        # 1. Petición directa con requests
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Avisar si hay error 403/404
        
        # 2. Pandas lee el HTML texto
        # 'match' busca una tabla que contenga la palabra "Score" para no equivocarse
        dfs = pd.read_html(StringIO(response.text), match="Score")
        df_fix = dfs[0]
        
        # 3. Limpieza: Buscamos partidos sin goles (futuros)
        # FBRef pone el Score vacío o NaN para partidos que no se han jugado
        upcoming = df_fix[df_fix['Score'].isna()].copy()
        
        # Seleccionar columnas y limpiar
        upcoming = upcoming[['Date', 'Home', 'Away']].dropna()
        
        return upcoming.head(15) # Devolvemos los próximos 15
        
    except Exception as e:
        # Si falla, devolvemos vacío pero no rompemos la app
        return pd.DataFrame()

df_stats = load_stats()
df_fix = load_fixtures()

if df_stats.empty:
    st.error("⚠️ Error conectando con la base de datos de estadísticas.")
    st.stop()

# --- 3. DICCIONARIO DE NOMBRES ---
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
    "Luton Town": "Luton",
    "Ipswich Town": "Ipswich",
    "Leicester City": "Leicester"
}

def normalize(name):
    return name_map.get(name, name)

# --- 4. INTERFAZ ---
st.write("### ⚽ Próximos Encuentros")

# Lógica de selección inteligente
home_team, away_team = None, None

if df_fix.empty:
    st.warning("⚠️ Modo Manual (Calendario bloqueado temporalmente)")
    teams = sorted(df_stats['HomeTeam'].unique())
    c1, c2 = st.columns(2)
    home_team = c1.selectbox("Local", teams, index=0)
    away_team = c2.selectbox("Visita", teams, index=1)
else:
    # Crear lista para el desplegable
    options = []
    raw_teams = []
    
    for idx, row in df_fix.iterrows():
        h_raw = row['Home']
        a_raw = row['Away']
        date = row['Date']
        label = f"{date} | {h_raw} vs {a_raw}"
        options.append(label)
        raw_teams.append((h_raw, a_raw))
    
    selected_idx = st.selectbox("Selecciona Jornada:", range(len(options)), format_func=lambda x: options[x])
    
    h_sel, a_sel = raw_teams[selected_idx]
    home_team = normalize(h_sel)
    away_team = normalize(a_sel)
    
    st.success(f"Analizando: **{home_team}** vs **{away_team}**")

# --- 5. MOTOR DE PREDICCIÓN ---
def get_team_metrics(team, df):
    # Filtro flexible (busca si el nombre está contenido en el del CSV)
    # Esto ayuda si 'Man City' no hace match con 'Manchester City'
    games_h = df[df['HomeTeam'] == team]
    games_a = df[df['AwayTeam'] == team]
    
    if games_h.empty and games_a.empty:
        # Intento de búsqueda inteligente
        possible = [t for t in df['HomeTeam'].unique() if team[:4] in t]
        if possible:
            team = possible[0]
            games_h = df[df['HomeTeam'] == team]
            games_a = df[df['AwayTeam'] == team]

    # Stats Córners
    c_h = games_h['HC'].mean() if not games_h.empty else 5.0
    c_a = games_a['AC'].mean() if not games_a.empty else 4.5
    
    # Stats Faltas
    f_h = games_h['HF'].mean() if not games_h.empty else 10.0
    f_a = games_a['AF'].mean() if not games_a.empty else 10.0
    
    return (c_h + c_a)/2, (f_h + f_a)/2

# Árbitro (Opcional)
refs = sorted(df_stats['Referee'].unique()) if 'Referee' in df_stats.columns else []
referee = st.selectbox("Árbitro (Opcional)", refs) if refs else None

# Cálculos
c1, f1 = get_team_metrics(home_team, df_stats)
c2, f2 = get_team_metrics(away_team, df_stats)

# Algoritmo
pred_corners = c1 + c2 + 1.0 # Factor ajuste liga
pred_cards = 3.5 # Base
ref_factor = 1.0

if referee:
    ref_d = df_stats[df_stats['Referee'] == referee]
    if not ref_d.empty:
        avg_ref = (ref_d['HY'].sum() + ref_d['AY'].sum()) / len(ref_d)
        avg_lea = (df_stats['HY'].sum() + df_stats['AY'].sum()) / len(df_stats)
        ref_factor = avg_ref / avg_lea
        pred_cards = ((f1 + f2) / 6.5) * ref_factor

# Simulación
sim_c = np.random.poisson(pred_corners, 1500)
prob_c = (sim_c > 9.5).mean() * 100

sim_k = np.random.poisson(pred_cards, 1500)
prob_k = (sim_k > 4.5).mean() * 100

# --- DASHBOARD ---
st.divider()
t1, t2 = st.tabs(["🚩 Córners", "🟨 Tarjetas"])

with t1:
    c1, c2 = st.columns(2)
    c1.metric("Línea Estimada", f"{pred_corners:.2f}")
    c2.metric("Prob. Over 9.5", f"{prob_c:.1f}%")
    
    if prob_c > 60:
        st.info("📈 Tendencia: ALTA (Over)")
    else:
        st.write("📉 Tendencia: Baja/Normal")

with t2:
    k1, k2 = st.columns(2)
    k1.metric("Tarjetas Est.", f"{pred_cards:.2f}")
    k2.metric("Prob. Over 4.5", f"{prob_k:.1f}%")
    
    if referee:
        st.caption(f"Árbitro estricto: x{ref_factor:.2f}")
