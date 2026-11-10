import streamlit as st

# Quotas d'attaques fixés en dur selon le niveau de ligue
LEAGUE_ATTACK_QUOTAS = {
    "16": 10, "17": 10, "18": 10,
    "19": 14, "20": 14, "21": 14, "22": 14, "23": 14, "24": 14, "25": 14, "26": 14, "27": 14,
    "28": 14, "29": 14, "30": 14,
    "31": 18, "32": 18, "33": 18,
    "Légende 3": 24, "Légende 2": 30, "Légende 1": 56
}

def get_db_client():
    import os
    import libsql_client
    url = os.environ.get("TURSO_DATABASE_URL", "https://coc-dashboard-2neuf.aws-eu-west-1.turso.io")
    auth_token = os.environ.get("TURSO_AUTH_TOKEN", "")
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
    return libsql_client.create_client_sync(url=url, auth_token=auth_token, tls=True)

def render_mode_ranked():
    st.subheader("⚔️ Suivi des Ligues Classées Hebdomadaires")
    
    # 1. Récupération des comptes disponibles depuis la base de données
    try:
        conn = get_db_client()
        accounts_res = conn.execute("SELECT player_tag, name FROM accounts ORDER BY name ASC")
        accounts_list = [(row[0], row[1]) for row in accounts_res.rows]
    except Exception as e:
        st.error(f"Erreur lors de la récupération des comptes : {e}")
        accounts_list = []

    if not accounts_list:
        st.warning("⚠️ Aucun compte trouvé dans la base de données. Veuillez d'abord ajouter un compte dans l'application.")
        return

    # Sélection du compte
    account_dict = {f"{name} ({tag})": tag for tag, name in accounts_list}
    selected_account_label = st.selectbox("Sélectionner le compte", list(account_dict.keys()))
    selected_tag = account_dict[selected_account_label]

    # 2. Sélection du Mois et de la Semaine
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        selected_month = st.selectbox("Sélectionner le mois", ["Novembre", "Décembre", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre"])
    with col_m2:
        selected_week = st.selectbox("Sélectionner la semaine", ["Semaine 1", "Semaine 2", "Semaine 3", "Semaine 4", "Semaine 5"])

    week_key = f"{selected_month} - {selected_week}"

    # Vérification si des données existent déjà pour ce compte et cette période
    existing_data = None
    try:
        res = conn.execute("""
            SELECT status, league_level, attacks_done, attacks_max, stars_3, stars_2, stars_1, 
                   stars_0_details, stars_1_details, stars_2_details, avg_destruction, 
                   def_done, def_max, def_0_details, def_1_details, def_2_details, def_missing,
                   trophies_attack, trophies_defense
            FROM ranked_leagues 
            WHERE player_tag = ? AND week_key = ?
        """, [selected_tag, week_key])
        rows = res.rows if hasattr(res, 'rows') else []
        if rows:
            existing_data = rows[0]
    except Exception:
        pass

    # 3. Sélection du niveau de ligue
    league_levels = [str(i) for i in range(16, 34)] + ["Légende 3", "Légende 2", "Légende 1"]
    
    default_league_index = 0
    if existing_data and existing_data[1] in league_levels:
        default_league_index = league_levels.index(existing_data[1])

    selected_league = st.selectbox("Niveau de la ligue", league_levels, index=default_league_index)
    max_attacks_allowed = LEAGUE_ATTACK_QUOTAS.get(selected_league, 10)
    st.info(f"📌 Quota d'attaques défini pour la ligue **{selected_league}** : **{max_attacks_allowed} attaques** par semaine.")

    if not existing_data:
        st.info(f"📌 Aucune donnée enregistrée pour le compte **{selected_account_label}** sur la période : **{week_key}**.")
    else:
        st.success(f"✅ Données enregistrées existantes pour **{week_key}**. Vous pouvez les modifier et soumettre le formulaire pour mettre à jour.")

    # 4. Formulaire de saisie détaillée (Matchs Terminés)
    with st.form(key=f"form_ranked_complete_{selected_tag}_{week_key}"):
        st.markdown("### 🏹 Saisie détaillée des Attaques")
        
        col_atk1, col_atk2, col_atk3 = st.columns(3)
        with col_atk1:
            nb_0_star_atk = st.number_input("Nombre d'attaques à 0 ⭐", min_value=0, max_value=max_attacks_allowed, value=0, step=1)
        with col_atk2:
            nb_1_star_atk = st.number_input("Nombre d'attaques à 1 ⭐", min_value=0, max_value=max_attacks_allowed, value=0, step=1)
        with col_atk3:
            nb_2_star_atk = st.number_input("Nombre d'attaques à 2 ⭐", min_value=0, max_value=max_attacks_allowed, value=0, step=1)

        # Saisie dynamique des pourcentages exacts par attaque
        atk_0_percentages = []
        if nb_0_star_atk > 0:
            st.markdown("##### Pourcentages exacts (0 ⭐)")
            cols_0 = st.columns(min(nb_0_star_atk, 4))
            for i in range(nb_0_star_atk):
                with cols_0[i % len(cols_0)]:
                    p = st.number_input(f"Atk 0⭐ #{i+1} (%)", min_value=0.0, max_value=99.9, value=0.0, step=0.1, key=f"atk_0_{i}")
                    atk_0_percentages.append(p)

        atk_1_percentages = []
        if nb_1_star_atk > 0:
            st.markdown("##### Pourcentages exacts (1 ⭐)")
            cols_1 = st.columns(min(nb_1_star_atk, 4))
            for i in range(nb_1_star_atk):
                with cols_1[i % len(cols_1)]:
                    p = st.number_input(f"Atk 1⭐ #{i+1} (%)", min_value=0.0, max_value=99.9, value=50.0, step=0.1, key=f"atk_1_{i}")
                    atk_1_percentages.append(p)

        atk_2_percentages = []
        if nb_2_star_atk > 0:
            st.markdown("##### Pourcentages exacts (2 ⭐)")
            cols_2 = st.columns(min(nb_2_star_atk, 4))
            for i in range(nb_2_star_atk):
                with cols_2[i % len(cols_2)]:
                    p = st.number_input(f"Atk 2⭐ #{i+1} (%)", min_value=0.0, max_value=99.9, value=80.0, step=0.1, key=f"atk_2_{i}")
                    atk_2_percentages.append(p)

        total_declared_atk = nb_0_star_atk + nb_1_star_atk + nb_2_star_atk
        if total_declared_atk > max_attacks_allowed:
            st.error(f"⚠️ Le nombre total d'attaques déclarées ({total_declared_atk}) dépasse le quota maximal autorisé pour cette ligue ({max_attacks_allowed}).")

        nb_3_star_atk = max(0, max_attacks_allowed - total_declared_atk)
        st.info(f"💡 Attaques restantes déduites automatiquement en **3 ⭐** : **{nb_3_star_atk} attaques** (sur un total de {max_attacks_allowed}).")

        st.markdown("---")
        st.markdown("### 🛡️ Saisie détaillée des Défenses")

        col_def1, col_def2, col_def3 = st.columns(3)
        with col_def1:
            nb_0_star_def = st.number_input("Nombre de défenses à 0 ⭐ (subies)", min_value=0, value=0, step=1)
        with col_def2:
            nb_1_star_def = st.number_input("Nombre de défenses à 1 ⭐ (subies)", min_value=0, value=0, step=1)
        with col_def3:
            nb_2_star_def = st.number_input("Nombre de défenses à 2 ⭐ (subies)", min_value=0, value=0, step=1)

        # Pourcentages et trophées pour les défenses
        def_0_percentages = []
        def_0_trophies = []
        if nb_0_star_def > 0:
            st.markdown("##### Détails des défenses 0 ⭐ (pourcentage et trophées gagnés)")
            for i in range(nb_0_star_def):
                c1, c2 = st.columns(2)
                with c1:
                    p = st.number_input(f"Def 0⭐ #{i+1} (%)", min_value=0.0, max_value=99.9, value=30.0, key=f"def_0_p_{i}")
                    def_0_percentages.append(p)
                with c2:
                    t = st.number_input(f"Trophées Def 0⭐ #{i+1}", min_value=0, value=5, key=f"def_0_t_{i}")
                    def_0_trophies.append(t)

        def_1_percentages = []
        def_1_trophies = []
        if nb_1_star_def > 0:
            st.markdown("##### Détails des défenses 1 ⭐ (pourcentage et trophées)")
            for i in range(nb_1_star_def):
                c1, c2 = st.columns(2)
                with c1:
                    p = st.number_input(f"Def 1⭐ #{i+1} (%)", min_value=0.0, max_value=99.9, value=60.0, key=f"def_1_p_{i}")
                    def_1_percentages.append(p)
                with c2:
                    t = st.number_input(f"Trophées Def 1⭐ #{i+1}", min_value=0, value=0, key=f"def_1_t_{i}")
                    def_1_trophies.append(t)

        def_2_percentages = []
        def_2_trophies = []
        if nb_2_star_def > 0:
            st.markdown("##### Détails des défenses 2 ⭐ (pourcentage et trophées)")
            for i in range(nb_2_star_def):
                c1, c2 = st.columns(2)
                with c1:
                    p = st.number_input(f"Def 2⭐ #{i+1} (%)", min_value=0.0, max_value=100.0, value=90.0, key=f"def_2_p_{i}")
                    def_2_percentages.append(p)
                with c2:
                    t = st.number_input(f"Trophées Def 2⭐ #{i+1}", min_value=-50, max_value=0, value=-10, key=f"def_2_t_{i}")
                    def_2_trophies.append(t)

        st.markdown("##### Gestion des défenses non reçues (Trophées manquants)")
        total_def_expected = st.number_input("Nombre total de défenses théoriques attendues", min_value=0, value=max_attacks_allowed, step=1)
        total_def_received = st.number_input("Nombre de défenses réellement reçues et jouées", min_value=0, value=nb_0_star_def + nb_1_star_def + nb_2_star_def, step=1)

        submit_button = st.form_submit_button(label="💾 Enregistrer les résultats de la ligue")

        if submit_button:
            if total_declared_atk > max_attacks_allowed:
                st.error("Erreur : Impossible d'enregistrer, le nombre d'attaques déclarées dépasse le quota.")
                return

            # Calculs automatiques
            all_received_trophies = def_0_trophies + def_1_trophies + def_2_trophies
            sum_received_trophies = sum(all_received_trophies)
            
            if total_def_received > 0:
                avg_trophies_per_def = sum_received_trophies / total_def_received
            else:
                avg_trophies_per_def = 0.0

            missing_defs = max(0, total_def_expected - total_def_received)
            adjusted_defense_trophies = sum_received_trophies + (missing_defs * avg_trophies_per_def)

            all_atk_percentages = atk_0_percentages + atk_1_percentages + atk_2_percentages + ([100.0] * nb_3_star_atk)
            avg_destruction = sum(all_atk_percentages) / len(all_atk_percentages) if all_atk_percentages else 0.0

            import json
            try:
                conn.execute("""
                    INSERT INTO ranked_leagues (
                        player_tag, week_key, status, league_level, attacks_done, attacks_max, 
                        stars_3, stars_2, stars_1, stars_0_details, stars_1_details, stars_2_details, 
                        avg_destruction, def_done, def_max, def_missing, trophies_attack, trophies_defense
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(player_tag, week_key) DO UPDATE SET 
                        status = excluded.status,
                        league_level = excluded.league_level,
                        attacks_done = excluded.attacks_done,
                        attacks_max = excluded.attacks_max,
                        stars_3 = excluded.stars_3,
                        stars_2 = excluded.stars_2,
                        stars_1 = excluded.stars_1,
                        stars_0_details = excluded.stars_0_details,
                        stars_1_details = excluded.stars_1_details,
                        stars_2_details = excluded.stars_2_details,
                        avg_destruction = excluded.avg_destruction,
                        def_done = excluded.def_done,
                        def_max = excluded.def_max,
                        def_missing = excluded.def_missing,
                        trophies_attack = excluded.trophies_attack,
                        trophies_defense = excluded.trophies_defense
                """, [
                    selected_tag, week_key, "Terminé", selected_league, max_attacks_allowed, max_attacks_allowed,
                    nb_3_star_atk, nb_2_star_atk, nb_1_star_atk,
                    json.dumps(atk_0_percentages), json.dumps(atk_1_percentages), json.dumps(atk_2_percentages),
                    avg_destruction, total_def_received, total_def_expected, missing_defs,
                    0, adjusted_defense_trophies
                ])
                st.success(f"🎉 Résultats enregistrés avec succès pour **{selected_account_label}** ({week_key}) !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de l'enregistrement en base de données : {e}")

    # 5. Affichage récapitulatif si les données existent déjà
    if existing_data:
        st.markdown("---")
        st.markdown(f"### 📊 Bilan enregistré pour {week_key}")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Niveau de Ligue", existing_data[1])
        with c2:
            st.metric("Attaques max", existing_data[3])
        with c3:
            st.metric("Destruction Moy.", f"{existing_data[10]:.1f}%")
        with c4:
            st.metric("Défenses manq. ajustées", f"{existing_data[18]:+.1f} trophées")
