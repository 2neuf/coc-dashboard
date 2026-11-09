import streamlit as st
import libsql_client
import os
import requests

HERO_PETS_LIST = [
    "L.A.S.S.I", "Mighty Yak", "Electro Owl", "Unicorn", 
    "Phoenix", "Poison Lizard", "Diggy", "Frosty", 
    "Spirit Fox", "Angry Jelly", "Sneezy", "Greedy Raven"
]

SIEGE_MACHINES_LIST = [
    "Wall Wrecker", "Battle Blimp", "Stone Slammer", "Siege Barracks", 
    "Log Launcher", "Flame Flinger", "Battle Drill"
]

def get_db_client():
    url = os.environ.get("TURSO_DATABASE_URL", "https://coc-dashboard-2neuf.aws-eu-west-1.turso.io")
    auth_token = os.environ.get("TURSO_AUTH_TOKEN", "")
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
    return libsql_client.create_client_sync(url=url, auth_token=auth_token, tls=True)

def init_db():
    try:
        conn = get_db_client()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                player_tag TEXT PRIMARY KEY,
                name TEXT,
                town_hall INTEGER,
                gold_pass_boost INTEGER DEFAULT 0
            )
        """)
        try:
            conn.execute("ALTER TABLE accounts ADD COLUMN active_composition TEXT DEFAULT 'Aucune'")
        except Exception:
            pass

        # Ajout de la colonne pour gérer l'ordre personnalisé des comptes
        try:
            conn.execute("ALTER TABLE accounts ADD COLUMN display_order INTEGER DEFAULT 0")
        except Exception:
            pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                item_name TEXT PRIMARY KEY
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compositions (
                comp_name TEXT PRIMARY KEY,
                details TEXT,
                town_hall_level INTEGER DEFAULT 18,
                raw_data TEXT
            )
        """)
        try:
            conn.execute("ALTER TABLE compositions ADD COLUMN raw_data TEXT")
        except Exception:
            pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS hero_equipment_config (
                hero_name TEXT,
                equipment_name TEXT,
                PRIMARY KEY (hero_name, equipment_name)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS custom_emojis (
                item_name TEXT PRIMARY KEY,
                emoji TEXT
            )
        """)
        
        # Initialisation de la table des ligues classées
        init_ranked_leagues_table()

        conn.execute("""
            INSERT OR IGNORE INTO accounts (player_tag, name, town_hall, active_composition, display_order) 
            VALUES (?, ?, ?, ?, ?)
        """, ["#YJ0U9P89V", "Mini", 18, "Aucune", 0])
    except Exception as e:
        st.error(f"Erreur d'initialisation DB : {e}")

def get_all_accounts():
    conn = get_db_client()
    res = conn.execute("SELECT player_tag, name, town_hall, active_composition, display_order FROM accounts ORDER BY display_order ASC, name ASC")
    return [row for row in res.rows]

@st.cache_data(ttl=60)
def fetch_player_data(player_tag):
    api_token = os.environ.get("COC_API_TOKEN", "")
    formatted_tag = player_tag.replace("#", "%23")
    url = f"https://api.clashofclans.com/v1/players/{formatted_tag}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json(), None
    except Exception as e:
        return None, str(e)
    return None, "Erreur API"

def get_db_favorites():
    conn = get_db_client()
    res = conn.execute("SELECT item_name FROM favorites")
    return {row[0] for row in res.rows}

def sort_items(items_list, favorites):
    def sort_key(item):
        name = item.get('name', '')
        is_fav = 0 if name in favorites else 1
        level = item.get('level', 0)
        max_level = item.get('maxLevel', 1)
        diff = max_level - level
        return (is_fav, diff, -level)
    return sorted(items_list, key=sort_key)

# Cache des emojis personnalisés pour éviter les requêtes DB à chaque affichage d'icône
@st.cache_data(ttl=10)
def _get_cached_custom_emoji(name):
    try:
        conn = get_db_client()
        res = conn.execute("SELECT emoji FROM custom_emojis WHERE item_name = ?", [name])
        if res.rows:
            return res.rows[0][0]
    except Exception:
        pass
    return None

def get_icon_emoji(item_name):
    # Utilise directement le cache global en mémoire s'il existe (zéro requête SQL à la volée)
    if "preloaded_emojis" in st.session_state and item_name in st.session_state["preloaded_emojis"]:
        return st.session_state["preloaded_emojis"][item_name]
    
    # Sinon, repli sur ta méthode de secours habituelle
    return "🛡️"

def render_card(name, level, max_level, favorites, emoji="⚔️"):
    is_fav = name in favorites
    fav_symbol = "❤️" if is_fav else "🤍"
    
    st.markdown(f"""
        <div style="border: 1px solid #333; padding: 10px; border-radius: 8px; margin-bottom: 8px; background-color: #1e1e1e;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 1.1em;">{emoji} <b>{name}</b></span>
                <span>{fav_symbol}</span>
            </div>
            <div style="margin-top: 5px; font-size: 0.9em; color: #aaa;">
                Niveau : <b>{level}</b> / {max_level}
            </div>
        </div>
    """, unsafe_allow_html=True)

def update_account_composition(player_tag, comp_name):
    conn = get_db_client()
    conn.execute("UPDATE accounts SET active_composition = ? WHERE player_tag = ?", [comp_name, player_tag])

@st.cache_data(ttl=10)
def get_cached_compositions():
    conn = get_db_client()
    try:
        res = conn.execute("SELECT comp_name, town_hall_level, raw_data, details FROM compositions")
        return [row for row in res.rows]
    except Exception:
        res = conn.execute("SELECT comp_name, town_hall_level, details FROM compositions")
        return [row for row in res.rows]

@st.cache_data(ttl=10)
def get_cached_hero_equipment(hero_name):
    conn = get_db_client()
    res = conn.execute("SELECT equipment_name FROM hero_equipment_config WHERE hero_name = ?", [hero_name])
    return [row[0] for row in res.rows]

@st.cache_data(ttl=120)
def fetch_clan_war_league(clan_tag):
    api_token = os.environ.get("COC_API_TOKEN", "")
    formatted_tag = clan_tag.replace("#", "%23")
    url = f"https://api.clashofclans.com/v1/clans/{formatted_tag}/currentwar/leaguegroup"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            league_group = response.json()
            rounds_data = []
            for round_info in league_group.get("rounds", []):
                for war_tag in round_info.get("warTags", []):
                    if war_tag and war_tag != "#0":
                        formatted_war_tag = war_tag.replace("#", "%23")
                        war_url = f"https://api.clashofclans.com/v1/clanwarleagues/wars/{formatted_war_tag}"
                        war_resp = requests.get(war_url, headers=headers)
                        if war_resp.status_code == 200:
                            rounds_data.append(war_resp.json())
            return {"group": league_group, "wars": rounds_data}, None
    except Exception as e:
        return None, str(e)
    return None, "Aucune ligue de guerre active trouvée ou erreur API"

def update_all_accounts_from_api():
    """Met à jour le nom et l'Hôtel de Ville (TH) exact pour TOUS les comptes de la base via l'API joueur."""
    conn = get_db_client()
    try:
        accounts_res = conn.execute("SELECT player_tag FROM accounts")
        tags = [row[0] for row in accounts_res.rows]
    except Exception:
        tags = []

    if not tags:
        return

    api_token = os.environ.get("COC_API_TOKEN", "")
    headers = {"Authorization": f"Bearer {api_token}", "Accept": "application/json"}

    for tag in tags:
        try:
            formatted_tag = tag.replace("#", "%23")
            url = f"https://api.clashofclans.com/v1/players/{formatted_tag}"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                name = data.get("name")
                th = data.get("townHallLevel")
                
                conn.execute("""
                    UPDATE accounts 
                    SET name = ?, town_hall = ? 
                    WHERE player_tag = ?
                """, [name, th, tag])
        except Exception:
            pass
                    
def init_league_archives_table():
    """Initialise la table pour stocker les archives de ligues par mois."""
    conn = get_db_client()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS league_archives (
                month_key TEXT PRIMARY KEY,
                wars_json TEXT
            )
        """)
    except Exception:
        pass

