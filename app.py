import streamlit as st
import requests
import libsql_client
import urllib.parse
from datetime import datetime

st.set_page_config(page_title="CoC Multi-Account Dashboard", layout="wide", page_icon="🛡️")

# CSS pour uniformiser les cartes et styliser les barres de progression personnalisées
st.markdown("""
<style>
    /* Hauteur et dimensions strictes et égales pour toutes les cartes */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #1e1e2e;
        border-radius: 10px;
        border: 1px solid #313244;
        padding: 8px;
        min-height: 135px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    /* Style élégant pour les titres max */
    .max-title {
        color: #22c55e !important;
        font-weight: bold;
    }

    /* Conteneur de la barre de progression custom */
    .custom-progress-bg {
        background-color: #313244;
        border-radius: 4px;
        height: 8px;
        width: 100%;
        margin-top: 6px;
        overflow: hidden;
    }
    /* Remplissage bleu (normal) */
    .custom-progress-fill-blue {
        background-color: #3b82f6;
        height: 100%;
        border-radius: 4px;
    }
    /* Remplissage vert (max) */
    .custom-progress-fill-green {
        background-color: #22c55e;
        height: 100%;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# 1. DATABASE & API SETUP
# -------------------------------------------------------------------
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
    # Table des comptes (avec le nom "Mini" configuré en dur pour le tag cible)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            player_tag TEXT PRIMARY KEY,
            name TEXT,
            town_hall INTEGER,
            gold_pass_boost INTEGER DEFAULT 0
        )
    """)
    # Table dédiée pour stocker les favoris par joueur/pseudo
    conn.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            player_tag TEXT,
            item_name TEXT,
            PRIMARY KEY (player_tag, item_name)
        )
    """)
    
    # Insertion en dur du joueur "Mini"
    conn.execute("""
        INSERT OR IGNORE INTO accounts (player_tag, name, town_hall) 
        VALUES (?, ?, ?)
    """, ["#YJ0U9P89V", "Mini", 18])

def get_db_favorites(player_tag):
    conn = get_db_client()
    res = conn.execute("SELECT item_name FROM favorites WHERE player_tag = ?", [player_tag])
    return {row[0] for row in res.rows}

def add_db_favorite(player_tag, item_name):
    conn = get_db_client()
    conn.execute("INSERT OR IGNORE INTO favorites (player_tag, item_name) VALUES (?, ?)", [player_tag, item_name])

def remove_db_favorite(player_tag, item_name):
    conn = get_db_client()
    conn.execute("DELETE FROM favorites WHERE player_tag = ? AND item_name = ?", [player_tag, item_name])

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

# Liste officielle des familiers (avec Sneezy)
HERO_PETS_LIST = [
    "L.A.S.S.I", "Mighty Yak", "Electro Owl", "Unicorn", 
    "Phoenix", "Poison Lizard", "Diggy", "Frosty", 
    "Spirit Fox", "Angry Jelly", "Sneezy"
]

# Liste officielle des engins de siège
SIEGE_MACHINES_LIST = [
    "Wall Wreck", "Battle Blimp", "Stone Slammer", 
    "Siege Barracks", "Log Launcher", "Flame Flinger", "Battle Drill"
]

def get_icon_emoji(name):
    n = name.lower()
    if "dragon" in n: return "🐉"
    if "pekka" in n: return "🤖"
    if "golem" in n: return "🗿"
    if "witch" in n: return "🧙‍♀️"
    if "wizard" in n: return "🧙‍♂️"
    if "hog" in n: return "🐗"
    if "valkyrie" in n: return "🪓"
    if "minion" in n: return "🦇"
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

def render_card(name, lvl, max_lvl, current_tag, current_favorites, icon="⚔️"):
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
                    remove_db_favorite(current_tag, name)
                else:
                    add_db_favorite(current_tag, name)
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

# -------------------------------------------------------------------
# 2. APP LAYOUT
# -------------------------------------------------------------------
st.title("🛡️ Clash of Clans Dashboard — MVP")

try:
    init_db()
    st.sidebar.success("✅ Turso DB Connected")
except Exception as e:
    st.sidebar.error(f"❌ DB Error: {e}")

current_tag = "#YJ0U9P89V"
player_name = "Mini"

st.sidebar.header("Account Active")
st.sidebar.info(f"Pseudo : **{player_name}**\nTag : **{current_tag}**")

current_favorites = get_db_favorites(current_tag)

with st.spinner("Fetching data from Supercell API..."):
    data, err = fetch_player_data(current_tag)

if err:
    st.error(err)
else:
    try:
        conn = get_db_client()
        conn.execute(
            "INSERT OR REPLACE INTO accounts (player_tag, name, town_hall) VALUES (?, ?, ?)",
            [data["tag"], player_name, data["townHallLevel"]]
        )
    except Exception as e:
        st.warning(f"Could not update Turso DB: {e}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Player Name", player_name)
    col2.metric("Town Hall Level", f"TH {data.get('townHallLevel')}")
    col3.metric("Trophies", data.get("trophies"))
    col4.metric("War Stars", data.get("warStars"))

    st.divider()

    tab_army, tab_troops, tab_war = st.tabs(["⚔️ Héros, Familiers & Équipements", "🧪 Troupes & Sorts", "🛡️ War & Profil"])

    with tab_army:
        st.subheader("👑 Héros")
        heroes = data.get("heroes", [])
        home_heroes = [h for h in heroes if h.get("village") == "home"]
        sorted_heroes = sort_items(home_heroes, current_favorites)
        if sorted_heroes:
            hero_cols = st.columns(len(sorted_heroes))
            for idx, hero in enumerate(sorted_heroes):
                with hero_cols[idx]:
                    render_card(hero['name'], hero.get("level"), hero.get("maxLevel"), current_tag, current_favorites, "👑")
        else:
            st.info("Aucun héros trouvé.")
                
        st.subheader("🐾 Familiers de Héros (Pets)")
        raw_troops_for_pets = data.get("troops", [])
        pets = [t for t in raw_troops_for_pets if t.get("name") in HERO_PETS_LIST]
        sorted_pets = sort_items(pets, current_favorites)
        
        if sorted_pets:
            pet_cols = st.columns(4)
            for idx, pet in enumerate(sorted_pets):
                col = pet_cols[idx % 4]
                with col:
                    render_card(pet['name'], pet.get("level"), pet.get("maxLevel"), current_tag, current_favorites, get_icon_emoji(pet['name']))
        else:
            st.info("Aucun familier trouvé.")

        st.subheader("⚔️ Équipements de Héros")
        equipment = data.get("heroEquipment", [])
        sorted_eq = sort_items(equipment, current_favorites)
        if sorted_eq:
            eq_cols = st.columns(4)
            for idx, eq in enumerate(sorted_eq):
                col = eq_cols[idx % 4]
                with col:
                    render_card(eq['name'], eq.get("level"), eq.get("maxLevel"), current_tag, current_favorites, "🔮")
        else:
            st.info("Aucun équipement trouvé.")

    with tab_troops:
        st.subheader("🧪 Progression des Troupes (Village Principal)")
        raw_troops = [t for t in data.get("troops", []) if t.get("village") == "home"]
        
        def should_exclude(name):
            name_lower = name.lower()
            is_super = "super" in name_lower or name in ["Sneaky Goblin", "Rocket Balloon", "Inferno Dragon"]
            is_pet = name in HERO_PETS_LIST
            is_siege = name in SIEGE_MACHINES_LIST
            return is_super or is_pet or is_siege
        
        troops = [t for t in raw_troops if not should_exclude(t.get("name", ""))]
        sorted_troops = sort_items(troops, current_favorites)
        
        if sorted_troops:
            cols = st.columns(4)
            for idx, troop in enumerate(sorted_troops):
                col = cols[idx % 4]
                with col:
                    render_card(troop['name'], troop.get("level"), troop.get("maxLevel"), current_tag, current_favorites, get_icon_emoji(troop['name']))
        else:
            st.info("Aucune troupe trouvée.")

        st.subheader("🛒 Engins de Siège")
        siege_machines = [t for t in raw_troops if t.get("name") in SIEGE_MACHINES_LIST]
        sorted_siege = sort_items(siege_machines, current_favorites)
        
        if sorted_siege:
            siege_cols = st.columns(4)
            for idx, siege in enumerate(sorted_siege):
                col = siege_cols[idx % 4]
                with col:
                    render_card(siege['name'], siege.get("level"), siege.get("maxLevel"), current_tag, current_favorites, get_icon_emoji(siege['name']))
        else:
            st.info("Aucun engin de siège trouvé.")

        st.subheader("⚡ Progression des Sorts (Village Principal)")
        spells = [s for s in data.get("spells", []) if s.get("village") == "home"]
        sorted_spells = sort_items(spells, current_favorites)
        
        if sorted_spells:
            spell_cols = st.columns(4)
            for idx, spell in enumerate(sorted_spells):
                col = spell_cols[idx % 4]
                with col:
                    render_card(spell['name'], spell.get("level"), spell.get("maxLevel"), current_tag, current_favorites, "🧪")
        else:
            st.info("Aucun sort trouvé.")

    with tab_war:
        st.subheader("📊 Performances de Guerre & Profil")
        col_w1, col_w2, col_w3 = st.columns(3)
        col_w1.metric("Attaques gagnées", data.get('attackWins', 0))
        col_w2.metric("Défenses gagnées", data.get('defenseWins', 0))
        col_w3.metric("Clan", data.get('clan', {}).get('name', 'Aucun clan'))
