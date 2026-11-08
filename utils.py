import streamlit as st
import requests
import libsql_client
import urllib.parse

HERO_PETS_LIST = [
    "L.A.S.S.I", "Mighty Yak", "Electro Owl", "Unicorn", 
    "Phoenix", "Poison Lizard", "Diggy", "Frosty", 
    "Spirit Fox", "Angry Jelly", "Sneezy"
]

SIEGE_MACHINES_LIST = [
    "Wall Wreck", "Battle Blimp", "Stone Slammer", 
    "Siege Barracks", "Log Launcher", "Flame Flinger", "Battle Drill"
]

@st.cache_resource
def get_db_client():
    url = st.secrets["TURSO_DATABASE_URL"]
    auth_token = st.secrets["TURSO_AUTH_TOKEN"]
    
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
        
    conn = libsql_client.create_client_sync(url=url, auth_token=auth_token)
    return conn

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

    # Table des favoris globale (uniquement item_name)
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
    return {row[0] for row in res.rows}

def add_db_favorite(item_name):
    conn = get_db_client()
    conn.execute("INSERT OR IGNORE INTO favorites (item_name) VALUES (?)", [item_name])

def remove_db_favorite(item_name):
    conn = get_db_client()
    conn.execute("DELETE FROM favorites WHERE item_name = ?", [item_name])

def get_all_accounts():
    conn = get_db_client()
    res = conn.execute("SELECT player_tag, name, town_hall, active_composition FROM accounts")
    return res.rows

def update_account_composition(player_tag, comp_name):
    conn = get_db_client()
    conn.execute("UPDATE accounts SET active_composition = ? WHERE player_tag = ?", [comp_name, player_tag])

def fetch_player_data(player_tag: str):
    clean_tag = player_tag.strip().upper()
    if not clean_tag.startswith("#"):
        clean_tag = "#" + clean_tag
        
    encoded_tag = urllib.parse.quote(clean_tag, safe='')
    url = f"https://api.clashofclans.com/v1/players/{encoded_tag}"
    
    headers = {
        "Authorization": f"Bearer {st.secrets['COC_API_TOKEN']}",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json(), None
    else:
        try:
            err_msg = response.json().get('message', 'Unknown error')
        except:
            err_msg = response.text
        return None, f"Erreur API ({response.status_code}) : {err_msg}"

def get_icon_emoji(name):
    if not name: return "⚔️"
    n = name.lower()
    if "king" in n: return "👑"
    if "queen" in n: return "👸"
    if "warden" in n: return "🧙‍♂️"
    if "champion" in n: return "🛡️"
    if "minion" in n: return "🦇"
    if "dragon" in n: return "🐉"
    if "pekka" in n: return "🤖"
    if "golem" in n: return "🗿"
    if "witch" in n: return "🧙‍♀️"
    if "wizard" in n: return "🧙‍♂️"
    if "hog" in n: return "🐗"
    if "valkyrie" in n: return "🪓"
    if "lava" in n: return "🌋"
    if "bowler" in n: return "🎳"
    if "electro" in n: return "⚡"
    if "ice" in n: return "❄️"
    if "healer" in n: return "👼"
    if "wall" in n: return "🧱"
    if "balloon" in n: return "🎈"
    if "miner" in n: return "⛏️"
    if "yeti" in n: return "🐻‍❄️"
    if "headhunter" in n: return "🗡️"
    if "apprentice" in n: return "🛡️"
    if "root" in n: return "🌱"
    if "druid" in n: return "🌿"
    if "l.a.s.s.i" in n or "dog" in n: return "🐕"
    if "yak" in n: return "🐂"
    if "owl" in n: return "🦉"
    if "unicorn" in n: return "🦄"
    if "phoenix" in n: return "🔥"
    if "lizard" in n: return "🦎"
    if "diggy" in n: return "🦫"
    if "frosty" in n: return "🧊"
    if "fox" in n: return "🦊"
    if "jelly" in n: return "🪼"
    if "blimp" in n or "slammer" in n or "flinger" in n or "launcher" in n or "barracks" in n or "drill" in n: return "🛒"
    if "ball" in n or "gauntlet" in n or "puppet" in n or "gem" in n or "vial" in n or "spike" in n or "boots" in n or "mirror" in n or "fireball" in n or "lance" in n or "rocket" in n or "tome" in n: return "🔮"
    return "⚔️"

def sort_items(items, current_favorites):
    def get_diff(item):
        lvl = item.get('level', 0)
        max_lvl = item.get('maxLevel', 0)
        return max_lvl - lvl

    favs = [i for i in items if i.get('name') in current_favorites]
    non_favs = [i for i in items if i.get('name') not in current_favorites]
    
    active_favs = sorted([i for i in favs if get_diff(i) > 0], key=get_diff)
    max_favs = [i for i in favs if get_diff(i) == 0]
    sorted_favs = active_favs + max_favs
    
    active_non_favs = sorted([i for i in non_favs if get_diff(i) > 0], key=get_diff)
    max_non_favs = [i for i in non_favs if get_diff(i) == 0]
    sorted_non_favs = active_non_favs + max_non_favs
    
    return sorted_favs + sorted_non_favs

def render_card(name, lvl, max_lvl, current_favorites, icon="⚔️"):
    remaining = max_lvl - lvl
    is_max = (remaining == 0)
    progress_pct = int(min(lvl / max_lvl, 1.0) * 100) if max_lvl > 0 else 0
    
    status_text = "Niv. MAX ✨" if is_max else f"Niv. {lvl} / {max_lvl} *(Reste {remaining})*"
    is_fav = name in current_favorites
    fav_icon = "⭐" if is_fav else "☆"
    
    with st.container(border=True):
        col_t, col_btn = st.columns([0.75, 0.25])
        with col_t:
            if is_max:
                st.markdown(f'<span class="max-title">{icon} {name}</span>', unsafe_allow_html=True)
            else:
                st.markdown(f"**{icon} {name}**")
        with col_btn:
            if st.button(fav_icon, key=f"fav_btn_{name}", help="Favori"):
                if is_fav:
                    remove_db_favorite(name)
                else:
                    add_db_favorite(name)
                st.rerun()
                
        if is_max:
            st.markdown(f":green[**{status_text}**]")
        else:
            st.caption(status_text)
            
        fill_class = "custom-progress-fill-green" if is_max else "custom-progress-fill-blue"
        bar_html = f"""
        <div class="custom-progress-bg">
            <div class="{fill_class}" style="width: {progress_pct}%;"></div>
        </div>
        """
        st.markdown(bar_html, unsafe_allow_html=True)
