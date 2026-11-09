import streamlit as st
import pandas as pd
from utils import get_db_client, init_ranked_leagues_table

def render_mode_ranked(db_accounts, accounts_dict, ordered_tags):
    st.subheader("🏆 Suivi des Ligues Classées Hebdomadaires")
    
    init_ranked_leagues_table()
    conn = get_db_client()
    
    current_week = st.selectbox(
        "Sélectionner la semaine / période", 
        ["Semaine 1 - Novembre", "Semaine 2 - Novembre", "Semaine 3 - Novembre", "Semaine 4 - Novembre"], 
        index=0
    )
    
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
