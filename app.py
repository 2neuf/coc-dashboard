import streamlit as st
from utils import init_db, get_all_accounts, fetch_player_data, get_db_favorites

st.set_page_config(page_title="CoC Multi-Account Dashboard", page_icon="🛡️", layout="wide")

# Initialisation de la base de données
init_db()

# Utilisation d'un conteneur vide pour créer un effet de "pop-up" ou de zone de chargement dédiée
loading_placeholder = st.empty()

with loading_placeholder.container():
    st.info("🔄 **Chargement en cours...** Veuillez patienter pendant la synchronisation des données et du cache.")
    # On peut ajouter une barre de progression visuelle pour faire patienter
    progress_bar = st.progress(0)
    progress_bar.progress(50)

# Récupération des comptes
accounts = get_all_accounts()
if not accounts:
    loading_placeholder.empty()
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

# Récupération des données API
progress_bar.progress(80)
data, error = fetch_player_data(current_tag)
if error:
    st.error(f"❌ Erreur lors de la récupération des données de l'API : {error}")
    data = {}

current_favorites = get_db_favorites()

# Fin du chargement : on efface la boîte de chargement pour laisser place au dashboard
progress_bar.progress(100)
loading_placeholder.empty()
