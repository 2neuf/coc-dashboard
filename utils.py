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
    return libsql_client.create_client_sync(url=url, auth_token=auth_token)

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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                item_name TEXT PRIMARY KEY
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compositions (
                comp_name TEXT PRIMARY KEY,
                details TEXT
            )
        """)
        try:
            conn.execute("ALTER TABLE compositions ADD COLUMN town_hall_level INTEGER DEFAULT 18")
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
            INSERT OR IGNORE INTO accounts (player_tag, name, town_hall, active_composition) 
            VALUES (?, ?, ?, ?)
        """, ["#YJ0U9P89V", "Mini", 18, "Aucune"])
    except Exception as e:
        st.error(f"Erreur d'initialisation DB : {e}")

def get_all_accounts():
    conn = get_db_client()
    res = conn.execute("SELECT player_tag, name, town_hall, active_composition FROM accounts")
    accounts = []
    for row in res.rows:
        accounts.append({
            "tag": row[0],
            "name": row[1],
            "townHall": row[2],
            "active_composition": row[3] if len(row) > 3 else "Aucune"
        })
    return accounts

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

def get_icon_emoji(name):
    icons = {
        "Barbarian King": "👑", "Archer Queen": "🏹", "Grand Warden": "🧙‍♂️", "Royal Champion": "🛡️", "Minion Prince": "🦇",
        "L.A.S.S.I": "🐶", "Mighty Yak": "🐂", "Electro Owl": "🦉", "Unicorn": "🦄", 
        "Phoenix": "🔥", "Poison Lizard": "🦎", "Diggy": "🦫", "Frosty": "❄️", 
        "Spirit Fox": "🦊", "Angry Jelly": "🪼", "Sneezy": "🤧", "Greedy Raven": "🦅"
    }
    return icons.get(name, "⚔️")

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
