import streamlit as st
from utils import init_db, get_all_accounts, fetch_player_data, get_db_favorites
from tabs.tab_config import render_tab_config
# Importe ici tes autres fichiers d'onglets si tu les as séparés, par exemple :
# from tabs.tab_overview import render_tab_overview
# from tabs.tab_heroes import render_tab_heroes
# from tabs.tab_troops import render_tab_troops

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
    st.markdown("### Vue d'ensemble du compte")
    if data:
        st.write(f"**Hôtel de Ville :** {data.get('townHallLevel', 'N/A')}")
        st.write(f"**Expérience :** {data.get('expLevel', 'N/A')}")
        st.write(f"**Trophées :** {data.get('trophies', 'N/A')} 🏆")
    else:
        st.info("Données non disponibles.")

with tab2:
    st.markdown("### Gestion des Héros & Équipements")
    heroes = data.get("heroes", [])
    if heroes:
        for h in heroes:
            if h.get("village") == "home":
                st.markdown(f"- **{h.get('name')}** (Niveau {h.get('level')}/{h.get('maxLevel')})")
    else:
        st.info("Aucun héros trouvé.")

with tab3:
    st.markdown("### Gestion des Troupes & Sorts")
    troops = data.get("troops", [])
    if troops:
        st.write(f"Total troupes détectées : {len(troops)}")
    else:
        st.info("Aucune troupe trouvée.")

with tab4:
    # Onglet de configuration avec les 3 modes géré par tab_config.py
    render_tab_config(data, current_tag, player_name, current_favorites)
