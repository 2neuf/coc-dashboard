import streamlit as st
from utils import init_db, get_all_accounts, fetch_player_data, get_db_favorites, get_db_client, fetch_clan_war_league
from tabs.tab_config import render_tab_config
from tabs.tab_overview import render_tab_overview
from tabs.tab_army import render_tab_army
from tabs.tab_troops import render_tab_troops

st.set_page_config(page_title="CoC Multi-Account Dashboard", page_icon="🛡️", layout="wide")

# 1. Initialisation de la base de données
init_db()

# 2. Gestion du verrou global et du chargement complet en amont
if "app_fully_loaded" not in st.session_state:
    st.session_state["app_fully_loaded"] = False

if not st.session_state["app_fully_loaded"]:
    with st.spinner("🔄 **Chargement complet en cours...** Synchronisation de l'API Clash of Clans, de la base de données, des ligues et des caches."):
        
        # Récupération des comptes
        accounts = get_all_accounts()
        if not accounts:
            st.warning("Aucun compte trouvé dans la base de données.")
            st.stop()

        # Barre latérale : Gestion des comptes
        st.sidebar.title("Gestion des Comptes")
        account_names = [acc[1] for acc in accounts]
        selected_name = st.sidebar.selectbox("Choisir le compte actif", account_names, key="account_selector")

        active_account = next(acc for acc in accounts if acc[1] == selected_name)
        current_tag = active_account[0]
        player_name = active_account[1]

        st.sidebar.markdown(f"**Pseudo : {player_name} Tag : {current_tag}**")

        # Récupération des données API du joueur et stockage en session
        data, error = fetch_player_data(current_tag)
        if error:
            st.error(f"❌ Erreur lors de la récupération des données de l'API : {error}")
            data = {}

        st.session_state["cached_player_data"] = data
        st.session_state["cached_favorites"] = get_db_favorites()
        st.session_state["current_tag"] = current_tag
        st.session_state["player_name"] = player_name

        # Préchargement des données de la Ligue de Guerre de Clan (CWL) pour le clan #2U0GCGPJU
        CLAN_TAG = "#2U0GCGPJU"
        league_data, league_error = fetch_clan_war_league(CLAN_TAG)
        st.session_state["cached_league_data"] = league_data

        # Préchargement global des emojis et compositions en mémoire
        conn_db = get_db_client()
        try:
            emoji_res = conn_db.execute("SELECT item_name, emoji FROM custom_emojis")
            st.session_state["preloaded_emojis"] = {row[0]: row[1] for row in emoji_res.rows}
        except Exception:
            st.session_state["preloaded_emojis"] = {}

        try:
            comp_res = conn_db.execute("SELECT * FROM compositions")
            st.session_state["preloaded_compositions"] = comp_res.rows
        except Exception:
            st.session_state["preloaded_compositions"] = []

        # Validation de la fin du chargement global
        st.session_state["app_fully_loaded"] = True
        st.rerun()

# --- 3. AFFICHAGE DE L'INTERFACE (Exécuté uniquement lorsque tout est 100% prêt) ---
st.title("🛡️ Clash of Clans Dashboard — Multi-Comptes")

data = st.session_state.get("cached_player_data", {})
current_favorites = st.session_state.get("cached_favorites", [])
current_tag = st.session_state.get("current_tag", "")
player_name = st.session_state.get("player_name", "")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Vue d'ensemble", 
    "⚔️ Héros, Familiers & Équipements", 
    "🧪 Troupes, Engins & Sorts", 
    "⚙️ Paramétrage Compositions"
])

with tab1:
    render_tab_overview()

with tab2:
    render_tab_army(data, current_favorites)

with tab3:
    render_tab_troops(data, current_favorites)

with tab4:
    render_tab_config(data, current_tag, player_name, current_favorites)
