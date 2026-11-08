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

    # Disposition des colonnes optimisée et resserrée pour la modification
    header_cols = st.columns([1.5, 1, 1, 2, 1])
    header_cols[0].markdown("**Pseudo**")
    header_cols[1].markdown("**HDV**")
    header_cols[2].markdown("**Ligue**")
    header_cols[3].markdown("**Compo Actuelle**")
    header_cols[4].markdown("**Action**")
    st.divider()

    for acc in accounts:
        tag, name, th, active_comp = acc[0], acc[1], acc[2], acc[3]
        
        row_cols = st.columns([1.5, 1, 1, 2, 1])
        
        # Affichage propre du pseudo sans le tag
        row_cols[0].markdown(f"**{name}**")
        row_cols[1].markdown(f"TH {th}")
        row_cols[2].markdown("0 🏆")
        row_cols[3].markdown(f":blue[**{active_comp if active_comp else 'Aucune'}**]")
        
        with row_cols[4]:
            if comp_options:
                # Gestion de l'état d'affichage du sélecteur par compte
                edit_state_key = f"editing_{tag}"
                if edit_state_key not in st.session_state:
                    st.session_state[edit_state_key] = False

                if not st.session_state[edit_state_key]:
                    if st.button("✏️", key=f"btn_edit_{tag}", help="Modifier la composition"):
                        st.session_state[edit_state_key] = True
                        st.rerun()
                else:
                    current_idx = comp_options.index(active_comp) if active_comp in comp_options else 0
                    with st.form(key=f"form_comp_{tag}"):
                        new_comp = st.selectbox(
                            "Compo", 
                            comp_options, 
                            index=current_idx, 
                            key=f"sel_{tag}", 
                            label_visibility="collapsed"
                        )
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            submitted = st.form_submit_button("💾")
                            if submitted:
                                update_account_composition(tag, new_comp)
                                st.session_state[edit_state_key] = False
                                st.success(f"Mis à jour !")
                                st.rerun()
                        with col_cancel:
                            if st.form_submit_button("❌"):
                                st.session_state[edit_state_key] = False
                                st.rerun()
            else:
                st.caption("⚠️ Aucune compo")
        
        st.markdown("---")
