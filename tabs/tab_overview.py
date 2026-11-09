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

    if overview_mode == "⚔️ Ligue Overview":
        st.subheader("⚔️ Suivi de la Ligue de Guerre de Clan")
        
        league_data = st.session_state.get("cached_league_data", None)
        
        if not league_data or not league_data.get("wars") or not league_data.get("group"):
            st.info("⚠️ Aucune donnée de ligue disponible ou active pour ce clan.")
            return
            
        group = league_data.get("group", {})
        wars_cache = league_data.get("wars", [])
        CLAN_TAG = "#2U0GCGPJU"
        
        # Indexons les détails de guerres récupérés par leur tag pour un accès rapide
        wars_map = {w.get("teamSize"): w for w in wars_cache} # ou via leur tag de guerre si disponible
        # Plus proprement, associons chaque war_tag des rounds du groupe
        rounds_info = group.get("rounds", [])
        
        days_columns = [f"Jour {i+1}" for i in range(len(rounds_info))]
        member_attacks = {}
        
        # Parcourir chaque jour (round) de la ligue
        for day_idx, round_obj in enumerate(rounds_info):
            day_name = f"Jour {day_idx+1}"
            war_tags = round_obj.get("warTags", [])
            
            # Chercher dans les guerres de ce round celle qui concerne notre clan
            for war_tag in war_tags:
                if not war_tag or war_tag == "#0":
                    continue
                
                # Retrouver la guerre correspondante dans le cache ou la requêter/filtrer
                # Dans notre fetch_clan_war_league, on avait stocké toutes les guerres valides. 
                # Cherchons la guerre dans la liste globale des wars récupérées :
                matched_war = None
                for w in wars_cache:
                    # Vérifier si notre clan est clan1 ou opponent dans cette guerre
                    if w.get("clan", {}).get("tag") == CLAN_TAG or w.get("opponent", {}).get("tag") == CLAN_TAG:
                        # Pour s'assurer que c'est bien le bon round, comparons les tags si l'API le permet, 
                        # ou vérifions les participants. 
                        # Plus simple : si la guerre contient notre clan, regardons si elle appartient à ce round.
                        pass
                
                # Approche robuste : On parcourt directement toutes les guerres de la liste 'wars_cache' 
                # et on les associe par ordre chronologique si elles impliquent notre clan.
        
        # Solution directe et ultra-robuste basée sur les guerres de notre clan triées par date de début (startTime)
        my_clan_wars = []
        for w in wars_cache:
            if w and (w.get("clan", {}).get("tag") == CLAN_TAG or w.get("opponent", {}).get("tag") == CLAN_TAG):
                my_clan_wars.append(w)
        
        # Tri des guerres de notre clan par date de début pour l'ordre chronologique des 7 jours
        my_clan_wars = sorted(my_clan_wars, key=lambda x: x.get("startTime", ""))[:7]
        
        actual_days_columns = [f"Jour {i+1}" for i in range(len(my_clan_wars))]
        
        for day_idx, war in enumerate(my_clan_wars):
            day_col = actual_days_columns[day_idx]
            
            # Déterminer si notre clan est "clan" ou "opponent" dans cette instance de guerre
            side = "clan" if war.get("clan", {}).get("tag") == CLAN_TAG else "opponent"
            clan_info = war.get(side, {})
            
            for member in clan_info.get("members", []):
                name = member.get("name")
                if name not in member_attacks:
                    member_attacks[name] = {d: "⏳ Non jouée" for d in actual_days_columns}
                
                attacks = member.get("attacks", [])
                if attacks:
                    atk_details = []
                    for atk in attacks:
                        stars = atk.get("stars", 0)
                        destruction = atk.get("destructionPercentage", 0)
                        icon = "⭐" if stars > 0 else "❌"
                        atk_details.append(f"{icon} {stars}★ ({destruction}%)")
                    member_attacks[name][day_col] = " | ".join(atk_details)
                else:
                    member_attacks[name][day_col] = "⏳ Non jouée"

        if member_attacks:
            df_data = []
            for member_name, rounds in member_attacks.items():
                row = {"Membre": member_name}
                row.update(rounds)
                df_data.append(row)
                
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun participant trouvé pour cette ligue.")

    else:
        # Vue d'ensemble classique des joueurs et compositions
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
