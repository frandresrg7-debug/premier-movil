import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="PL Pro Predictor", layout="wide")
st.title("⚽ Premier League: Inteligencia Deportiva")

# --- 1. CARGA DE DATOS HISTÓRICOS (STATS) ---
@st.cache_data(ttl=3600)
def load_stats():
    # Base de datos de Football-Data.co.uk (Confiable para stats pasados)
    url = "https://www.football-data.co.uk/mmz4281/2425/E0.csv"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = StringIO(r.text)
        df = pd.read_csv(data)
        cols = ['Date', 'HomeTeam', 'AwayTeam', 'Referee', 'FTHG', 'FTAG', 'HC', 'AC', 'HY', 'AY', 'HF', 'AF']
        existing = [c for c in cols if c in df.columns]
        return df[existing].dropna()
    except:
        return pd.DataFrame()

# --- 2. CARGA DEL CALENDARIO (FANTASY PREMIER LEAGUE API) ---
# Esta API es oficial y nunca se bloquea.
@st.cache_data(ttl=3600)
def load_fixtures_official():
    try:
        # 1. Obtener nombres de equipos (ID -> Nombre)
        r_teams = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/")
        teams_data = r_teams.json()['teams']
        id_to_name = {t['id']: t['name'] for t in teams_data}
        
        # 2. Obtener partidos
        r_fix = requests.get("https://fantasy.premierleague.com/api/fixtures/")
        fixtures = r_fix.json()
        
        # 3. Filtrar partidos futuros
        future_games = []
        for f in fixtures:
            if not f['finished'] and f['event'] is not None:
                # Solo próxima jornada (aprox)
                home_name = id_to_name.get(f['team_h'], "Unknown")
                away_name = id_to_name.get(f['team_a'], "Unknown")
                # Formato de fecha
                kickoff = f['kickoff_time'][:10] 
                future_games.append({
                    "Date": kickoff,
                    "Home": home_name,
                    "Away": away_name
                })
                
        return pd.DataFrame(future_games).head(15) # Solo los siguientes 15
    except:
        return pd.DataFrame()

df_stats = load_stats()
df_fix = load_fixtures_official()

# --- 3. UNIFICACIÓN DE NOMBRES (DICCIONARIO INTELIGENTE) ---
# FPL llama "Spurs" a "Tottenham", el CSV lo llama "Tottenham", etc.
def normalize_name(name):
    name = name.lower()
    mapping = {
        "spurs": "Tottenham",
        "tottenham": "Tottenham",
        "man utd": "Man United",
        "man united": "Man United",
        "man city": "Man City",
        "nott'm forest": "Nott'm Forest",
        "nottingham": "Nott'm Forest",
        "wolves": "Wolves",
        "brighton": "Brighton",
        "newcastle": "Newcastle",
        "leicester": "Leicester",
        "sheffield utd": "Sheffield United",
        "west ham": "West Ham",
        "luton": "Luton"
    }
    for k, v in mapping.items():
        if k in name: return v
    # Si no está en el mapa, intentar capitalizar
    return name.title()

# --- 4. INTERFAZ DE SELECCIÓN ---
st.write("### 📅 Próximos Partidos (Fuente: API Oficial)")

if df_fix.empty:
    st.error("Error conectando a la API. Usa el modo manual abajo.")
    teams = sorted(df_stats['HomeTeam'].unique())
    home_input = st.selectbox("Local", teams)
    away_input = st.selectbox("Visita", teams)
else:
    # Crear lista desplegable
    options = []
    for i, row in df_fix.iterrows():
        options.append(f"{row['Date']} | {row['Home']} vs {row['Away']}")
    
    sel_idx = st.selectbox("Selecciona el encuentro:", range(len(options)), format_func=lambda x: options[x])
    
    # Obtener nombres y normalizarlos para buscar en la base de datos
    raw_h = df_fix.iloc[sel_idx]['Home']
    raw_a = df_fix.iloc[sel_idx]['Away']
    home_input = normalize_name(raw_h)
    away_input = normalize_name(raw_a)

# --- 5. MOTOR DE ANÁLISIS PROFUNDO ---

def analyze_match(h_team, a_team, df):
    # Buscar equipos en el CSV (Búsqueda flexible)
    # A veces el nombre normalizado no es idéntico, buscamos "contiene"
    def get_df_team(name, side):
        # Intento exacto
        d = df[df[side] == name]
        if not d.empty: return d
        # Intento parcial
        all_teams = df[side].unique()
        matches = [t for t in all_teams if name[:4] in t]
        if matches: return df[df[side] == matches[0]]
        return pd.DataFrame()

    h_data = get_df_team(h_team, 'HomeTeam')
    a_data = get_df_team(a_team, 'AwayTeam')
    
    # SI no hay datos (ej. equipo recién ascendido sin partidos en CSV)
    if h_data.empty or a_data.empty:
        return None

    # ESTADÍSTICAS CLAVE
    # 1. Corners
    hc_for = h_data['HC'].mean()      # Corners a favor Local
    hc_ag = h_data['AC'].mean()       # Corners en contra Local (Concedidos)
    ac_for = a_data['AC'].mean()      # Corners a favor Visita
    ac_ag = a_data['HC'].mean()       # Corners en contra Visita (Concedidos)
    
    # 2. Tarjetas (Faltas como proxy de intensidad)
    hf = h_data['HF'].mean()
    af = a_data['AF'].mean()
    
    # 3. Lógica de Predicción
    # Geometría: Ataque Local vs Defensa Visita + Ataque Visita vs Defensa Local
    exp_corn_h = (hc_for + ac_ag) / 2 
    exp_corn_a = (ac_for + hc_ag) / 2
    total_corners = exp_corn_h + exp_corn_a * 1.05 # Factor corrector liga
    
    # Intensidad
    total_fouls = hf + af
    
    return {
        "h_stats": {"c_for": hc_for, "c_ag": hc_ag, "f": hf},
        "a_stats": {"c_for": ac_for, "c_ag": ac_ag, "f": af},
        "pred_corners": total_corners,
        "pred_fouls": total_fouls
    }

