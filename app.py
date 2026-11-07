import streamlit as st
import requests
import libsql_client
import urllib.parse
from datetime import datetime

st.set_page_config(page_title="CoC Multi-Account Dashboard", layout="wide", page_icon="🛡️")

# Injection CSS pour harmoniser les hauteurs et styliser les cartes Max en vert
st.markdown("""
<style>
    /* Uniformise la hauteur minimale des conteneurs */
    [data-testid="stVerticalBlockBorderWrapper"] {
        min-height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    /* Style pour les cartes au niveau max (fond vert sombre et bordure verte) */
    .max-card {
        background-color: rgba(20, 83, 45, 0.25) !important;
        border: 1px solid rgba(34, 197, 94, 0.6) !important;
        border-radius: 8px;
        padding: 10px;
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            player_tag TEXT PRIMARY KEY,
            name TEXT,
            town_hall INTEGER,
            gold_pass_boost INTEGER DEFAULT 0
        )
    """)

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

# Liste officielle des familiers
HERO_PETS_LIST = [
    "L.A.S.S.I", "Mighty Yak", "Electro Owl", "Unicorn", 
    "Phoenix", "Poison Lizard", "Diggy", "Frosty", 
    "Spirit Fox", "Angry Jelly", "Furnace"
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
    return "⚔️"

# -------------------------------------------------------------------
# 2. APP LAYOUT
# -------------------------------------------------------------------
st.title("🛡️ Clash of Clans Dashboard — MVP")

try:
    init_db()
    st.sidebar.success("✅ Turso DB Connected")
except Exception as e:
    st.sidebar.error(f"❌ DB Error: {e}")

st.sidebar.header("Account Active")
current_tag = "#YJ0U9P89V"
st.sidebar.info(f"Tag ciblé : **{current_tag}**")

with st.spinner("Fetching data from Supercell API..."):
    data, err = fetch_player_data(current_tag)

if err:
    st.error(err)
else:
    try:
        conn = get_db_client()
        conn.execute(
            "INSERT OR REPLACE INTO accounts (player_tag, name, town_hall) VALUES (?, ?, ?)",
            [data["tag"], data["name"], data["townHallLevel"]]
        )
    except Exception as e:
        st.warning(f"Could not update Turso DB: {e}")

    # Account Summary Header
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Player Name", data.get("name"))
    col2.metric("Town Hall Level", f"TH {data.get('townHallLevel')}")
    col3.metric("Trophies", data.get("trophies"))
    col4.metric("War Stars", data.get("warStars"))

    st.divider()

    # Tabs Layout
    tab_army, tab_troops, tab_war = st.tabs(["⚔️ Héros, Familiers & Équipements", "🧪 Troupes & Sorts", "🛡️ War & Profil"])

    with tab_army:
        st.subheader("👑 Héros")
        heroes = data.get("heroes", [])
        home_heroes = [h for h in heroes if h.get("village") == "home"]
        if home_heroes:
            hero_cols = st.columns(len(home_heroes))
            for idx, hero in enumerate(home_heroes):
                with hero_cols[idx]:
                    lvl = hero.get("level")
                    max_lvl = hero.get("maxLevel")
                    progress = min(lvl / max_lvl, 1.0) if max_lvl > 0 else 0
                    remaining = max_lvl - lvl
                    is_max = (remaining == 0)
                    
                    container = st.container(border=True)
                    with container:
                        if is_max:
                            st.markdown(f'<div class="max-card">', unsafe_allow_html=True)
                        
                        st.markdown(f"**👑 {hero['name']}**")
                        if is_max:
                            st.caption(f"Niv. {lvl} / {max_lvl} — **Max ✨**")
                        else:
                            st.caption(f"Niv. {lvl} / {max_lvl} *(Reste {remaining})*")
                        st.progress(progress)
                        
                        if is_max:
                            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Aucun héros trouvé.")
                
        st.subheader("🐾 Familiers de Héros (Pets)")
        raw_troops_for_pets = data.get("troops", [])
        pets = [t for t in raw_troops_for_pets if t.get("name") in HERO_PETS_LIST]
        
        if pets:
            pet_cols = st.columns(4)
            for idx, pet in enumerate(pets):
                col = pet_cols[idx % 4]
                lvl = pet.get("level")
                max_lvl = pet.get("maxLevel")
                remaining = max_lvl - lvl
                progress = min(lvl / max_lvl, 1.0) if max_lvl > 0 else 0
                icon = get_icon_emoji(pet['name'])
                is_max = (remaining == 0)
                
                with col:
                    container = st.container(border=True)
                    with container:
                        if is_max:
                            st.markdown(f'<div class="max-card">', unsafe_allow_html=True)
                            
                        st.markdown(f"**{icon} {pet['name']}**")
                        if is_max:
                            st.caption(f"Niv. {lvl} / {max_lvl} — **Max ✨**")
                        else:
                            st.caption(f"Niv. {lvl} / {max_lvl} *(Reste {remaining})*")
                        st.progress(progress)
                        
                        if is_max:
                            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Aucun familier trouvé.")

        st.subheader("⚔️ Équipements de Héros")
        equipment = data.get("heroEquipment", [])
        if equipment:
            eq_cols = st.columns(4)
            for idx, eq in enumerate(equipment):
                col = eq_cols[idx % 4]
                lvl = eq.get("level")
                max_lvl = eq.get("maxLevel")
                progress = min(lvl / max_lvl, 1.0) if max_lvl > 0 else 0
                remaining = max_lvl - lvl
                is_max = (remaining == 0)
                
                with col:
                    container = st.container(border=True)
                    with container:
                        if is_max:
                            st.markdown(f'<div class="max-card">', unsafe_allow_html=True)
                            
                        st.markdown(f"**🔮 {eq['name']}**")
                        if is_max:
                            st.caption(f"Niv. {lvl} / {max_lvl} — **Max ✨**")
                        else:
                            st.caption(f"Niv. {lvl} / {max_lvl} *(Reste {remaining})*")
                        st.progress(progress)
                        
                        if is_max:
                            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Aucun équipement trouvé.")

    with tab_troops:
        st.subheader("🧪 Progression des Troupes (Village Principal)")
        raw_troops = [t for t in data.get("troops", []) if t.get("village") == "home"]
        
        def should_exclude(name):
            name_lower = name.lower()
            is_super = "super" in name_lower or name in ["Sneaky Goblin", "Rocket Balloon", "Inferno Dragon"]
            is_pet = name in HERO_PETS_LIST
            return is_super or is_pet
        
        troops = [t for t in raw_troops if not should_exclude(t.get("name", ""))]
        
        if troops:
            cols = st.columns(4)
            for idx, troop in enumerate(troops):
                col = cols[idx % 4]
                lvl = troop.get("level")
                max_lvl = troop.get("maxLevel")
                remaining = max_lvl - lvl
                progress = min(lvl / max_lvl, 1.0) if max_lvl > 0 else 0
                icon = get_icon_emoji(troop['name'])
                is_max = (remaining == 0)
                
                with col:
                    container = st.container(border=True)
                    with container:
                        if is_max:
                            st.markdown(f'<div class="max-card">', unsafe_allow_html=True)
                            
                        st.markdown(f"**{icon} {troop['name']}**")
                        if is_max:
                            st.caption(f"Niv. {lvl} / {max_lvl} — **Max ✨**")
                        else:
                            st.caption(f"Niv. {lvl} / {max_lvl} *(Reste {remaining})*")
                        st.progress(progress)
                        
                        if is_max:
                            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Aucune troupe trouvée.")

        st.subheader("⚡ Progression des Sorts (Village Principal)")
        spells = [s for s in data.get("spells", []) if s.get("village") == "home"]
        
        if spells:
            spell_cols = st.columns(4)
            for idx, spell in enumerate(spells):
                col = spell_cols[idx % 4]
                lvl = spell.get("level")
                max_lvl = spell.get("maxLevel")
                remaining = max_lvl - lvl
                progress = min(lvl / max_lvl, 1.0) if max_lvl > 0 else 0
                is_max = (remaining == 0)
                
                with col:
                    container = st.container(border=True)
                    with container:
                        if is_max:
                            st.markdown(f'<div class="max-card">', unsafe_allow_html=True)
                            
                        st.markdown(f"**🧪 {spell['name']}**")
                        if is_max:
                            st.caption(f"Niv. {lvl} / {max_lvl} — **Max ✨**")
                        else:
                            st.caption(f"Niv. {lvl} / {max_lvl} *(Reste {remaining})*")
                        st.progress(progress)
                        
                        if is_max:
                            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Aucun sort trouvé.")

    with tab_war:
        st.subheader("📊 Performances de Guerre & Profil")
        col_w1, col_w2, col_w3 = st.columns(3)
        col_w1.metric("Attaques gagnées", data.get('attackWins', 0))
        col_w2.metric("Défenses gagnées", data.get('defenseWins', 0))
        col_w3.metric("Clan", data.get('clan', {}).get('name', 'Aucun clan'))
