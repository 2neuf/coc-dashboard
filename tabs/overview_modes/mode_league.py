import streamlit as st
import pandas as pd
from utils import get_all_archived_months, get_league_archive

def render_mode_league(accounts_dict, ordered_tags):
    st.subheader("⚔️ Suivi de la Ligue de Guerre de Clan (En cours)")
    
    league_data = st.session_state.get("cached_league_data", None)
    
    if not league_data or not league_data.get("wars"):
        st.info("⚠️ Aucune donnée de ligue en direct disponible pour ce clan (la ligue est peut-être terminée). Consultez les archives ci-dessous 👇")
        wars_cache = []
    else:
        wars_cache = league_data.get("wars", [])
        
    CLAN_TAG = "#2U0GCGPJU"
    
    account_order_map = {tag: idx for idx, tag in enumerate(ordered_tags)}
    
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

    if wars_cache:
        process_and_display_league(wars_cache)
        
    st.divider()

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
