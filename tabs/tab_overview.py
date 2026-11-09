import streamlit as st
import pandas as pd
from utils import (
    get_db_client, 
    update_account_composition, 
    get_all_archived_months, 
    get_league_archive,
    init_ranked_leagues_table
)

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
    account_order_map = {tag: idx for idx, tag in enumerate(ordered_tags)}

    if overview_mode == "⚔️ Ligue Overview":
        st.subheader("⚔️ Suivi de la Ligue de Guerre de Clan (En cours)")
        
        league_data = st.session_state.get("cached_league_data", None)
        
        if not league_data or not league_data.get("wars"):
            st.info("⚠️ Aucune donnée de ligue en direct disponible pour ce clan (la ligue est peut-être terminée). Consultez les archives ci-dessous 👇")
            wars_cache = []
        else:
            wars_cache = league_data.get("wars", [])
            
        CLAN_TAG = "#2U0GCGPJU"
        
        def process_and_display_league(wars_list, title_suffix=""):
            my_clan_wars = []
            for w in wars_list:
                if w and (w.get("clan", {}).get("tag") == CLAN_TAG or w.get("opponent", {}).get("tag") == CLAN_TAG):
                    my_clan_wars.append(w)
            
            my_clan_wars = sorted(my_clan_wars, key=lambda x: x.get("startTime", ""))[:7]
            if not my_clan_wars:
                st.info(f"Aucune guerre trouvée {title_suffix}.")
                return
                
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
                            "days": {d: "⏳ Non jouée" for d in actual_days_columns},
                            "total_stars": 0,
                            "total_destruction": 0.0,
                            "attacks_count": 0
                        }
                    else:
                        players_data[p_tag]["name"] = p_name
                    
                    attacks = member.get("attacks", [])
                    if attacks:
                        atk_details = []
                        for atk in attacks:
                            stars = atk.get("stars", 0)
                            destruction = atk.get("destructionPercentage", 0.0)
                            
                            players_data[p_tag]["total_stars"] += stars
                            players_data[p_tag]["total_destruction"] += destruction
                            players_data[p_tag]["attacks_count"] += 1
                            
                            icon = "⭐" if stars > 0 else "❌"
                            atk_details.append(f"{icon} {stars}★ ({destruction}%)")
                        players_data[p_tag]["days"][day_col] = " | ".join(atk_details)

            if players_data:
                sorted_p_tags = sorted(players_data.keys(), key=lambda t: account_order_map.get(t, 999))
                df_rows = []
                for p_tag in sorted_p_tags:
                    info = players_data[p_tag]
                    row = {"Membre": info["name"]}
                    row.update(info["days"])
                    
                    t_stars = info["total_stars"]
                    t_dest = info["total_destruction"]
                    atk_cnt = info["attacks_count"]
                    
                    avg_stars = round(t_stars / atk_cnt, 2) if atk_cnt > 0 else 0.0
                    avg_dest = round(t_dest / atk_cnt, 1) if atk_cnt > 0 else 0.0
                    
                    row["Total"] = f"⭐ {t_stars} | 💥 {round(t_dest, 1)}% (Moy: {avg_stars}★ / {avg_dest}%)"
                    df_rows.append(row)
                    
                df = pd.DataFrame(df_rows)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Aucun participant trouvé.")

        # Affichage du tableau en direct si disponible
        if wars_cache:
            process_and_display_league(wars_cache)
            
        st.divider()

        # Bloc dépliable par mois pour les archives
        st.subheader("📂 Archives des Ligues")
        archived_months = get_all_archived_months()
        
        if archived_months:
            for month in archived_months:
                with st.expander(f"📅 Ligue du mois de **{month}**"):
                    archived_wars = get_league_archive(month)
                    if archived_wars:
                        process_and_display_league(archived_wars, f"pour le mois de {month}")
                    else:
                        st.info(f"Aucune donnée enregistrée pour {month}.")
        else:
            st.caption("Aucune archive disponible pour le moment.")

    elif overview_mode == "🏆 Ligues Classées":
        st.subheader("🏆 Suivi des Ligues Classées Hebdomadaires")
        
        init_ranked_leagues_table()
        
        # Sélection de la semaine
        current_week = st.selectbox(
            "Sélectionner la semaine / période", 
            ["Semaine 1 - Novembre", "Semaine 2 - Novembre", "Semaine 3 - Novembre", "Semaine 4 - Novembre"], 
            index=0
        )
        
        # Récupération des données enregistrées pour cette semaine
        ranked_res = conn.execute(
            "SELECT player_tag, status, attacks_done, attacks_max, stars_3, stars_2, stars_1, avg_destruction, def_done, def_max, trophies_attack, trophies_defense FROM ranked_leagues WHERE week_key = ?", 
            [current_week]
        )
        ranked_data_map = {row[0]: row for row in ranked_res.rows}
        
        table_rows = []
        for tag in ordered_tags:
            acc = accounts_dict.get(tag)
            if not acc:
                continue
            name, th = acc[1], acc[2]
            
            # Valeurs par défaut si non saisies
            r_data = ranked_data_map.get(tag, ("En cours", 0, 8, 0, 0, 0, 0.0, 0, 8, 0, 0))
            status, atk_done, atk_max, s3, s2, s1, avg_dest, def_done, def_max, t_atk, t_def = r_data[1], r_data[2], r_data[3], r_data[4], r_data[5], r_data[6], r_data[7], r_data[8], r_data[9], r_data[10], r_data[11]
            
            total_trophies = t_atk + t_def
            avg_def_trophies = round(t_def / def_done, 1) if def_done > 0 else 0.0
            
            table_rows.append({
                "Tag": tag,
                "Pseudo": name,
                "Ligue": f"TH {th}",
                "Statut": status,
                "Attaque": f"{atk_done}/{atk_max} atk | ⭐ {s3}x3★, {s2}x2★, {s1}x1★ | Moy. 💥 {avg_dest}% | Trophées Atk: {t_atk}",
                "Défense": f"{def_done}/{def_max} def | Trophées Def: {t_def} (Moy: {avg_def_trophies})",
                "Classement": f"🏆 {total_trophies} trophées"
            })
            
        if table_rows:
            df_ranked = pd.DataFrame(table_rows)
            st.dataframe(df_ranked.drop(columns=["Tag"]), use_container_width=True, hide_index=True)
            
            st.divider()
            st.markdown("### ✍️ Saisie manuelle des résultats de la semaine")
            
            selected_account_name = st.selectbox("Choisir le compte à modifier", [acc[1] for acc in db_accounts], key="ranked_edit_account")
            selected_tag = next(acc[0] for acc in db_accounts if acc[1] == selected_account_name)
            
            current_r = ranked_data_map.get(selected_tag, ("En cours", 0, 8, 0, 0, 0, 0.0, 0, 8, 0, 0))
            
            with st.form(key="form_edit_ranked"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    status_options = ["En cours", f"Prévu pour {current_week}", "Terminé (Semaine dernière)"]
                    default_status_idx = 0 if current_r[1] == "En cours" else (1 if "Prévu" in current_r[1] else 2)
                    new_status = st.selectbox("Statut", status_options, index=min(default_status_idx, len(status_options)-1))
                    
                    new_atk_done = st.number_input("Attaques réalisées", min_value=0, max_value=20, value=int(current_r[2]))
                    new_atk_max = st.number_input("Attaques max hebdomadaires", min_value=1, max_value=20, value=int(current_r[3]))
                
                with col2:
                    new_s3 = st.number_input("Nombre de 3 étoiles", min_value=0, value=int(current_r[4]))
                    new_s2 = st.number_input("Nombre de 2 étoiles", min_value=0, value=int(current_r[5]))
                    new_s1 = st.number_input("Nombre de 1 étoile", min_value=0, value=int(current_r[6]))
                    new_avg_dest = st.number_input("Pourcentage de destruction moyen (%)", min_value=0.0, max_value=100.0, value=float(current_r[7]))
                    new_t_atk = st.number_input("Trophées obtenus en Attaque", value=int(current_r[10]))
                
                with col3:
                    new_def_done = st.number_input("Défenses subies (attaques contre village)", min_value=0, max_value=20, value=int(current_r[8]))
                    new_def_max = st.number_input("Défenses max hebdomadaires", min_value=1, max_value=20, value=int(current_r[9]))
                    new_t_def = st.number_input("Trophées obtenus en Défense", value=int(current_r[11]))
                    
                if st.form_submit_button("💾 Enregistrer les modifications pour ce compte", type="primary"):
                    conn.execute("""
                        INSERT INTO ranked_leagues (player_tag, week_key, status, attacks_done, attacks_max, stars_3, stars_2, stars_1, avg_destruction, def_done, def_max, trophies_attack, trophies_defense)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(player_tag, week_key) DO UPDATE SET
                            status = excluded.status,
                            attacks_done = excluded.attacks_done,
                            attacks_max = excluded.attacks_max,
                            stars_3 = excluded.stars_3,
                            stars_2 = excluded.stars_2,
                            stars_1 = excluded.stars_1,
                            avg_destruction = excluded.avg_destruction,
                            def_done = excluded.def_done,
                            def_max = excluded.def_max,
                            trophies_attack = excluded.trophies_attack,
                            trophies_defense = excluded.trophies_defense
                    """, [selected_tag, current_week, new_status, new_atk_done, new_atk_max, new_s3, new_s2, new_s1, new_avg_dest, new_def_done, new_def_max, new_t_atk, new_t_def])
                    st.success(f"✅ Résultats de ligue classée mis à jour pour **{selected_account_name}** !")
                    st.rerun()
        else:
            st.info("Aucun compte disponible.")

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
