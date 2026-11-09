import streamlit as st
from utils import get_db_client
from tabs.overview_modes.mode_general import render_mode_general
from tabs.overview_modes.mode_league import render_mode_league
from tabs.overview_modes.mode_ranked import render_mode_ranked

def render_tab_overview():
    overview_mode = st.radio(
        "Mode de la Vue d'ensemble",
        [
            "📊 Vue d'ensemble des joueurs et Compositions", 
            "⚔️ Ligue Overview",
            "🏆 Ligues Classées"
        ],
        index=0,
        horizontal=True,
        label_visibility="collapsed"
    )

    conn = get_db_client()
    
    # Récupération des comptes triés par display_order actuel
    accounts_res = conn.execute("SELECT player_tag, name, town_hall, active_composition, display_order FROM accounts ORDER BY display_order ASC, name ASC")
    db_accounts = accounts_res.rows
    
    if "accounts_order_state" not in st.session_state:
        st.session_state["accounts_order_state"] = [row[0] for row in db_accounts]
    else:
        current_tags = [row[0] for row in db_accounts]
        if set(st.session_state["accounts_order_state"]) != set(current_tags):
            st.session_state["accounts_order_state"] = current_tags

    accounts_dict = {row[0]: row for row in db_accounts}
    ordered_tags = st.session_state["accounts_order_state"]

    # Redirection vers le mode approprié
    if overview_mode == "⚔️ Ligue Overview":
        render_mode_league(accounts_dict, ordered_tags)
    elif overview_mode == "🏆 Ligues Classées":
        render_mode_ranked(db_accounts, accounts_dict, ordered_tags)
    else:
        render_mode_general(db_accounts, accounts_dict, ordered_tags)
