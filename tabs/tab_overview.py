import streamlit as st
from utils import get_db_client, update_account_composition, fetch_player_data, get_db_favorites, get_icon_emoji

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

    # Colonnes ultra-compactes pour pseudo, HDV, ligue, action, et toute la largeur pour la compo
    header_cols = st.columns([1, 0.5, 0.5, 6, 0.6])
    header_cols[0].markdown("**Pseudo**")
    header_cols[1].markdown("**HDV**")
    header_cols[2].markdown("**Ligue**")
    header_cols[3].markdown("**Composition Active**")
    header_cols[4].markdown("**Action**")
    st.divider()

    for acc in accounts:
        tag, name, th, active_comp = acc[0], acc[1], acc[2], acc[3]
        
        row_cols = st.columns([1, 0.5, 0.5, 6, 0.6])
        
        row_cols[0].markdown(f"**{name}**")
        row_cols[1].markdown(f"TH {th}")
        row_cols[2].markdown("0 🏆")
        
        # Nettoyage et épuration du texte des détails pour ne garder que l'essence visuelle
        details_raw = all_comps.get(active_comp, "") if active_comp else ""
        
        # Si on veut alléger le texte brut enregistré en retirant les mots superflus
        cleaned_details = details_raw.replace("Héros ->", "").replace("Pet:", "").replace("Équipements:", "").replace("Troupes:", "").replace("Sorts:", "")
        
        comp_display_text = f"**{active_comp}** — <span style='font-size: 0.9em; color: #ddd;'>{cleaned_details}</span>" if active_comp in all_comps else ":grey[Aucune composition assignée]"
        
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
                                st.rerun()
                        with col_cancel:
                            if st.form_submit_button("❌"):
                                st.session_state[edit_state_key] = False
                                st.rerun()
            else:
                st.caption("⚠️")
        
        st.markdown("---")
