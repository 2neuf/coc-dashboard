import streamlit as st
from utils import get_all_accounts, fetch_player_data, get_db_client

def render_tab_overview():
    st.subheader("📊 Vue d'ensemble de tous les joueurs")
    
    all_accs = get_all_accounts()
    overview_data = []
    
    conn_db = get_db_client()
    for acc in all_accs:
        p_tag, p_name, p_th, p_comp = acc[0], acc[1], acc[2], acc[3]
        
        p_data, p_err = fetch_player_data(p_tag)
        if not p_err and p_data:
            l_info = p_data.get("league")
            p_trophies = p_data.get("trophies", 0)
            if l_info and isinstance(l_info, dict) and l_info.get("name"):
                l_name = l_info.get("name")
            else:
                l_name = f"Légende ({p_trophies} 🏆)" if p_trophies >= 5000 else f"{p_trophies} 🏆"
        else:
            l_name = "Inconnu"
        
        comp_details_text = "Aucune"
        if p_comp and p_comp != "Aucune":
            comp_res = conn_db.execute("SELECT details FROM compositions WHERE comp_name = ?", [p_comp])
            if comp_res.rows:
                comp_details_text = f"📌 {p_comp} — {comp_res.rows[0][0]}"
            else:
                comp_details_text = p_comp

        overview_data.append({
            "Pseudo": p_name,
            "HDV": f"TH {p_th}",
            "Ligue": l_name,
            "Composition d'attaque": comp_details_text
        })
        
    st.dataframe(overview_data, width='stretch')
