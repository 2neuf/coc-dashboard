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
    "def_missing", "trophies_attack", "trophies_defense",
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
def calculate_attack_trophies(stars, destruction_pct):
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


def calculate_defense_trophies(stars, destruction_pct):
    return 40 - calculate_attack_trophies(stars, destruction_pct)


def compute_summary(atk_pcts_by_star, nb_3_star, def_details_list, received, expected):
    flat_atk_pcts = []
    total_atk_trophies = 0

    for p in atk_pcts_by_star[0]:
        flat_atk_pcts.append(float(p))
        total_atk_trophies += calculate_attack_trophies(0, p)
    for p in atk_pcts_by_star[1]:
        flat_atk_pcts.append(float(p))
        total_atk_trophies += calculate_attack_trophies(1, p)
    for p in atk_pcts_by_star[2]:
        flat_atk_pcts.append(float(p))
        total_atk_trophies += calculate_attack_trophies(2, p)
    for _ in range(nb_3_star):
        flat_atk_pcts.append(100.0)
        total_atk_trophies += 40

    avg_destruction = sum(flat_atk_pcts) / len(flat_atk_pcts) if flat_atk_pcts else 0.0

    def_trophies_collected = []
    for d in def_details_list[0]:
        p = d.get("pct", 0)
        def_trophies_collected.append(calculate_defense_trophies(0, p))
    for d in def_details_list[1]:
        p = d.get("pct", 0)
        def_trophies_collected.append(calculate_defense_trophies(1, p))
    for d in def_details_list[2]:
        p = d.get("pct", 0)
        def_trophies_collected.append(calculate_defense_trophies(2, p))

    sum_received = sum(def_trophies_collected)
    if received > 0:
        avg_per_def = int(sum_received // received)
    else:
        avg_per_def = 0

    missing = max(0, expected - received)
    adjusted_defense_trophies = sum_received + missing * avg_per_def

    return {
        "avg_destruction": round(avg_destruction, 2),
        "missing": missing,
        "trophies_attack": total_atk_trophies,
        "trophies_defense": float(adjusted_defense_trophies),
    }


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

        tab_overview, tab_form = st.tabs(["📊 Vue d'ensemble", "📝 Saisir / Modifier une ligue"])
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
# Vue d'ensemble (Tableau Unique par Compte)
# ---------------------------------------------------------------------------
def render_overview(conn, accounts):
    try:
        rows = fetch_ranked(conn)
    except Exception as e:
        st.error(f"Erreur de lecture des ligues : {e}")
        return
    
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=COLUMNS)
    table_data = []
    
    for tag, name in accounts:
        acc_rows = df[df["player_tag"] == tag] if not df.empty else pd.DataFrame()
        if not acc_rows.empty:
            acc_rows["_order"] = acc_rows["week_key"].map(_week_order)
            acc_rows = acc_rows.sort_values("_order")
            last = acc_rows.iloc[-1]
            
            league = last.get("league_level", "-")
            status = last.get("status", "Terminé")
            week_info = last.get("week_key", "")
            statut_display = f"{status} ({week_info})"
            
            attacks_done = int(last.get("attacks_done", 0) or 0)
            attacks_max = int(last.get("attacks_max", 0) or 0)
            s3 = int(last.get("stars_3", 0) or 0)
            s2 = int(last.get("stars_2", 0) or 0)
            s1 = int(last.get("stars_1", 0) or 0)
            s0 = len(_loads(last.get("stars_0_details"), []))
            
            avg_dest = float(last.get("avg_destruction", 0.0) or 0.0)
            t_atk = float(last.get("trophies_attack", 0.0) or 0.0)
            
            def_done = int(last.get("def_done", 0) or 0)
            def_max = int(last.get("def_max", 0) or 0)
            t_def = float(last.get("trophies_defense", 0.0) or 0.0)
            
            avg_def_trophy = int(t_def // def_done) if def_done > 0 else 0
            total_trophies = t_atk + t_def
            
            table_data.append({
                "Pseudo": name,
                "Ligue": league,
                "Statut": statut_display,
                "Atk (Faites / Max)": f"{attacks_done} / {attacks_max}",
                "3⭐": s3,
                "2⭐": s2,
                "1⭐": s1,
                "0⭐": s0,
                "Destr. moy.": f"{avg_dest:.1f}%",
                "Trophées Atk": f"{t_atk:+.0f}" if t_atk != 0 else "0",
                "Déf (Reçues / Attendues)": f"{def_done} / {def_max}",
                "Moy. trophée/déf.": f"{avg_def_trophy}",
                "Trophées Déf": f"{t_def:+.0f}",
                "Total Trophées": f"{total_trophies:+.0f}"
            })
        else:
            table_data.append({
                "Pseudo": name,
                "Ligue": "-",
                "Statut": "Inscris (Aucune ligue)",
                "Atk (Faites / Max)": "0 / 0",
                "3⭐": 0, "2⭐": 0, "1⭐": 0, "0⭐": 0,
                "Destr. moy.": "0.0%",
                "Trophées Atk": "0",
                "Déf (Reçues / Attendues)": "0 / 0",
                "Moy. trophée/déf.": "0",
                "Trophées Déf": "0",
                "Total Trophées": "0"
            })
            
    summary_df = pd.DataFrame(table_data)
    
    st.markdown("### 📊 Tableau de Suivi Global des Ligues")
    st.dataframe(summary_df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Formulaire "ligue terminée" (Ajout ou Modification)
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
    
    default_acc_idx = 0
    if "edit_tag" in st.session_state:
        for idx, (lbl, t) in enumerate(labels.items()):
            if t == st.session_state["edit_tag"]:
                default_acc_idx = idx
                break

    label = st.selectbox("Compte", list(labels), index=default_acc_idx, key="rk_form_account")
    tag = labels[label]

    c1, c2 = st.columns(2)
    
    default_month_idx = 0
    default_week_idx = 0
    if "edit_week_key" in st.session_state:
        try:
            m_part, w_part = st.session_state["edit_week_key"].split(" - ")
            if m_part in MONTHS:
                default_month_idx = MONTHS.index(m_part)
            if w_part in WEEKS:
                default_week_idx = WEEKS.index(w_part)
        except Exception:
            pass

    month = c1.selectbox("Mois", MONTHS, index=default_month_idx, key="rk_form_month")
    week = c2.selectbox("Semaine", WEEKS, index=default_week_idx, key="rk_form_week")
    week_key = f"{month} - {week}"
    k = f"{tag}_{week_key}"

    try:
        found = fetch_ranked(conn, tag, week_key)
    except Exception as e:
        st.error(f"Erreur de lecture : {e}")
        return
    existing = found[0] if found else None

    default_idx = LEAGUE_LEVELS.index(existing["league_level"]) if existing and existing["league_level"] in LEAGUE_LEVELS else 0
    league = st.selectbox("Niveau de la ligue", LEAGUE_LEVELS, index=default_idx, key=f"rk_league_{k}")
    quota = LEAGUE_ATTACK_QUOTAS[league]
    st.info(f"📌 Ligue **{league}** : **{quota} attaques** par semaine.")

    if existing:
        st.warning(f"✏️ **Mode Modification** : Des données existent déjà pour **{week_key}**. Tu peux modifier les valeurs ci-dessous et réenregistrer.")
    else:
        st.info(f"➕ **Mode Création** : Aucune donnée pour **{label}** sur **{week_key}**.")

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

    # --- Nombres d'attaques ---
    st.markdown("### 🏹 Attaques")
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
    if declared_atk > quota:
        st.error(f"⚠️ {declared_atk} attaques déclarées pour un quota de {quota}.")
    st.info(f"💡 Attaques restantes déduites en **3 ⭐** : **{nb_3_star}** (sur {quota}).")

    # --- Nombres de défenses ---
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

    expected = quota
    prev_recv = int(existing["def_done"]) if existing and existing["def_done"] else 0
    received = st.number_input(
        f"Défenses réellement reçues (sur {expected} attendues)",
        min_value=declared_def, max_value=max(expected, declared_def),
        value=min(max(declared_def, prev_recv), max(expected, declared_def)),
        step=1, key=f"rk_drecv_{k}_{quota}_{declared_def}",
    )
    missing_preview = max(0, expected - received)
    if missing_preview:
        st.info(f"💡 {missing_preview} défense(s) manquante(s) : la moyenne de trophées sera complétée automatiquement.")

    # --- Formulaire de saisie ---
    with st.form(key=f"rk_form_{k}_{quota}"):
        st.markdown("#### Pourcentages des attaques")
        atk_pcts = [
            _pct_inputs("Attaques 0 ⭐", n_atk[0], ex_atk[0], 0, 49, f"rk_a0_{k}"),
            _pct_inputs("Attaques 1 ⭐", n_atk[1], ex_atk[1], 1, 99, f"rk_a1_{k}"),
            _pct_inputs("Attaques 2 ⭐", n_atk[2], ex_atk[2], 50, 99, f"rk_a2_{k}"),
        ]

        st.markdown("#### Pourcentages des défenses subies")
        d0_pcts = _def_inputs_pct_only("Défenses 0 ⭐ (adversaire a fait 0⭐)", n_def[0], ex_def_pcts[0], 25, 49, f"rk_d0_{k}")
        d1_pcts = _def_inputs_pct_only("Défenses 1 ⭐ (adversaire a fait 1⭐)", n_def[1], ex_def_pcts[1], 50, 99, f"rk_d1_{k}")
        d2_pcts = _def_inputs_pct_only("Défenses 2 ⭐ (adversaire a fait 2⭐)", n_def[2], ex_def_pcts[2], 80, 99, f"rk_d2_{k}")

        btn_label = "💾 Mettre à jour la semaine" if existing else "💾 Enregistrer la nouvelle semaine"
        submitted = st.form_submit_button(btn_label)

    if submitted:
        if declared_atk > quota:
            st.error("Impossible d'enregistrer : le nombre d'attaques dépasse le quota.")
            return

        def_details_structured = [
            [{"pct": p, "trophies": calculate_defense_trophies(0, p)} for p in d0_pcts],
            [{"pct": p, "trophies": calculate_defense_trophies(1, p)} for p in d1_pcts],
            [{"pct": p, "trophies": calculate_defense_trophies(2, p)} for p in d2_pcts],
        ]

        summary = compute_summary(
            atk_pcts_by_star=atk_pcts,
            nb_3_star=nb_3_star,
            def_details_list=def_details_structured,
            received=received,
            expected=expected,
        )

        try:
            conn.execute("""
                INSERT INTO ranked_leagues (
                    player_tag, week_key, status, league_level, attacks_done, attacks_max,
                    stars_3, stars_2, stars_1, stars_0_details, stars_1_details, stars_2_details,
                    avg_destruction, def_done, def_max, def_0_details, def_1_details, def_2_details,
                    def_missing, trophies_attack, trophies_defense
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                summary["avg_destruction"], received, expected,
                json.dumps({"pct": d0_pcts, "trophies": [d["trophies"] for d in def_details_structured[0]]}),
                json.dumps({"pct": d1_pcts, "trophies": [d["trophies"] for d in def_details_structured[1]]}),
                json.dumps({"pct": d2_pcts, "trophies": [d["trophies"] for d in def_details_structured[2]]}),
                summary["missing"], summary["trophies_attack"], summary["trophies_defense"],
            ])
        except Exception as e:
            st.error(f"Erreur lors de l'enregistrement : {e}")
            return

        st.session_state.pop("edit_tag", None)
        st.session_state.pop("edit_week_key", None)

        st.session_state["ranked_flash"] = f"🎉 Résultats enregistrés avec succès pour {label} ({week_key}) !"
        st.rerun()

    # --- Bilan de la période ---
    if existing:
        st.markdown("---")
        st.markdown(f"### 📊 Bilan enregistré : {week_key}")
        stars_total = 3 * (existing["stars_3"] or 0) + 2 * (existing["stars_2"] or 0) + (existing["stars_1"] or 0)
        m = st.columns(5)
        m[0].metric("Ligue", existing["league_level"])
        m[1].metric("Étoiles", f"{stars_total} / {3 * (existing['attacks_max'] or 0)}")
        m[2].metric("Trophées atk", f"{int(existing['trophies_attack'] or 0):+d}")
        m[3].metric("Destruction moy.", f"{(existing['avg_destruction'] or 0):.1f}%")
        m[4].metric("Trophées déf. ajustés", f"{(existing['trophies_defense'] or 0):+.1f}")

        # 🔍 SECTION DE DÉBOGAGE
        with st.expander("🔍 Voir le détail des trophées (Debug Attaques & Défenses)"):
            st.write("**Détail des attaques :**")
            for star_lvl in [0, 1, 2]:
                details_json = existing.get(f"stars_{star_lvl}_details")
                pcts = _loads(details_json, [])
                if pcts:
                    for idx, p in enumerate(pcts):
                        t_calc = calculate_attack_trophies(star_lvl, p)
                        st.text(f"• Attaque {star_lvl}⭐ #{idx+1} : {p}% de destruction -> {t_calc} trophées")
            
            if existing.get("stars_3", 0) > 0:
                st.text(f"• Attaques 3⭐ : {existing['stars_3']} attaque(s) à 100% -> 40 trophées chacune")

            st.write("---")
            st.write("**Détail des défenses subies :**")
            for star_lvl in [0, 1, 2]:
                def_data = _loads(existing.get(f"def_{star_lvl}_details"), {})
                pcts = def_data.get("pct", []) if isinstance(def_data, dict) else []
                trophies_list = def_data.get("trophies", []) if isinstance(def_data, dict) else []
                if pcts:
                    for idx, p in enumerate(pcts):
                        t_val = trophies_list[idx] if idx < len(trophies_list) else "N/A"
                        st.text(f"• Défense {star_lvl}⭐ subie #{idx+1} : {p}% de destruction -> {t_val} trophées de défense")
            
            missing_def = existing.get("def_missing", 0)
            if missing_def > 0:
                st.text(f"• Défenses manquantes prises en compte : {missing_def} (compensées par la moyenne)")
