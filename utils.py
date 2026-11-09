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

def sync_league_players_to_db(league_data):
    """Enregistre automatiquement les membres du clan et leur niveau d'HDV trouvés dans la ligue."""
    if not league_data or not league_data.get("wars"):
        return
    conn = get_db_client()
    CLAN_TAG = "#2U0GCGPJU"
    for w in league_data.get("wars", []):
        if w and (w.get("clan", {}).get("tag") == CLAN_TAG or w.get("opponent", {}).get("tag") == CLAN_TAG):
            side = "clan" if w.get("clan", {}).get("tag") == CLAN_TAG else "opponent"
            for m in w.get(side, {}).get("members", []):
                m_tag = m.get("tag")
                m_name = m.get("name")
                m_th = m.get("townHallLevel", 18) # Récupère le vrai niveau d'HDV du joueur dans la guerre
                try:
                    # Insertion ou mise à jour de l'HDV si le joueur existe déjà
                    conn.execute("""
                        INSERT INTO accounts (player_tag, name, town_hall, active_composition, display_order)
                        VALUES (?, ?, ?, 'Aucune', 0)
                        ON CONFLICT(player_tag) DO UPDATE SET 
                            town_hall = excluded.town_hall,
                            name = excluded.name
                    """, [m_tag, m_name, m_th])
                except Exception:
                    pass
