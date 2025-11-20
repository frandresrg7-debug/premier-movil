import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="PL Mobile Intelligence", layout="wide")
st.title("📱 PL Predicciones: Corners & Tarjetas")

# --- CARGA DE DATOS ---
@st.cache_data(ttl=3600)
def load_data():
    # Datos históricos (CSV)
    url_csv = "https://www.football-data.co.uk/mmz4281/2425/E0.csv"
    try:
        df = pd.read_csv(url_csv)
        # Limpieza básica
        cols = ['Date', 'HomeTeam', 'AwayTeam', 'Referee', 'FTHG', 'FTAG', 'HC', 'AC', 'HY', 'AY', 'HF', 'AF']
        df = df[cols].dropna()
        return df
    except:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.error("Error cargando datos. Intenta recargar la página.")
    st.stop()

# --- FUNCIONES ---
def get_stats(team, df):
    # Filtramos partidos del equipo
    h = df[df['HomeTeam'] == team]
    a = df[df['AwayTeam'] == team]
    
    # Promedio Corners (Local + Visitante)
    corn_h = h['HC'].mean() if not h.empty else 0
    corn_a = a['AC'].mean() if not a.empty else 0
    avg_corn = (corn_h + corn_a) / 2 if (corn_h > 0 and corn_a > 0) else 4.5
    
    # Promedio Faltas
    foul_h = h['HF'].mean() if not h.empty else 0
    foul_a = a['AF'].mean() if not a.empty else 0
    avg_foul = (foul_h + foul_a) / 2 if (foul_h > 0 and foul_a > 0) else 10.0
    
    return avg_corn, avg_foul

def get_ref_stats(ref, df):
    matches = df[df['Referee'] == ref]
    if matches.empty: return 1.0 # Valor por defecto
    
    avg_cards = (matches['HY'].sum() + matches['AY'].sum()) / len(matches)
    league_avg = (df['HY'].sum() + df['AY'].sum()) / len(df)
    
    # Factor de severidad
    return avg_cards / league_avg

# --- INTERFAZ MÓVIL ---
teams = sorted(df['HomeTeam'].unique())
refs = sorted(df['Referee'].unique())

st.write("### ⚽ Configurar Partido")
col1, col2 = st.columns(2)
home = col1.selectbox("Local", teams, index=0)
away = col2.selectbox("Visita", teams, index=1)
ref = st.selectbox("Árbitro", refs)

if home == away:
    st.warning("Selecciona equipos distintos")
    st.stop()

# --- CÁLCULOS ---
c_h, f_h = get_stats(home, df)
c_a, f_a = get_stats(away, df)
ref_factor = get_ref_stats(ref, df)

# Predicción Corners (Modelo Simple Ponderado)
# Sumamos promedios + Factor Liga
pred_corners = c_h + c_a + 1.5 

# Predicción Tarjetas
# (Faltas Local + Faltas Visita) / 6.5 * Severidad Árbitro
pred_cards = ((f_h + f_a) / 6.5) * ref_factor

# Simulación (Montecarlo)
sim_c = np.random.poisson(pred_corners, 1000)
prob_over_9 = (sim_c > 9.5).mean() * 100

sim_t = np.random.poisson(pred_cards, 1000)
prob_over_4 = (sim_t > 4.5).mean() * 100

# --- RESULTADOS ---
st.divider()
st.header("📊 Resultados")

tab1, tab2 = st.tabs(["🚩 Corners", "🟨 Tarjetas"])

with tab1:
    st.metric("Total Esperado", f"{pred_corners:.2f}")
    st.metric("Probabilidad +9.5", f"{prob_over_9:.1f}%")
    if prob_over_9 > 60:
        st.success("Alta probabilidad de Corners")
    else:
        st.info("Partido normal/bajo en corners")

with tab2:
    st.metric("Tarjetas Esperadas", f"{pred_cards:.2f}")
    st.metric("Probabilidad +4.5", f"{prob_over_4:.1f}%")
    st.write(f"Severidad Árbitro: x{ref_factor:.2f}")
    if ref_factor > 1.15:
        st.error("¡Árbitro muy estricto!")
