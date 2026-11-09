import streamlit as st
from utils import get_db_client, update_account_composition

def render_mode_general(db_accounts, accounts_dict, ordered_tags):
    st.subheader("📊 Vue d'ensemble de tous les joueurs et Compositions")
    
    conn = get_db_client()
    comps_res = conn.execute("SELECT comp_name, details FROM compositions")
    all_comps = {row[0]: row[1] for row in comps_res.rows}
    comp_options = list(all_comps.keys())
    
    if not db_accounts:
        st.info("Aucun compte enregistré.")
        return

    header_cols = st.columns([1, 0.5, 0.5, 4.5, 1.1, 0.6])
    header_cols[0].markdown("**Pseudo**")
    header_cols[1].markdown("**HDV**")
    header_cols[2].markdown("**Ligue**")
    header_cols[3].markdown("**Composition Active**")
    header_cols[4].markdown("**Ordre**")
    header_cols[5].markdown("**Action**")
    st.divider()

    total_accounts = len(ordered_tags)
    new_ordered_tags = list(ordered_tags)

    for idx, tag in enumerate(ordered_tags):
        if tag not in accounts_dict:
            continue
        acc = accounts_dict[tag]
        name, th, active_comp = acc[1], acc[2], acc[3]
        
        row_cols = st.columns([1, 0.5, 0.5, 4.5, 1.1, 0.6])
        
        row_cols[0].markdown(f"**{name}**")
        row_cols[1].markdown(f"TH {th}")
        row_cols[2].markdown("0 🏆")
        
        details_raw = all_comps.get(active_comp, "") if active_comp else ""
        cleaned_details = details_raw
        for prefix in [
            "Héros ->", "Pet:", "Équipements:", "Troupes:", "Sorts:", 
            "Barbarian King", "Archer Queen", "Grand Warden", "Royal Champion", "Minion Prince",
            "L.A.S.S.I", "Mighty Yak", "Electro Owl", "Unicorn", "Phoenix", 
            "Poison Lizard", "Diggy", "Frosty", "Spirit Fox", "Angry Jelly", "Sneezy", "Greedy Raven",
            " Spell"
        ]:
            cleaned_details = cleaned_details.replace(prefix, "")
            
        cleaned_details = cleaned_details.replace("()", "").replace("  ", " ").strip(" |-/")
        comp_display_text = f"**{active_comp}** — <span style='font-size: 0.9em; color: #ddd;'>{cleaned_details}</span>" if active_comp in all_comps else ":grey[Aucune composition assignée]"
        
        row_cols[3].markdown(comp_display_text, unsafe_allow_html=True)
        
        with row_cols[4]:
            col_num, col_btns = st.columns([1.3, 1])
            with col_num:
                new_pos = st.number_input(
                    "Pos", 
                    min_value=1, 
                    max_value=total_accounts, 
                    value=idx + 1, 
                    step=1, 
                    key=f"num_pos_{tag}", 
                    label_visibility="collapsed"
                )
                if new_pos - 1 != idx:
                    target_idx = int(new_pos - 1)
                    if tag in new_ordered_tags:
                        new_ordered_tags.remove(tag)
                        new_ordered_tags.insert(target_idx, tag)
                        st.session_state["accounts_order_state"] = new_ordered_tags

            with col_btns:
                col_u, col_d = st.columns(2)
                with col_u:
                    if idx > 0:
                        if st.button("⬆️", key=f"up_{tag}", help="Monter"):
                            new_ordered_tags[idx], new_ordered_tags[idx - 1] = new_ordered_tags[idx - 1], new_ordered_tags[idx]
                            st.session_state["accounts_order_state"] = new_ordered_tags
                            st.rerun()
                with col_d:
                    if idx < total_accounts - 1:
                        if st.button("⬇️", key=f"down_{tag}", help="Descendre"):
                            new_ordered_tags[idx], new_ordered_tags[idx + 1] = new_ordered_tags[idx + 1], new_ordered_tags[idx]
                            st.session_state["accounts_order_state"] = new_ordered_tags
                            st.rerun()

        with row_cols[5]:
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
                        new_comp = st.selectbox("Compo", comp_options, index=current_idx, key=f"sel_{tag}", label_visibility="collapsed")
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.form_submit_button("💾"):
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

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 **Enregistrer définitivement l'ordre des comptes**", type="primary", use_container_width=True):
        for new_idx, p_tag in enumerate(st.session_state["accounts_order_state"]):
            conn.execute("UPDATE accounts SET display_order = ? WHERE player_tag = ?", [new_idx, p_tag])
        st.success("✅ Ordre des comptes enregistré avec succès !")
        st.rerun()
