import streamlit as st
from utils import get_db_client, update_account_composition, fetch_player_data, sort_items, get_db_favorites, get_icon_emoji

def render_tab_overview():
    st.subheader("📊 Vue d'ensemble de tous les joueurs et Compositions")
    
    conn = get_db_client()
    
    accounts_res = conn.execute("SELECT player_tag, name, town_hall, active_composition FROM accounts")
    accounts = accounts_res.rows
    
    comps_res = conn.execute("SELECT comp_name, details FROM compositions")
    all_comps = {row[0]: row[1] for row in comps_res.rows}
    
    comp_options = list(all_comps.keys())
    
    if not accounts:
        st.info("Aucun compte enregistré.")
        return

    # Colonnes asymétriques : la compo actuelle prend le maximum de largeur (5)
    header_cols = st.columns([1, 0.6, 0.6, 5, 0.8])
    header_cols[0].markdown("**Pseudo**")
    header_cols[1].markdown("**HDV**")
    header_cols[2].markdown("**Ligue**")
    header_cols[3].markdown("**Compo Actuelle & Détails**")
    header_cols[4].markdown("**Action**")
    st.divider()

    favorites = get_db_favorites()

    for acc in accounts:
        tag, name, th, active_comp = acc[0], acc[1], acc[2], acc[3]
        
        row_cols = st.columns([1, 0.6, 0.6, 5, 0.8])
        
        row_cols[0].markdown(f"**{name}**")
        row_cols[1].markdown(f"TH {th}")
        row_cols[2].markdown("0 🏆")
        
        # Récupérer les données live du joueur pour analyser les niveaux (héros, troupes, sorts, équipements)
        p_data, _ = fetch_player_data(tag)
        
        comp_display_text = f":blue[**{active_comp}**]"
        if active_comp in all_comps and p_data:
            # On peut formater un affichage enrichi et compact sur une seule ligne
            # Analyse rapide des niveaux pour l'affichage compact
            details_raw = all_comps[active_comp]
            comp_display_text = f"**{active_comp}** — <span style='font-size: 0.85em; color: #ccc;'>{details_raw}</span>"
        elif active_comp == "Aucune" or not active_comp:
            comp_display_text = ":grey[Aucune composition assignée]"

        row_cols[3].markdown(comp_display_text, unsafe_allow_html=True)
        
        with row_cols[4]:
            if comp_options:
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
