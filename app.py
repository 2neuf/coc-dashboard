import streamlit as st
from utils import init_db, get_all_accounts, fetch_player_data, get_db_favorites
from tabs.tab_config import render_tab_config
from tabs.tab_overview import render_tab_overview
from tabs.tab_army import render_tab_army
from tabs.tab_troops import render_tab_troops

st.set_page_config(page_title="CoC Multi-Account Dashboard", page_icon="🛡️", layout="wide")

# 1. Initialisation de la base de données
init_db()

# 2. Indicateur de chargement visuel au démarrage
loading_placeholder = st.empty()

with loading_placeholder.container():
    st.info("🔄 **Chargement en cours...** Synchronisation des données et du cache.")
    progress_bar = st.progress(0)
    progress_bar.progress(40)

# Récupération des comptes depuis la DB
accounts = get_all_accounts()
if not accounts:
    loading_placeholder.empty()
    st.warning("Aucun compte trouvé dans la base de données.")
    st.stop()

# Barre latérale : Gestion des comptes
st.sidebar.title("Gestion des Comptes")
account_names = [acc[1] for acc in accounts]
selected_name = st.sidebar.selectbox("Choisir le compte actif", account_names)

active_account = next(acc for acc in accounts if acc[1] == selected_name)
current_tag = active_account[0]
player_name = active_account[1]

st.sidebar.markdown(f"**Pseudo : {player_name} Tag : {current_tag}**")

progress_bar.progress(75)

# Récupération des données API (mises en cache)
data, error = fetch_player_data(current_tag)
if error:
    st.error(f"❌ Erreur lors de la récupération des données de l'API : {error}")
    data = {}

current_favorites = get_db_favorites()

# Fin du chargement : on nettoie la zone de chargement
progress_bar.progress(100)
loading_placeholder.empty()

# --- 3. AFFICHAGE DES ONGLETS DE L'APPLICATION ---
st.title("🛡️ Clash of Clans Dashboard — Multi-Comptes")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Vue d'ensemble", 
    "⚔️ Héros, Familiers & Équipements", 
    "🧪 Troupes, Engins & Sorts", 
    "⚙️ Paramétrage Compositions"
])

with tab1:
    render_tab_overview(data, current_tag)

with tab2:
    render_tab_army(data, current_favorites)

with tab3:
    render_tab_troops(data, current_favorites)

with tab4:
    render_tab_config(data, current_tag, player_name, current_favorites)
