import streamlit as st
import pandas as pd
from utils import get_db_client, update_account_composition

def render_tab_overview():
    overview_mode = st.radio(
        "Mode de la Vue d'ensemble",
        [
            "📊 Vue d'ensemble des joueurs et Compositions", 
            "⚔️ Ligue Overview"
        ],
        index=0,
        horizontal=True,
        label_visibility="collapsed"
    )

    conn = get_db_client()
    
    # Récupération des comptes triés par display_order actuel
    accounts_res = conn.execute("SELECT player_tag, name, town_hall, active_composition, display_order FROM accounts ORDER BY display_order ASC, name ASC")
    db_accounts = accounts_res.rows
    
    # Initialisation de l'ordre en session_state si absent ou si la liste a changé
    if "accounts_order_state" not in st.session_state:
        st.session_state["accounts_order_state"] = [row[0] for row in db_accounts]
    else:
        current_tags = [row[0] for row in db_accounts]
        if set(st.session_state["accounts_order_state"]) != set(current_tags):
            st.session_state["accounts_order_state"] = current_tags

    accounts_dict = {row[0]: row for row in db_accounts}
    ordered_tags = st.session_state["accounts_order_state"]
    account_order_map = {tag: idx for idx, tag in enumerate(ordered_tags)}

    if overview_mode == "⚔️ Ligue Overview":
        st.subheader("⚔️ Suivi de la Ligue de Guerre de Clan")
        
        league_data = st.session_state.get("cached_league_data", None)
        
        if not league_data or not league_data.get("wars"):
            st.info("⚠️ Aucune donnée de ligue disponible ou active pour ce clan.")
            return
            
        wars_cache = league_data.get("wars", [])
        CLAN_TAG = "#2U0GCGPJU"
        
        my_clan_wars = []
        for w in wars_cache:
            if w and (w.get("clan", {}).get("tag") == CLAN_TAG or w.get("opponent", {}).get("tag") == CLAN_TAG):
                my_clan_wars.append(w)
        
        my_clan_wars = sorted(my_clan_wars, key=lambda x: x.get("startTime", ""))[:7]
        actual_days_columns = [f"Jour {i+1}" for i in range(len(my_clan_wars))]
        
        players_data = {}
        
        for day_idx, war in enumerate(my_clan_wars):
            day_col = actual_days_columns[day_idx]
            side = "clan" if war.get("clan", {}).get("tag") == CLAN_TAG else "opponent"
            clan_info = war.get(side, {})
            
            for member in clan_info.get("members", []):
                p_tag = member.get("tag")
                p_name = member.get("name")
                
                if p_tag not in players_data:
                    players_data[p_tag] = {
                        "name": p_name,
                        "days": {d: "⏳ Non jouée" for d in actual_days_columns}
                    }
                else:
                    players_data[p_tag]["name"] = p_name
                
                attacks = member.get("attacks", [])
                if attacks:
                    atk_details = []
                    for atk in attacks:
                        stars = atk.get("stars", 0)
                        destruction = atk.get("destructionPercentage", 0)
                        icon = "⭐" if stars > 0 else "❌"
                        atk_details.append(f"{icon} {stars}★ ({destruction}%)")
                    players_data[p_tag]["days"][day_col] = " | ".join(atk_details)

        if players_data:
            # Tri selon l'ordre en cours dans la session
            sorted_p_tags = sorted(players_data.keys(), key=lambda t: account_order_map.get(t, 999))
            
            df_rows = []
            for p_tag in sorted_p_tags:
                info = players_data[p_tag]
                row = {"Membre": info["name"]}
                row.update(info["days"])
                df_rows.append(row)
                
            df = pd.DataFrame(df_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun participant trouvé pour cette ligue.")

    else:
        # Mode 1 : Vue d'ensemble de tous les joueurs et Compositions
        st.subheader("📊 Vue d'ensemble de tous les joueurs et Compositions")
        
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
        
        # Tableaux temporaires pour stocker les modifications de position par l'utilisateur
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
            
            # Saisie directe de la position ou boutons ⬆️ / ⬇️ sans rechargement intempestif
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
                    # Mise à jour de l'ordre en mémoire sans forcer de rerun immédiat
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

        # Bouton unique de validation globale en bas de page
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 **Enregistrer définitivement l'ordre des comptes**", type="primary", use_container_width=True):
            for new_idx, p_tag in enumerate(st.session_state["accounts_order_state"]):
                conn.execute("UPDATE accounts SET display_order = ? WHERE player_tag = ?", [new_idx, p_tag])
            st.success("✅ Ordre des comptes enregistré avec succès !")
            st.rerun()