analysis = analyze_match(home_input, away_input, df_stats)

# Selector de Árbitro
st.write("---")
col_ref, col_extra = st.columns(2)
refs = sorted(df_stats['Referee'].unique()) if 'Referee' in df_stats.columns else []
sel_ref = col_ref.selectbox("Árbitro del partido:", refs)

# Datos Árbitro
ref_factor = 1.0
ref_avg = 3.8
if not df_stats.empty and sel_ref:
    ref_d = df_stats[df_stats['Referee'] == sel_ref]
    if not ref_d.empty:
        ref_avg = (ref_d['HY'].sum() + ref_d['AY'].sum()) / len(ref_d)
        league_avg = (df_stats['HY'].sum() + df_stats['AY'].sum()) / len(df_stats)
        ref_factor = ref_avg / league_avg

# --- 6. GENERACIÓN DEL REPORTE ---
if analysis:
    p_corn = analysis['pred_corners']
    p_cards = (analysis['pred_fouls'] / 6.5) * ref_factor
    
    # Simulación Montecarlo
    sim_c = np.random.poisson(p_corn, 1000)
    prob_c_95 = (sim_c > 9.5).mean() * 100
    
    sim_k = np.random.poisson(p_cards, 1000)
    prob_k_45 = (sim_k > 4.5).mean() * 100

    st.header("📊 Informe del Analista IA")
    
    tab1, tab2 = st.tabs(["🚩 Análisis de Córners", "🟨 Análisis Disciplinario"])
    
    with tab1:
        c1, c2 = st.columns(2)
        c1.metric("Línea Esperada", f"{p_corn:.2f}")
        c2.metric("Prob. Over 9.5", f"{prob_c_95:.1f}%")
        
        st.markdown("#### 📝 ¿Por qué esta predicción?")
        
        # Lógica explicada
        h_s = analysis['h_stats']
        a_s = analysis['a_stats']
        
        # Razón 1: Potencia Local
        txt_h = f"**{home_input} en casa** es {'muy agresivo' if h_s['c_for'] > 6 else 'moderado'} generando {h_s['c_for']:.1f} córners por partido."
        
        # Razón 2: Debilidad Visitante
        txt_a = f"**{away_input} fuera** concede una media de {a_s['c_ag']:.1f} córners al rival."
        
        # Razón 3: Choque
        verdict = ""
        if p_corn > 10.5:
            verdict = "🔥 **Conclusión:** Partido muy abierto. Se espera que ambos equipos ataquen y las defensas despejen mucho."
            st.success(verdict)
        elif p_corn < 9.0:
            verdict = "🧊 **Conclusión:** Partido trabado. Las estadísticas sugieren juego en mediocampo y pocas llegadas a línea de fondo."
            st.warning(verdict)
        else:
            verdict = "⚖️ **Conclusión:** Partido promedio. No hay una ventaja estadística clara."
            st.info(verdict)
            
        st.markdown(f"""
        *   {txt_h}
        *   {txt_a}
        *   La suma matemática de tendencias proyecta: **{p_corn:.2f}** saques de esquina.
        """)

    with tab2:
        k1, k2 = st.columns(2)
        k1.metric("Tarjetas Est.", f"{p_cards:.2f}")
        k2.metric("Prob. Over 4.5", f"{prob_k_45:.1f}%")
        
        st.markdown("#### ⚖️ Factor Arbitral")
        st.markdown(f"El árbitro es **{sel_ref}**.")
        
        if ref_factor > 1.1:
            st.error(f"⚠️ **¡Cuidado!** Este árbitro es ESTRICTO. Saca un {((ref_factor-1)*100):.0f}% más de tarjetas que el promedio de la liga ({ref_avg:.2f} por partido).")
        elif ref_factor < 0.9:
            st.success(f"Este árbitro es PERMISIVO. Solo saca {ref_avg:.2f} tarjetas por partido (Promedio Liga: 4.0).")
        else:
            st.info(f"Árbitro estándar ({ref_avg:.2f} tarjetas/partido).")
            
        st.markdown(f"**Fricción esperada:** Se proyectan unas **{analysis['pred_fouls']:.0f} faltas** totales basadas en el estilo de los equipos.")

else:
    st.warning("No hay suficientes datos históricos para generar un reporte detallado de estos equipos.")
