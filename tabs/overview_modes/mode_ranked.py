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
    # TODO : si utils.py contient déjà une fonction de connexion, importe-la ici à la place.
    import libsql_client
    url = os.environ.get("TURSO_DATABASE_URL", "https://coc-dashboard-2neuf.aws-eu-west-1.turso.io")
    auth_token = os.environ.get("TURSO_AUTH_TOKEN", "")
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
    return libsql_client.create_client_sync(url=url, auth_token=auth_token, tls=True)


def ensure_table(conn):
    """Crée la table si elle n'existe pas (sans effet si elle existe déjà)."""
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
            stars_0_ TEXT,
            stars_1_ TEXT,
            stars_2_ TEXT,
            avg_destruction REAL,
            def_done INTEGER,
            def_max INTEGER,
            def_0_ TEXT,
            def_1_details TEXT,
            def_2_details TEXT,
            def_missing INTEGER,
            trophies_attack REAL,
            trophies_defense REAL,
            PRIMARY KEY (player_tag, week_key)
        )
    """)

    # Table déjà existante : on ajoute les colonnes manquantes
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

    # Nécessaire pour le ON CONFLICT(player_tag, week_key) de l'enregistrement
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
    """Clé de tri chronologique pour 'Novembre - Semaine 2'."""
    try:
        month, week = week_key.split(" - ")
        return MONTHS.index(month) * 10 + int(week.split()[-1])
    except (ValueError, IndexError):
        return 999


# ---------------------------------------------------------------------------
# Calculs
# ---------------------------------------------------------------------------
def compute_summary(atk_pcts, nb_3_star, def_trophies, received, expected):
    """atk_pcts : pourcentages des attaques à 0/1/2 étoiles (liste à plat)."""
    all_pcts = list(atk_pcts) + [100.0] * nb_3_star
    avg_destruction = sum(all_pcts) / len(all_pcts) if all_pcts else 0.0

    sum_received = sum(def_trophies)
    avg_per_def = sum_received / received if received > 0 else 0.0
    missing = max(0, expected - received)
    adjusted = sum_received + missing * avg_per_def
    return {
        "avg_destruction": round(avg_destruction, 2),
        "missing": missing,
        "avg_per_def": avg_per_def,
        "adjusted_trophies": round(adjusted, 1),
    }


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
def render_mode_ranked():
    st.subheader("⚔️ Ligues Classées")

    try:
        conn = get_db_client()
        ensure_table(conn)
        res = conn.execute("SELECT player_tag, name FROM accounts ORDER BY name ASC")
        accounts = [(row[0], row[1]) for row in res.rows]
    except Exception as e:
        st.error(f"Erreur d'accès à la base de données : {e}")
        return

    try:
        if not accounts:
            st.warning("⚠️ Aucun compte en base. Ajoute d'abord un compte dans l'application.")
            return

        tab_overview, tab_form = st.tabs(["📊 Vue d'ensemble", "📝 Saisir une ligue terminée"])
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
# Vue d'ensemble
# ---------------------------------------------------------------------------
def render_overview(conn, accounts):
    try:
        rows = fetch_ranked(conn)
    except Exception as e:
        st.error(f"Erreur de lecture des ligues : {e}")
        return
    if not rows:
        st.info("Aucune ligue enregistrée pour le moment. Utilise l'onglet « Saisir une ligue terminée ».")
        return

    names = {tag: name for tag, name in accounts}
    df = pd.DataFrame(rows)
    for col in NUM_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["Compte"] = df["player_tag"].map(names).fillna(df["player_tag"])
    df["_order"] = df["week_key"].map(_week_order)
    df["stars_0"] = df["stars_0_details"].map(lambda v: len(_loads(v, [])))
    df["stars_total"] = 3 * df["stars_3"] + 2 * df["stars_2"] + df["stars_1"]
    df = df.sort_values("_order")

    st.markdown("### Dernière période de chaque compte")
    for tag, g in df.groupby("player_tag", sort=False):
        last = g.iloc[-1]
        prev = g.iloc[-2] if len(g) > 1 else None
        with st.container(border=True):
            st.markdown(f"**{last['Compte']}** · {last['week_key']} · {last['status']}")
            c = st.columns(5)
            c[0].metric("Ligue", last["league_level"])
            c[1].metric("Attaques", f"{int(last['attacks_done'])} / {int(last['attacks_max'])}")
            c[2].metric("Étoiles", f"{int(last['stars_total'])} / {3 * int(last['attacks_max'])}")
            c[3].metric(
                "Destruction moy.", f"{last['avg_destruction']:.1f}%",
                delta=None if prev is None else f"{last['avg_destruction'] - prev['avg_destruction']:+.1f} pt",
            )
            c[4].metric(
                "Trophées déf.", f"{last['trophies_defense']:+.1f}",
                delta=None if prev is None else f"{last['trophies_defense'] - prev['trophies_defense']:+.1f}",
            )

    st.markdown("### Historique d'un compte")
    account_names = list(dict.fromkeys(df["Compte"]))
    chosen = st.selectbox("Compte", account_names, key="rk_overview_account")
    hist = df[df["Compte"] == chosen]

    chart_df = hist.set_index("week_key")
    col_a, col_b = st.columns(2)
    with col_a:
        st.caption("Destruction moyenne (%)")
        st.line_chart(chart_df[["avg_destruction"]])
    with col_b:
        st.caption("Trophées de défense (ajustés)")
        st.line_chart(chart_df[["trophies_defense"]])

    table = hist[[
        "week_key", "league_level", "attacks_done", "stars_3", "stars_2", "stars_1", "stars_0",
        "stars_total", "avg_destruction", "def_done", "def_max", "def_missing", "trophies_defense",
    ]].rename(columns={
        "week_key": "Période", "league_level": "Ligue", "attacks_done": "Attaques",
        "stars_3": "3⭐", "stars_2": "2⭐", "stars_1": "1⭐", "stars_0": "0⭐",
        "stars_total": "Étoiles", "avg_destruction": "Destr. moy. (%)",
        "def_done": "Déf. reçues", "def_max": "Déf. attendues", "def_missing": "Déf. manquantes",
        "trophies_defense": "Trophées déf.",
    })
    st.dataframe(table, hide_index=True)


# ---------------------------------------------------------------------------
# Formulaire "ligue terminée"
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


def _def_inputs(title, n, prefill, default_pct, default_trophy, max_pct, key):
    pcts, trophies = [], []
    if n <= 0:
        return pcts, trophies
    st.markdown(f"##### {title}")
    pre_p = prefill.get("pct", []) if isinstance(prefill, dict) else []
    pre_t = prefill.get("trophies", []) if isinstance(prefill, dict) else []
    for i in range(n):
        c1, c2 = st.columns(2)
        with c1:
            pcts.append(st.number_input(
                f"Défense #{i + 1} (%)", min_value=0, max_value=max_pct,
                value=min(pre_p[i] if i < len(pre_p) else default_pct, max_pct),
                step=1, key=f"{key}_p_{i}",
            ))
        with c2:
            trophies.append(st.number_input(
                f"Trophées défense #{i + 1}", min_value=-60, max_value=60,
                value=int(pre_t[i]) if i < len(pre_t) else default_trophy,
                step=1, key=f"{key}_t_{i}",
            ))
    return pcts, trophies


def render_form(conn, accounts):
    flash = st.session_state.pop("ranked_flash", None)
    if flash:
        st.success(flash)

    # --- Compte, période, ligue -------------------------------------------
    labels = {f"{name} ({tag})": tag for tag, name in accounts}
    label = st.selectbox("Compte", list(labels), key="rk_form_account")
    tag = labels[label]

    c1, c2 = st.columns(2)
    month = c1.selectbox("Mois", MONTHS, key="rk_form_month")
    week = c2.selectbox("Semaine", WEEKS, key="rk_form_week")
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
        st.success(f"✅ Données existantes pour **{week_key}** : tu peux les modifier et réenregistrer.")
    else:
        st.info(f"Aucune donnée pour **{label}** sur **{week_key}**.")

    ex_atk = [_loads(existing.get(f"stars_{i}_details"), []) if existing else [] for i in range(3)]
    ex_def = [_loads(existing.get(f"def_{i}_details"), {}) if existing else {} for i in range(3)]

    # --- Nombres d'attaques (hors formulaire pour que les champs se mettent à jour) ---
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

    # --- Nombres de défenses ---------------------------------------------
    st.markdown("### 🛡️ Défenses")
    cd = st.columns(3)
    n_def = [
        cd[i].number_input(
            f"Défenses à {i} ⭐ (subies)", min_value=0,
            value=len(ex_def[i].get("pct", [])) if isinstance(ex_def[i], dict) else 0,
            step=1, key=f"rk_ndef{i}_{k}",
        )
        for i in range(3)
    ]
    declared_def = sum(n_def)

    # Défenses attendues = quota d'attaques de la ligue
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
        st.info(f"💡 {missing_preview} défense(s) manquante(s) : la moyenne de trophées par défense sera ajoutée pour chacune.")

    # --- Détails (dans le formulaire) -------------------------------------
    with st.form(key=f"rk_form_{k}_{quota}"):
        st.markdown("#### Détail des attaques")
        atk_pcts = [
            _pct_inputs("Attaques 0 ⭐", n_atk[0], ex_atk[0], 0, 49, f"rk_a0_{k}"),
            _pct_inputs("Attaques 1 ⭐", n_atk[1], ex_atk[1], 1, 99, f"rk_a1_{k}"),
            _pct_inputs("Attaques 2 ⭐", n_atk[2], ex_atk[2], 50, 99, f"rk_a2_{k}"),
        ]

        st.markdown("#### Détail des défenses")
        d0_p, d0_t = _def_inputs("Défenses 0 ⭐", n_def[0], ex_def[0], 0, 30, 49, f"rk_d0_{k}")
        d1_p, d1_t = _def_inputs("Défenses 1 ⭐", n_def[1], ex_def[1], 1, 20, 99, f"rk_d1_{k}")
        d2_p, d2_t = _def_inputs("Défenses 2 ⭐", n_def[2], ex_def[2], 50, 10, 99, f"rk_d2_{k}")

        submitted = st.form_submit_button("💾 Enregistrer les résultats de la ligue")

    if submitted:
        if declared_atk > quota:
            st.error("Impossible d'enregistrer : le nombre d'attaques dépasse le quota.")
            return

        summary = compute_summary(
            atk_pcts=atk_pcts[0] + atk_pcts[1] + atk_pcts[2],
            nb_3_star=nb_3_star,
            def_trophies=d0_t + d1_t + d2_t,
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
                json.dumps({"pct": d0_p, "trophies": d0_t}),
                json.dumps({"pct": d1_p, "trophies": d1_t}),
                json.dumps({"pct": d2_p, "trophies": d2_t}),
                summary["missing"], 0, summary["adjusted_trophies"],
            ])
        except Exception as e:
            st.error(f"Erreur lors de l'enregistrement : {e}")
            return

        st.session_state["ranked_flash"] = f"🎉 Résultats enregistrés pour {label} ({week_key})."
        st.rerun()

    # --- Bilan de la période ---------------------------------------------
    if existing:
        st.markdown("---")
        st.markdown(f"### 📊 Bilan enregistré : {week_key}")
        stars_total = 3 * (existing["stars_3"] or 0) + 2 * (existing["stars_2"] or 0) + (existing["stars_1"] or 0)
        m = st.columns(4)
        m[0].metric("Ligue", existing["league_level"])
        m[1].metric("Étoiles", f"{stars_total} / {3 * (existing['attacks_max'] or 0)}")
        m[2].metric("Destruction moy.", f"{(existing['avg_destruction'] or 0):.1f}%")
        m[3].metric("Trophées déf. ajustés", f"{(existing['trophies_defense'] or 0):+.1f}")
