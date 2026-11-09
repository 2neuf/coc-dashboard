import streamlit as st
from utils import init_db, get_all_accounts, fetch_player_data, get_db_favorites

# Configuration de la page
st.set_page_config(page_title="CoC Multi-Account Dashboard", page_icon="🛡️", layout="wide")

# Initialisation de la base de données au démarrage
init_db()

# Écran de chargement global (freeze de l'application pendant la récupération des requêtes et du cache)
with st.spinner("🔄 Chargement des données du compte et synchronisation de la base de données..."):
    # Récupération des comptes et du compte actif
    accounts = get_all_accounts()
    if not accounts:
        st.warning("Aucun compte trouvé dans la base de données.")
        st.stop()
        
    # Gestion de la sélection du compte actif dans la barre latérale
    st.sidebar.title("Gestion des Comptes")
    account_names = [acc[1] for acc in accounts]
    selected_name = st.sidebar.selectbox("Choisir le compte actif", account_names)
    
    active_account = next(acc for acc in accounts if acc[1] == selected_name)
    current_tag = active_account[0]
    player_name = active_account[1]
    
    st.sidebar.markdown(f"**Pseudo : {player_name} Tag : {current_tag}**")
    
    # Appel des données de l'API Clash of Clans (mis en cache automatiquement via utils.py)
    data, error = fetch_player_data(current_tag)
    if error:
        st.error(f"❌ Erreur lors de la récupération des données de l'API : {error}")
        data = {}

    # Récupération des favoris depuis la base de données
    current_favorites = get_db_favorites()

# --- ICI TU CONTINUES AVEC L'AFFICHAGE DE TES ONGLETS CLASSIQUES ---
# Exemple :
# tab_overview, tab_heroes, tab_troops, tab_config = st.tabs(["Vue d'ensemble", "Héros...", "Troupes...", "Paramétrage"])
# with tab_config:
#     render_tab_config(data, current_tag, player_name, current_favorites)
