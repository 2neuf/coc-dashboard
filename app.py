import streamlit as st
from utils import init_db, get_all_accounts, get_db_favorites, fetch_player_data, get_db_client
from tabs.tab_overview import render_tab_overview
from tabs.tab_army import render_tab_army
from tabs.tab_troops import render_tab_troops
from tabs.tab_config import render_tab_config

st.set_page_config(page_title="CoC Multi-Account Dashboard", layout="wide", page_icon="🛡️")

# CSS Globale
st.markdown("""
<style>
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #1e1e2e;
        border-radius: 10px;
        border: 1px solid #313244;
        padding: 8px;
        min-height: 135px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .max-title {
        color: #22c55e !important;
        font-weight: bold;
    }
    .custom-progress-bg {
        background-color: #313244;
        border-radius: 4px;
        height: 8px;
        width: 100%;
        margin-top: 6px;
        overflow: hidden;
    }
    .custom-progress-fill-blue {
        background-color: #3b82f6;
        height: 100%;
        border-radius: 4px;
    }
    .custom-progress-fill-green {
        background-color: #22c55e;
        height: 100%;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Clash of Clans Dashboard — Multi-Comptes")

try:
    init_db()
    st.sidebar.success("✅ Turso DB Connected")
except Exception as e:
    st.sidebar.error(f"❌ DB Error: {e}")

accounts_list = get_all_accounts()
account_options = {row[1]: row[0] for row in accounts_list}

st.sidebar.header("Gestion des Comptes")
selected_account_name = st.sidebar.selectbox("Choisir le compte actif", list(account_options.keys()))
current_tag = account_options[selected_account_name]
player_name = selected_account_name

st.sidebar.info(f"Pseudo : **{player_name}**\nTag : **{current_tag}**")

current_favorites = get_db_favorites(current_tag)

with st.spinner("Fetching data from Supercell API..."):
    data, err = fetch_player_data(current_tag)

if err:
    st.error(err)
else:
    try:
        conn = get_db_client()
        conn.execute(
            "INSERT OR REPLACE INTO accounts (player_tag, name, town_hall, active_composition) VALUES (?, ?, ?, COALESCE((SELECT active_composition FROM accounts WHERE player_tag = ?), 'Aucune'))",
            [data.get("tag"), player_name, data.get("townHallLevel"), data.get("tag")]
        )
    except Exception as e:
        st.warning(f"Could not update Turso DB: {e}")

    tab_overview, tab_army, tab_troops, tab_config = st.tabs([
        "📊 Vue d'ensemble", 
        "⚔️ Héros, Familiers & Équipements", 
        "🧪 Troupes, Engins & Sorts", 
        "⚙️ Paramétrage Compositions"
    ])

    with tab_overview:
        render_tab_overview()

    with tab_army:
        render_tab_army(data, current_tag, current_favorites)

    with tab_troops:
        render_tab_troops(data, current_tag, current_favorites)

    with tab_config:
        render_tab_config(data, current_tag, player_name)
