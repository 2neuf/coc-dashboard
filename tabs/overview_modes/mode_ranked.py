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


# ---------------------------------------------------------------------------
# Calculs Trophées
# ---------------------------------------------------------------------------
def calculate_attack_trophies(stars, destruction_pct, is_global=False):
    if is_global:
        if stars == 3: return 40
        elif stars == 2: return 28
        elif stars == 1: return 13
        elif stars == 0: return 4
        return 0
    else:
        if stars == 3: return 40
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
    st.markdown("""
        <style>
            div.block-container { padding-top: 1rem; padding-bottom: 1rem; }
            [data-testid="stVerticalBlock"] { gap: 0.15rem !important; }
            [data-testid="stHorizontalBlock"] { align-items: center !important; }
            hr { margin: 0.1rem 0px !important; border-color: #2c2c2c !important; }
            .stButton button { 
                padding: 0px 0.55rem !important; 
                height: 36px !important; 
                min-height: 36px !important; 
                font-size: 1.05rem !important; 
                font-weight: bold !important;
                line-height: 36px !important;
            }
            div[data-baseweb="select"] > div { 
                min-height: 36px !important; 
                height: 36px !important;
                padding-top: 0px !important; 
                padding-bottom: 0px !important; 
                font-size: 1rem !important;
            }
            .ranked-cell {
                margin: 0 !important;
                padding: 0 !important;
                height: 36px !important;
                line-height: 36px !important;
                font-size: 1.05rem !important;
                white-space: nowrap !important;
            }
        </style>
    """, unsafe_allow_html=True)

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
            st.warning("⚠️ Aucun compte en base.")
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
# Vue d'ensemble & Tableau Ongoing Ultra-Compact
# ---------------------------------------------------------------------------
def render_overview(conn, accounts):
    c_m, c_w = st.columns(2)
    sel_month = c_m.selectbox("Mois actif", MONTHS, key="ongoing_month")
    sel_week = c_w.selectbox("Semaine active", WEEKS, key="ongoing_week")
    current_week_key = f"{sel_month} - {sel_week}"

    try:
        rows = fetch_ranked(conn, week_key=current_week_key)
    except Exception as e:
        st.error(f"Erreur de lecture : {e}")
        return
    
    df_week = pd.DataFrame(rows) if rows else pd.DataFrame(columns=COLUMNS)

    st.markdown("<hr>", unsafe_allow_html=True)
    
    header_cols = [0.9, 1.25, 1.05, 0.75, 0.95, 0.95, 0.95, 0.95, 0.8, 0.8]
    hc = st.columns(header_cols)
    hc[0].markdown("<p class='ranked-cell'><b>Mode</b></p>", unsafe_allow_html=True)
    hc[1].markdown("<p class='ranked-cell'><b>Pseudo</b></p>", unsafe_allow_html=True)
    hc[2].markdown("<p class='ranked-cell'><b>Ligue</b></p>", unsafe_allow_html=True)
    hc[3].markdown("<p class='ranked-cell'><b>Atk</b></p>", unsafe_allow_html=True)
    hc[4].markdown("<p class='ranked-cell'><b>3⭐</b></p>", unsafe_allow_html=True)
    hc[5].markdown("<p class='ranked-cell'><b>2⭐</b></p>", unsafe_allow_html=True)
    hc[6].markdown("<p class='ranked-cell'><b>1⭐</b></p>", unsafe_allow_html=True)
    hc[7].markdown("<p class='ranked-cell'><b>0⭐</b></p>", unsafe_allow_html=True)
    hc[8].markdown("<p class='ranked-cell'><b>Atk Tr.</b></p>", unsafe_allow_html=True)
    hc[9].markdown("<p class='ranked-cell'><b>Total</b></p>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    for tag, name in accounts:
        acc_row = df_week[df_week["player_tag"] == tag]
        
        if acc_row.empty:
            league = "18"
            s3, s2, s1 = 0, 0, 0
            s0_count = 0
            t_atk = 0.0
            t_def = 0.0
            tracking_mode = "Globale"
        else:
            r = acc_row.iloc[0]
            league = r.get("league_level", "18")
            s3 = int(r.get("stars_3", 0) or 0)
            s2 = int(r.get("stars_2", 0) or 0)
            s1 = int(r.get("stars_1", 0) or 0)
            s0_count = len(_loads(r.get("stars_0_details"), []))
            t_atk = float(r.get("trophies_attack", 0.0) or 0.0)
            t_def = float(r.get("trophies_defense", 0.0) or 0.0)
            tracking_mode = r.get("tracking_mode", "Globale") or "Globale"

        quota = LEAGUE_ATTACK_QUOTAS.get(league, 14)
        total_attacks = s3 + s2 + s1 + s0_count
        total_trophies = t_atk + t_def

        cols = st.columns(header_cols)
        
        # 1. Mode (Texte simple par défaut, affichage du selectbox si édition activée)
        with cols[0]:
            edit_mode_key = f"edit_m_{tag}"
            if st.session_state.get(edit_mode_key, False):
                new_mode = st.selectbox("", ["Globale", "Précis"], index=0 if tracking_mode == "Globale" else 1, key=f"m_{tag}", label_visibility="collapsed")
                if new_mode != tracking_mode:
                    _save_field(conn, tag, current_week_key, tracking_mode=new_mode)
                    st.session_state[edit_mode_key] = False
                    st.rerun()
            else:
                mc1, mc2 = st.columns([2, 1])
                mc1.markdown(f"<p class='ranked-cell' style='font-size:0.9rem;'>{tracking_mode}</p>", unsafe_allow_html=True)
                if mc2.button("✏️", key=f"btn_m_{tag}"):
                    st.session_state[edit_mode_key] = True
                    st.rerun()

        # 2. Pseudo
        with cols[1]:
            st.markdown(f"<p class='ranked-cell'>{name}</p>", unsafe_allow_html=True)

        # 3. Ligue (Texte simple par défaut, affichage du selectbox si édition activée)
        with cols[2]:
            edit_lg_key = f"edit_l_{tag}"
            if st.session_state.get(edit_lg_key, False):
                new_league = st.selectbox("", LEAGUE_LEVELS, index=LEAGUE_LEVELS.index(league) if league in LEAGUE_LEVELS else 0, key=f"l_{tag}", label_visibility="collapsed")
                if new_league != league:
                    new_quota = LEAGUE_ATTACK_QUOTAS.get(new_league, 14)
                    _save_field(conn, tag, current_week_key, league_level=new_league, attacks_max=new_quota, def_max=new_quota)
                    st.session_state[edit_lg_key] = False
                    st.rerun()
            else:
                lc1, lc2 = st.columns([2, 1])
                lc1.markdown(f"<p class='ranked-cell' style='font-size:0.9rem;'>{league}</p>", unsafe_allow_html=True)
                if lc2.button("✏️", key=f"btn_l_{tag}"):
                    st.session_state[edit_lg_key] = True
                    st.rerun()

        # 4. Total Attaques
        with cols[3]:
            st.markdown(f"<p class='ranked-cell'>{total_attacks}/{quota}</p>", unsafe_allow_html=True)

        # 5. 3⭐ et son bouton "+"
        with cols[4]:
            sc1, sc2 = st.columns([0.8, 1])
            sc1.markdown(f"<p class='ranked-cell'>{s3}</p>", unsafe_allow_html=True)
            if sc2.button("+", key=f"b3_{tag}"):
                _add_attack(conn, tag, current_week_key, 3, 100.0, tracking_mode)
                st.rerun()

        # 6. 2⭐ et son bouton "+"
        with cols[5]:
            sc1, sc2 = st.columns([0.8, 1])
            sc1.markdown(f"<p class='ranked-cell'>{s2}</p>", unsafe_allow_html=True)
            if sc2.button("+", key=f"b2_{tag}"):
                if tracking_mode == "Globale":
                    _add_attack(conn, tag, current_week_key, 2, 75.0, tracking_mode)
                    st.rerun()
                else:
                    st.session_state[f"p_atk_{tag}"] = 2

        # 7. 1⭐ et son bouton "+"
        with cols[6]:
            sc1, sc2 = st.columns([0.8, 1])
            sc1.markdown(f"<p class='ranked-cell'>{s1}</p>", unsafe_allow_html=True)
            if sc2.button("+", key=f"b1_{tag}"):
                if tracking_mode == "Globale":
                    _add_attack(conn, tag, current_week_key, 1, 50.0, tracking_mode)
                    st.rerun()
                else:
                    st.session_state[f"p_atk_{tag}"] = 1

        # 8. 0⭐ et son bouton "+"
        with cols[7]:
            sc1, sc2 = st.columns([0.8, 1])
            sc1.markdown(f"<p class='ranked-cell'>{s0_count}</p>", unsafe_allow_html=True)
            if sc2.button("+", key=f"b0_{tag}"):
                if tracking_mode == "Globale":
                    _add_attack(conn, tag, current_week_key, 0, 20.0, tracking_mode)
                    st.rerun()
                else:
                    st.session_state[f"p_atk_{tag}"] = 0

        # 9. Trophées Atk
        with cols[8]:
            st.markdown(f"<p class='ranked-cell'>{t_atk:+.0f}</p>", unsafe_allow_html=True)

        # 10. Total
        with cols[9]:
            st.markdown(f"<p class='ranked-cell'><b>{total_trophies:+.0f}</b></p>", unsafe_allow_html=True)

        # Popup mini pour le mode précis
        if st.session_state.get(f"p_atk_{tag}") is not None:
            star_val = st.session_state[f"p_atk_{tag}"]
            with st.form(key=f"f_prec_{tag}"):
                st.markdown(f"**Pourcentage de destruction ({star_val} ⭐) pour {name} :**")
                min_l = 0 if star_val == 0 else (1 if star_val == 1 else 50)
                max_l = 49 if star_val == 0 else (99 if star_val in [1, 2] else 100)
                pct = st.number_input("Destruction %", min_value=min_l, max_value=max_l, value=min_l)
                if st.form_submit_button("Valider"):
                    _add_attack(conn, tag, current_week_key, star_val, float(pct), tracking_mode)
                    st.session_state.pop(f"p_atk_{tag}", None)
                    st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Fonctions de mise à jour et formulaire a posteriori
# ---------------------------------------------------------------------------
def _save_field(conn, tag, week_key, **kwargs):
    existing = fetch_ranked(conn, tag, week_key)
    if not existing:
        conn.execute("""
            INSERT INTO ranked_leagues (player_tag, week_key, status, league_level, attacks_max, def_max, tracking_mode, trophies_attack, trophies_defense, avg_destruction, stars_3, stars_2, stars_1)
            VALUES (?, ?, 'En cours', '18', 14, 14, 'Globale', 0.0, 0.0, 0.0, 0, 0, 0)
        """, [tag, week_key])
    
    set_clauses, vals = [], []
    for k, v in kwargs.items():
        set_clauses.append(f"{k} = ?")
        vals.append(v)
    vals.extend([tag, week_key])
    conn.execute(f"UPDATE ranked_leagues SET {', '.join(set_clauses)} WHERE player_tag = ? AND week_key = ?", vals)


def _add_attack(conn, tag, week_key, stars, destruction_pct, mode):
    existing = fetch_ranked(conn, tag, week_key)
    if not existing:
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
    new_t_atk = float(r.get("trophies_attack", 0.0) or 0.0) + t_add

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

    st.markdown("### 🏹 Attaques (Saisie complète)")
    ca = st.columns(3)
    n_atk = [
        ca[i].number_input(f"Attaques à {i} ⭐", min_value=0, max_value=quota, value=min(len(ex_atk[i]), quota), step=1, key=f"rk_natk{i}_{k}_{quota}")
        for i in range(3)
    ]
    nb_3_star = max(0, quota - sum(n_atk))
    st.info(f"💡 Attaques restantes en **3 ⭐** : **{nb_3_star}** (sur {quota}).")

    with st.form(key=f"rk_form_{k}_{quota}"):
        st.markdown("#### Pourcentages des attaques")
        atk_pcts = [
            [st.number_input(f"A0 #{i+1}", 0, 49, val, key=f"a0_{k}_{i}") for i, val in enumerate(ex_atk[0])],
            [st.number_input(f"A1 #{i+1}", 1, 99, val, key=f"a1_{k}_{i}") for i, val in enumerate(ex_atk[1])],
            [st.number_input(f"A2 #{i+1}", 50, 99, val, key=f"a2_{k}_{i}") for i, val in enumerate(ex_atk[2])],
        ]
        submitted = st.form_submit_button("💾 Enregistrer la ligue complète")

    if submitted:
        flat_atk = [p for sub in atk_pcts for p in sub] + ([100.0] * nb_3_star)
        avg_dest = sum(flat_atk) / len(flat_atk) if flat_atk else 0.0
        t_atk = sum(calculate_attack_trophies(0, p) for p in atk_pcts[0]) + \
                sum(calculate_attack_trophies(1, p) for p in atk_pcts[1]) + \
                sum(calculate_attack_trophies(2, p) for p in atk_pcts[2]) + (nb_3_star * 40)

        conn.execute("""
            INSERT INTO ranked_leagues (
                player_tag, week_key, status, league_level, attacks_done, attacks_max,
                stars_3, stars_2, stars_1, stars_0_details, stars_1_details, stars_2_details,
                avg_destruction, def_done, def_max, trophies_attack, tracking_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_tag, week_key) DO UPDATE SET
                status = excluded.status,
                league_level = excluded.league_level,
                attacks_done = excluded.attacks_done,
                stars_3 = excluded.stars_3,
                stars_2 = excluded.stars_2,
                stars_1 = excluded.stars_1,
                avg_destruction = excluded.avg_destruction,
                trophies_attack = excluded.trophies_attack
        """, [
            tag, week_key, "Terminé", league, quota, quota,
            nb_3_star, n_atk[2], n_atk[1],
            json.dumps(atk_pcts[0]), json.dumps(atk_pcts[1]), json.dumps(atk_pcts[2]),
            round(avg_dest, 2), quota, quota, t_atk, "Précis"
        ])
        st.session_state["ranked_flash"] = f"🎉 Données enregistrées pour {label} !"
        st.rerun()
