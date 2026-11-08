import streamlit as st
import libsql_client
import os

# Liste officielle des familiers de héros (incluant Greedy Raven)
HERO_PETS_LIST = [
    "L.A.S.S.I", "Mighty Yak", "Electro Owl", "Unicorn", 
    "Phoenix", "Poison Lizard", "Diggy", "Frosty", 
    "Spirit Fox", "Angry Jelly", "Sneezy", "Greedy Raven"
]

# Liste des engins de siège
SIEGE_MACHINES_LIST = [
    "Wall Wrecker", "Battle Blimp", "Stone Slammer", "Siege Barracks", 
    "Log Launcher", "Flame Flinger", "Battle Drill"
]

def get_db_client():
    url = os.environ.get("TURSO_DATABASE_URL", "libsql://coc-dashboard-2neuf.turso.io")
    auth_token = os.environ.get("TURSO_AUTH_TOKEN", "")
    return libsql_client.create_client_sync(url=url, auth_token=auth_token)

def init_db():
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

def get_db_favorites():
    conn = get_db_client()
    res = conn.execute("SELECT item_name FROM favorites")
    return [row[0] for row in res.rows]

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

def update_account_composition(player_tag, comp_name):
    conn = get_db_client()
    conn.execute("UPDATE accounts SET active_composition = ? WHERE player_tag = ?", [comp_name, player_tag])