def save_league_archive(month_key, wars_data):
    """Sauvegarde ou met à jour les données d'une ligue pour un mois donné (ex: 'Novembre')."""
    import json
    init_league_archives_table()
    conn = get_db_client()
    try:
        wars_str = json.dumps(wars_data)
        conn.execute("""
            INSERT INTO league_archives (month_key, wars_json)
            VALUES (?, ?)
            ON CONFLICT(month_key) DO UPDATE SET wars_json = excluded.wars_json
        """, [month_key, wars_str])
    except Exception as e:
        print(f"Erreur sauvegarde archive ligue: {e}")

def get_league_archive(month_key):
    """Récupère les données d'une ligue archivée pour un mois donné."""
    import json
    init_league_archives_table()
    conn = get_db_client()
    try:
        res = conn.execute("SELECT wars_json FROM league_archives WHERE month_key = ?", [month_key])
        rows = res.rows if hasattr(res, 'rows') else []
        if rows and rows[0] and rows[0][0]:
            data = rows[0][0]
            if isinstance(data, str):
                return json.loads(data)
            return data
    except Exception as e:
        print(f"Erreur lecture archive: {e}")
    return None

def get_all_archived_months():
    """Retourne la liste de tous les mois archivés."""
    init_league_archives_table()
    conn = get_db_client()
    try:
        res = conn.execute("SELECT month_key FROM league_archives ORDER BY month_key DESC")
        return [row[0] for row in res.rows]
    except Exception:
        return []

def init_ranked_leagues_table():
    """Initialise la table pour stocker le suivi des ligues classées hebdomadaires."""
    conn = get_db_client()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ranked_leagues (
                player_tag TEXT,
                week_key TEXT,
                status TEXT DEFAULT 'Prévu',
                attacks_done INTEGER DEFAULT 0,
                attacks_max INTEGER DEFAULT 8,
                stars_3 INTEGER DEFAULT 0,
                stars_2 INTEGER DEFAULT 0,
                stars_1 INTEGER DEFAULT 0,
                avg_destruction REAL DEFAULT 0.0,
                def_done INTEGER DEFAULT 0,
                def_max INTEGER DEFAULT 8,
                trophies_attack INTEGER DEFAULT 0,
                trophies_defense INTEGER DEFAULT 0,
                PRIMARY KEY (player_tag, week_key)
            )
        """)
    except Exception:
        pass
