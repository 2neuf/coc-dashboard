import json
import os
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
LEAGUE_ATTACK_QUOTAS = {
    "16": 10, "17": 10, "18": 10,
    "19": 14, "20": 14, "21": 14, "22": 14, "23": 14, "24": 14, "25": 14, "26": 14, "27": 14,
    "28": 14, "29": 14, "30": 14,
    "31": 18, "32": 18, "33": 18,
    "Légende 3": 24, "Légende 2": 30, "Légende 1": 56,
}
LEAGUE_LEVELS = [str(i) for i in range(16, 34)] + ["Légende 3", "Légende 2", "Légende 1"]
MONTHS = ["Novembre", "Décembre", "Janvier", "Février", "Mars", "Avril",
          "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre"]
WEEKS = [f"Semaine {i}" for i in range(1, 6)]

COLUMNS = [
    "player_tag", "week_key", "status", "league_level", "attacks_done", "attacks_max",
    "stars_3", "stars_2", "stars_1", "stars_0_details", "stars_1_details", "stars_2_details",
    "avg_destruction", "def_done", "def_max", "def_0_details", "def_1_details", "def_2_details",
    "def_missing", "trophies_attack", "trophies_defense", "tracking_mode"
]
NUM_COLS = ["attacks_done", "attacks_max", "stars_3", "stars_2", "stars_1", "avg_destruction",
            "def_done", "def_max", "def_missing", "trophies_attack", "trophies_defense"]


# ---------------------------------------------------------------------------
# Base de données (Turso)
# ---------------------------------------------------------------------------
def get_db_client():
    import libsql_client
    url = os.environ.get("TURSO_DATABASE_URL", "https://coc-dashboard-2neuf.aws-eu-west-1.turso.io")
    auth_token = os.environ.get("TURSO_AUTH_TOKEN", "")
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
    return libsql_client.create_client_sync(url=url, auth_token=auth_token, tls=True)


def ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ranked_leagues (
            player_tag TEXT NOT NULL,
            week_key TEXT NOT NULL,
            status TEXT,
            league_level TEXT,
            attacks_done INTEGER,
            attacks_max INTEGER,
            stars_3 INTEGER,
            stars_2 INTEGER,
            stars_1 INTEGER,
            stars_0_details TEXT,
            stars_1_details TEXT,
            stars_2_details TEXT,
            avg_destruction REAL,
            def_done INTEGER,
            def_max INTEGER,
            def_0_details TEXT,
            def_1_details TEXT,
            def_2_details TEXT,
            def_missing INTEGER,
            trophies_attack REAL,
            trophies_defense REAL,
            tracking_mode TEXT DEFAULT 'Globale',
            PRIMARY KEY (player_tag, week_key)
        )
    """)
    col_types = {
        "status": "TEXT", "league_level": "TEXT", "attacks_done": "INTEGER", "attacks_max": "INTEGER",
        "stars_3": "INTEGER", "stars_2": "INTEGER", "stars_1": "INTEGER",
        "stars_0_details": "TEXT", "stars_1_details": "TEXT", "stars_2_details": "TEXT",
        "avg_destruction": "REAL", "def_done": "INTEGER", "def_max": "INTEGER",
        "def_0_details": "TEXT", "def_1_details": "TEXT", "def_2_details": "TEXT",
        "def_missing": "INTEGER", "trophies_attack": "REAL", "trophies_defense": "REAL",
        "tracking_mode": "TEXT",
    }
    res = conn.execute("SELECT name FROM pragma_table_info('ranked_leagues')")
    present = {row[0] for row in res.rows}
    for col, col_type in col_types.items():
        if col not in present:
            conn.execute(f"ALTER TABLE ranked_leagues ADD COLUMN {col} {col_type}")

    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_ranked_tag_week "
            "ON ranked_leagues(player_tag, week_key)"
        )
    except Exception:
        pass


def _rows_to_dicts(res):
    rows = res.rows if hasattr(res, "rows") else []
    return [{col: row[i] for i, col in enumerate(COLUMNS)} for row in rows]


def fetch_ranked(conn, tag=None, week_key=None):
    query = f"SELECT {', '.join(COLUMNS)} FROM ranked_leagues"
    clauses, params = [], []
    if tag is not None:
        clauses.append("player_tag = ?")
        params.append(tag)
    if week_key is not None:
        clauses.append("week_key = ?")
        params.append(week_key)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    return _rows_to_dicts(conn.execute(query, params))


def _loads(value, default):
    try:
        return json.loads(value) if value else default
    except (TypeError, ValueError):
        return default


def _week_order(week_key):
    try:
        month, week = week_key.split(" - ")
        return MONTHS.index(month) * 10 + int(week.split()[-1])
    except (ValueError, IndexError):
        return 999


# ---------------------------------------------------------------------------
# Calculs Automatiques des Trophées et Statistiques
# ---------------------------------------------------------------------------
def calculate_attack_trophies(stars, destruction_pct, is_global=False):
    if is_global:
        if stars == 3:
            return 40
        elif stars == 2:
            return 28
        elif stars == 1:
            return 13
        elif stars == 0:
            return 4
        return 0
    else:
        if stars == 3:
            return 40
        elif stars == 2:
            extra = max(0, destruction_pct - 50)
            return 16 + int(extra // 3)
        elif stars == 1:
            return 4 + int(destruction_pct // 8)
        elif stars == 0:
            return int(destruction_pct // 10)
        return 0


def calculate_defense_trophies(stars, destruction_pct, is_global=False):
    return 40 - calculate_attack_trophies(stars, destruction_pct, is_global)


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
def render_mode_ranked():
    st.subheader("⚔️ Ligues Classées")

    try:
        conn = get_db_client()
        ensure_table(conn)
        res = conn.execute("SELECT player_tag, name FROM accounts ORDER BY display_order ASC, name ASC")
        accounts = [(row[0], row[1]) for row in res.rows]
    except Exception as e:
        st.error(f"Erreur d'accès à la base de données : {e}")
        return

    try:
        if not accounts:
            st.warning("⚠️ Aucun compte en base. Ajoute d'abord un compte dans l'application.")
            return

        tab_overview, tab_form = st.tabs(["📊 Vue d'ensemble & Ongoing", "📝 Saisie Avancée a posteriori"])
        with tab_overview:
            render_overview(conn, accounts)
        with tab_form:
            render_form(conn, accounts)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Vue d'ensemble & Mode Ongoing interactif
# ---------------------------------------------------------------------------
def render_overview(conn, accounts):
    st.markdown("### ⚡ Mode Ongoing (Suivi en direct) & Vue Globale")

    # Sélection de la semaine active pour le mode ongoing
    c_m, c_w = st.columns(2)
    sel_month = c_m.selectbox("Mois actif", MONTHS, key="ongoing_month")
    sel_week = c_w.selectbox("Semaine active", WEEKS, key="ongoing_week")
    current_week_key = f"{sel_month} - {sel_week}"

    try:
        rows = fetch_ranked(conn, week_key=current_week_key)
    except Exception as e:
        st.error(f"Erreur de lecture des ligues : {e}")
        return
    
    df_week = pd.DataFrame(rows) if rows else pd.DataFrame(columns=COLUMNS)

    st.markdown(f"#### 📋 Semaine : `{current_week_key}`")
    st.info("💡 Utilisez les boutons `+` pour ajouter vos attaques et défenses en direct. Choisissez le mode **Globale** (estimation automatique rapide) ou **Précis** (avec pourcentage exact).")

    for tag, name in accounts:
        # Récupérer ou initialiser les données pour ce joueur/cette semaine
        acc_row = df_week[df_week["player_tag"] == tag]
        
        if acc_row.empty:
            league = "18"
            status = "En cours"
            attacks_done = 0
            attacks_max = LEAGUE_ATTACK_QUOTAS[league]
            s3, s2, s1 = 0, 0, 0
            s0_list = []
            s1_list = []
            s2_list = []
            avg_dest = 0.0
            t_atk = 0.0
            def_done = 0
            def_max = quota = attacks_max
            d0_list, d1_list, d2_list = [], [], []
            t_def = 0.0
            tracking_mode = "Globale"
        else:
            r = acc_row.iloc[0]
            league = r.get("league_level", "18")
            status = r.get("status", "En cours")
            attacks_done = int(r.get("attacks_done", 0) or 0)
            attacks_max = int(r.get("attacks_max", LEAGUE_ATTACK_QUOTAS.get(league, 14)) or 14)
            s3 = int(r.get("stars_3", 0) or 0)
            s2 = int(r.get("stars_2", 0) or 0)
            s1 = int(r.get("stars_1", 0) or 0)
            s0_list = _loads(r.get("stars_0_details"), [])
            s1_list = _loads(r.get("stars_1_details"), [])
            s2_list = _loads(r.get("stars_2_details"), [])
            avg_dest = float(r.get("avg_destruction", 0.0) or 0.0)
            t_atk = float(r.get("trophies_attack", 0.0) or 0.0)
            def_done = int(r.get("def_done", 0) or 0)
            def_max = int(r.get("def_max", attacks_max) or attacks_max)
            d0_data = _loads(r.get("def_0_details"), {})
            d1_data = _loads(r.get("def_1_details"), {})
            d2_data = _loads(r.get("def_2_details"), {})
            d0_list = d0_data.get("pct", []) if isinstance(d0_data, dict) else d0_data
            d1_list = d1_data.get("pct", []) if isinstance(d1_data, dict) else d1_data
            d2_list = d2_data.get("pct", []) if isinstance(d2_data, dict) else d2_data
            t_def = float(r.get("trophies_defense", 0.0) or 0.0)
            tracking_mode = r.get("tracking_mode", "Globale") or "Globale"

        quota = LEAGUE_ATTACK_QUOTAS.get(league, 14)
        s0_count = len(s0_list)
        total_attacks_recorded = s3 + s2 + s1 + s0_count
        total_trophies = t_atk + t_def

        # Conteneur visuel par joueur
        with st.container():
            st.markdown(f"---")
            cols = st.columns([1.5, 1.5, 1.2, 1.8, 1.2, 1.2, 1.2, 1.2, 1.2, 1.5])
            
            # 1. Mode de suivi (Globale / Précis)
            with cols[0]:
                new_mode = st.selectbox("Mode", ["Globale", "Précis"], index=0 if tracking_mode == "Globale" else 1, key=f"mode_{tag}_{current_week_key}")
                if new_mode != tracking_mode:
                    _save_field(conn, tag, current_week_key, tracking_mode=new_mode)
                    st.rerun()

            # 2. Pseudo et Changement direct de Ligue
            with cols[1]:
                st.markdown(f"**{name}**")
                new_league = st.selectbox("Ligue", LEAGUE_LEVELS, index=LEAGUE_LEVELS.index(league) if league in LEAGUE_LEVELS else 0, key=f"lg_{tag}_{current_week_key}")
                if new_league != league:
                    new_quota = LEAGUE_ATTACK_QUOTAS.get(new_league, 14)
                    _save_field(conn, tag, current_week_key, league_level=new_league, attacks_max=new_quota, def_max=new_quota)
                    st.rerun()

            # 3. Attaques faites / max
            with cols[2]:
                st.markdown(f"**Atk:** {total_attacks_recorded}/{quota}")
                st.markdown(f"**Destr:** {avg_dest:.1f}%")

            # 4. Boutons d'attaque (+3⭐, +2⭐, +1⭐, +0⭐)
            with cols[3]:
                st.caption("Ajout Attaque")
                bc3, bc2, bc1, bc0 = st.columns(4)
                if bc3.button("3⭐+", key=f"a3_{tag}"):
                    _add_attack(conn, tag, current_week_key, 3, 100.0, new_mode)
                    st.rerun()
                if bc2.button("2⭐+", key=f"a2_{tag}"):
                    if new_mode == "Globale":
                        _add_attack(conn, tag, current_week_key, 2, 75.0, new_mode)
                        st.rerun()
                    else:
                        st.session_state[f"prompt_atk_{tag}"] = 2
                if bc1.button("1⭐+", key=f"a1_{tag}"):
                    if new_mode == "Globale":
                        _add_attack(conn, tag, current_week_key, 1, 50.0, new_mode)
                        st.rerun()
                    else:
                        st.session_state[f"prompt_atk_{tag}"] = 1
                if bc0.button("0⭐+", key=f"a0_{tag}"):
                    if new_mode == "Globale":
                        _add_attack(conn, tag, current_week_key, 0, 20.0, new_mode)
                        st.rerun()
                    else:
                        st.session_state[f"prompt_atk_{tag}"] = 0

            # Compteurs d'étoiles actuels
            with cols[4]:
                st.metric("3⭐", s3)
            with cols[5]:
                st.metric("2⭐", s2)
            with cols[6]:
                st.metric("1⭐", s1)
            with cols[7]:
                st.metric("0⭐", s0_count)

            # Trophées Attaque & Défense
            with cols[8]:
                st.metric("Atk Tr.", f"{t_atk:+.0f}")
                st.metric("Déf Tr.", f"{t_def:+.0f}")

            with cols[9]:
                st.metric("Total", f"{total_trophies:+.0f}")
                def_recv = def_done
                st.caption(f"Déf: {def_recv}/{quota}")

            # Gestion du prompt pour le mode Précis (pourcentage requis)
            if st.session_state.get(f"prompt_atk_{tag}") is not None:
                star_val = st.session_state[f"prompt_atk_{tag}"]
                with st.form(key=f"form_precise_atk_{tag}"):
                    st.markdown(f"🎯 **Mode Précis** : Entrez le % de destruction pour l'attaque à **{star_val} ⭐**")
                    max_limit = 49 if star_val == 0 else (99 if star_val in [1, 2] else 100)
                    min_limit = 0 if star_val == 0 else (1 if star_val == 1 else 50)
                    pct_val = st.number_input("Pourcentage (%)", min_value=min_limit, max_value=max_limit, value=min_limit)
                    if st.form_submit_button("Valider l'attaque"):
                        _add_attack(conn, tag, current_week_key, star_val, float(pct_val), "Précis")
                        st.session_state.pop(f"prompt_atk_{tag}", None)
                        st.rerun()


# ---------------------------------------------------------------------------
# Fonctions d'aide à la mise à jour en direct (Ongoing)
# ---------------------------------------------------------------------------
def _save_field(conn, tag, week_key, **kwargs):
    existing = fetch_ranked(conn, tag, week_key)
    if not existing:
        # Créer la ligne de base
        conn.execute("""
            INSERT INTO ranked_leagues (player_tag, week_key, status, league_level, attacks_max, def_max, tracking_mode, trophies_attack, trophies_defense, avg_destruction, stars_3, stars_2, stars_1)
            VALUES (?, ?, 'En cours', '18', 14, 14, 'Globale', 0.0, 0.0, 0.0, 0, 0, 0)
        """, [tag, week_key])
    
    set_clauses = []
    vals = []
    for k, v in kwargs.items():
        set_clauses.append(f"{k} = ?")
        vals.append(v)
    vals.extend([tag, week_key])
    
    conn.execute(f"UPDATE ranked_leagues SET {', '.join(set_clauses)} WHERE player_tag = ? AND week_key = ?", vals)


def _add_attack(conn, tag, week_key, stars, destruction_pct, mode):
    existing = fetch_ranked(conn, tag, week_key)
    if not existing:
        # Initialiser
        conn.execute("""
            INSERT INTO ranked_leagues (player_tag, week_key, status, league_level, attacks_max, def_max, tracking_mode, trophies_attack, trophies_defense, avg_destruction, stars_3, stars_2, stars_1, stars_0_details, stars_1_details, stars_2_details)
            VALUES (?, ?, 'En cours', '18', 14, 14, ?, 0.0, 0.0, 0.0, 0, 0, 0, '[]', '[]', '[]')
        """, [tag, week_key, mode])
        existing = fetch_ranked(conn, tag, week_key)

    r = existing[0]
    s3 = int(r.get("stars_3", 0) or 0)
    s2 = int(r.get("stars_2", 0) or 0)
    s1 = int(r.get("stars_1", 0) or 0)
    s0_list = _loads(r.get("stars_0_details"), [])
    s1_list = _loads(r.get("stars_1_details"), [])
    s2_list = _loads(r.get("stars_2_details"), [])

    is_glob = (mode == "Globale")
    t_add = calculate_attack_trophies(stars, destruction_pct, is_glob)
    curr_t_atk = float(r.get("trophies_attack", 0.0) or 0.0)
    new_t_atk = curr_t_atk + t_add

    # Mettre à jour les compteurs
    if stars == 3:
        s3 += 1
        destruction_pct = 100.0
    elif stars == 2:
        s2 += 1
        s2_list.append(destruction_pct)
    elif stars == 1:
        s1 += 1
        s1_list.append(destruction_pct)
    elif stars == 0:
        s0_list.append(destruction_pct)

    # Recalculer la destruction moyenne
    all_pcts = s0_list + s1_list + s2_list + ([100.0] * s3 * len(s3 * [100.0]) if s3 > 0 else []) # simple aggregation
    # Recalcul précis de la liste globale de destruction
    flat_pcts = s0_list + s1_list + s2_list + ([100.0] * s3)
    avg_dest = sum(flat_pcts) / len(flat_pcts) if flat_pcts else 0.0
    attacks_done = len(flat_pcts)

    conn.execute("""
        UPDATE ranked_leagues SET
            stars_3 = ?, stars_2 = ?, stars_1 = ?,
            stars_0_details = ?, stars_1_details = ?, stars_2_details = ?,
            attacks_done = ?, avg_destruction = ?, trophies_attack = ?, tracking_mode = ?
        WHERE player_tag = ? AND week_key = ?
    """, [
        s3, s2, s1,
        json.dumps(s0_list), json.dumps(s1_list), json.dumps(s2_list),
        attacks_done, round(avg_dest, 2), new_t_atk, mode,
        tag, week_key
    ])


# ---------------------------------------------------------------------------
# Formulaire "ligue terminée" (Saisie Avancée a posteriori)
# ---------------------------------------------------------------------------
def _pct_inputs(title, n, prefill, default, max_value, key):
    values = []
    if n <= 0:
        return values
    st.markdown(f"##### {title}")
    cols = st.columns(min(n, 4))
    for i in range(n):
        start = prefill[i] if i < len(prefill) else default
        with cols[i % len(cols)]:
            values.append(st.number_input(
                f"#{i + 1} (%)", min_value=0, max_value=max_value,
                value=min(start, max_value), step=1, key=f"{key}_{i}",
            ))
    return values


def _def_inputs_pct_only(title, n, prefill_list, default_pct, max_pct, key):
    pcts = []
    if n <= 0:
        return pcts
    st.markdown(f"##### {title}")
    cols = st.columns(min(n, 4))
    for i in range(n):
        start = prefill_list[i] if i < len(prefill_list) else default_pct
        with cols[i % len(cols)]:
            pcts.append(st.number_input(
                f"Déf #{i + 1} (%)", min_value=0, max_value=max_pct,
                value=min(start, max_pct), step=1, key=f"{key}_p_{i}",
            ))
    return pcts


def render_form(conn, accounts):
    flash = st.session_state.pop("ranked_flash", None)
    if flash:
        st.success(flash)

    labels = {f"{name} ({tag})": tag for tag, name in accounts}
    label = st.selectbox("Compte", list(labels), key="rk_form_account_post")
    tag = labels[label]

    c1, c2 = st.columns(2)
    month = c1.selectbox("Mois", MONTHS, key="rk_form_month_post")
    week = c2.selectbox("Semaine", WEEKS, key="rk_form_week_post")
    week_key = f"{month} - {week}"
    k = f"{tag}_{week_key}_post"

    found = fetch_ranked(conn, tag, week_key)
    existing = found[0] if found else None

    default_idx = LEAGUE_LEVELS.index(existing["league_level"]) if existing and existing["league_level"] in LEAGUE_LEVELS else 0
    league = st.selectbox("Niveau de la ligue", LEAGUE_LEVELS, index=default_idx, key=f"rk_league_{k}")
    quota = LEAGUE_ATTACK_QUOTAS[league]
    st.info(f"📌 Ligue **{league}** : **{quota} attaques** par semaine.")

    ex_atk = [_loads(existing.get(f"stars_{i}_details"), []) if existing else [] for i in range(3)]
    ex_def_pcts = []
    for i in range(3):
        d_data = _loads(existing.get(f"def_{i}_details"), {}) if existing else {}
        if isinstance(d_data, dict):
            ex_def_pcts.append(d_data.get("pct", []))
        elif isinstance(d_data, list):
            ex_def_pcts.append(d_data)
        else:
            ex_def_pcts.append([])

    st.markdown("### 🏹 Attaques (Saisie complète)")
    ca = st.columns(3)
    n_atk = [
        ca[i].number_input(
            f"Attaques à {i} ⭐", min_value=0, max_value=quota,
            value=min(len(ex_atk[i]), quota), step=1, key=f"rk_natk{i}_{k}_{quota}",
        )
        for i in range(3)
    ]
    declared_atk = sum(n_atk)
    nb_3_star = max(0, quota - declared_atk)
    st.info(f"💡 Attaques restantes en **3 ⭐** : **{nb_3_star}** (sur {quota}).")

    st.markdown("### 🛡️ Défenses (Subies)")
    cd = st.columns(3)
    n_def = [
        cd[i].number_input(
            f"Défenses à {i} ⭐ subies", min_value=0,
            value=len(ex_def_pcts[i]), step=1, key=f"rk_ndef{i}_{k}",
        )
        for i in range(3)
    ]
    declared_def = sum(n_def)
    received = st.number_input(
        f"Défenses réellement reçues (sur {quota} attendues)",
        min_value=declared_def, max_value=max(quota, declared_def),
        value=max(declared_def, quota), step=1, key=f"rk_drecv_{k}_{quota}",
    )

    with st.form(key=f"rk_form_{k}_{quota}"):
        st.markdown("#### Pourcentages des attaques")
        atk_pcts = [
            _pct_inputs("Attaques 0 ⭐", n_atk[0], ex_atk[0], 0, 49, f"rk_a0_{k}"),
            _pct_inputs("Attaques 1 ⭐", n_atk[1], ex_atk[1], 1, 99, f"rk_a1_{k}"),
            _pct_inputs("Attaques 2 ⭐", n_atk[2], ex_atk[2], 50, 99, f"rk_a2_{k}"),
        ]

        st.markdown("#### Pourcentages des défenses subies")
        d0_pcts = _def_inputs_pct_only("Défenses 0 ⭐", n_def[0], ex_def_pcts[0], 25, 49, f"rk_d0_{k}")
        d1_pcts = _def_inputs_pct_only("Défenses 1 ⭐", n_def[1], ex_def_pcts[1], 50, 99, f"rk_d1_{k}")
        d2_pcts = _def_inputs_pct_only("Défenses 2 ⭐", n_def[2], ex_def_pcts[2], 80, 99, f"rk_d2_{k}")

        submitted = st.form_submit_button("💾 Enregistrer la ligue complète")

    if submitted:
        flat_atk = atk_pcts[0] + atk_pcts[1] + atk_pcts[2] + ([100.0] * nb_3_star)
        avg_dest = sum(flat_atk) / len(flat_atk) if flat_atk else 0.0
        
        # Calcul trophées globaux
        t_atk = sum(calculate_attack_trophies(0, p) for p in atk_pcts[0]) + \
                sum(calculate_attack_trophies(1, p) for p in atk_pcts[1]) + \
                sum(calculate_attack_trophies(2, p) for p in atk_pcts[2]) + (nb_3_star * 40)

        d_trophies = [calculate_defense_trophies(0, p) for p in d0_pcts] + \
                     [calculate_defense_trophies(1, p) for p in d1_pcts] + \
                     [calculate_defense_trophies(2, p) for p in d2_pcts]
        t_def = sum(d_trophies)

        conn.execute("""
            INSERT INTO ranked_leagues (
                player_tag, week_key, status, league_level, attacks_done, attacks_max,
                stars_3, stars_2, stars_1, stars_0_details, stars_1_details, stars_2_details,
                avg_destruction, def_done, def_max, def_0_details, def_1_details, def_2_details,
                def_missing, trophies_attack, trophies_defense, tracking_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                def_0_details = excluded.def_0_details,
                def_1_details = excluded.def_1_details,
                def_2_details = excluded.def_2_details,
                def_missing = excluded.def_missing,
                trophies_attack = excluded.trophies_attack,
                trophies_defense = excluded.trophies_defense
        """, [
            tag, week_key, "Terminé", league, quota, quota,
            nb_3_star, n_atk[2], n_atk[1],
            json.dumps(atk_pcts[0]), json.dumps(atk_pcts[1]), json.dumps(atk_pcts[2]),
            round(avg_dest, 2), received, quota,
            json.dumps({"pct": d0_pcts}), json.dumps({"pct": d1_pcts}), json.dumps({"pct": d2_pcts}),
            max(0, quota - received), t_atk, t_def, "Précis"
        ])
        st.session_state["ranked_flash"] = f"🎉 Données enregistrées pour {label} !"
        st.rerun()
