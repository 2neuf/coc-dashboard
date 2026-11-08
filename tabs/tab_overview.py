import streamlit as st
from utils import get_db_client, update_account_composition

def render_tab_overview():
    st.subheader("📊 Vue d'ensemble de tous les joueurs et Compositions")
    
    conn = get_db_client()
    
    accounts_res = conn.execute("SELECT player_tag, name, town_hall, active_composition FROM accounts")
    accounts = accounts_res.rows
    
    comps_res = conn.execute("SELECT comp_name, town_hall_level FROM compositions")
    all_comps = comps_res.rows
    comp_options = [row[0] for row in all_comps]
    
    if not accounts:
        st.info("Aucun compte enregistré.")
        return

    header_cols = st.columns([2, 1, 1, 2, 2])
    header_cols[0].markdown("**Pseudo**")
    header_cols[1].markdown("**HDV**")
    header_cols[2].markdown("**Ligue**")
    header_cols[3].markdown("**Compo Actuelle**")
    header_cols[4].markdown("**Changer de compo**")
    st.divider()

    for acc in accounts:
        tag, name, th, active_comp = acc[0], acc[1], acc[2], acc[3]
        
        row_cols = st.columns([2, 1, 1, 2, 2])
        
        row_cols[0].markdown(f"**{name}**\n`{tag}`")
        row_cols[1].markdown(f"TH {th}")
        row_cols[2].markdown("0 🏆")
        row_cols[3].markdown(f":blue[**{active_comp if active_comp else 'Aucune'}**]")
        
        with row_cols[4]:
            if comp_options:
                current_idx = comp_options.index(active_comp) if active_comp in comp_options else 0
                
                with st.form(key=f"form_comp_{tag}"):
                    new_comp = st.selectbox(
                        "Compo", 
                        comp_options, 
                        index=current_idx, 
                        key=f"sel_{tag}", 
                        label_visibility="collapsed"
                    )
                    submitted = st.form_submit_button("💾 Enregistrer")
                    if submitted:
                        update_account_composition(tag, new_comp)
                        st.success(f"Mis à jour pour {name} !")
                        st.rerun()
            else:
                st.caption("⚠️ Créez une compo d'abord")
        
        st.markdown("---")
