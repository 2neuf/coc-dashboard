import streamlit as st
import requests
import libsql_client
import urllib.parse
from datetime import datetime

st.set_page_config(page_title="CoC Multi-Account Dashboard", layout="wide", page_icon="🛡️")

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

    # Tabs Layout (Sans l'onglet farm, recentré sur l'armée, les troupes/sorts et la guerre)
    tab_army, tab_troops, tab_war = st.tabs(["⚔️ Héros & Équipements", "🧪 Troupes & Sorts", "🛡️ War & Profil"])

    with tab_army:
        st.subheader("Héros")
        heroes = data.get("heroes", [])
        # Filtrer uniquement le village principal si besoin, ou tout afficher
        home_heroes = [h for h in heroes if h.get("village") == "home"]
        if home_heroes:
            hero_cols = st.columns(len(home_heroes))
            for idx, hero in enumerate(home_heroes):
                with hero_cols[idx]:
                    st.metric(hero['name'], f"Lvl {hero['level']} / {hero['maxLevel']}")
        else:
            st.info("Aucun héros trouvé.")
                
        st.subheader("Équipements de Héros")
        equipment = data.get("heroEquipment", [])
        if equipment:
            eq_cols = st.columns(min(4, len(equipment)))
            for idx, eq in enumerate(equipment):
                col_idx = idx % 4
                eq_cols[col_idx].write(f"**{eq['name']}**\n\nNiveau {eq['level']} (Max {eq['maxLevel']})")
        else:
            st.info("Aucun équipement trouvé.")

    with tab_troops:
        st.subheader("Progression des Troupes (Village Principal)")
        troops = [t for t in data.get("troops", []) if t.get("village") == "home"]
        
        if troops:
            # Affichage sous forme de grille compacte
            cols = st.columns(4)
            for idx, troop in enumerate(troops):
                col = cols[idx % 4]
                lvl = troop.get("level")
                max_lvl = troop.get("maxLevel")
                # Calcul des niveaux restants
                remaining = max_lvl - lvl
                
                with col:
                    if remaining == 0:
                        st.success(f"**{troop['name']}**\n\nMax ({lvl}/{max_lvl}) ✨")
                    else:
                        st.info(f"**{troop['name']}**\n\nNiveau {lvl} / {max_lvl}\n*(Reste {remaining} niv.)*")
        else:
            st.info("Aucune troupe trouvée.")

        st.subheader("Progression des Sorts (Village Principal)")
        spells = [s for s in data.get("spells", []) if s.get("village") == "home"]
        
        if spells:
            spell_cols = st.columns(4)
            for idx, spell in enumerate(spells):
                col = spell_cols[idx % 4]
                lvl = spell.get("level")
                max_lvl = spell.get("maxLevel")
                remaining = max_lvl - lvl
                
                with col:
                    if remaining == 0:
                        st.success(f"**{spell['name']}**\n\nMax ({lvl}/{max_lvl}) ✨")
                    else:
                        st.info(f"**{spell['name']}**\n\nNiveau {lvl} / {max_lvl}\n*(Reste {remaining} niv.)*")
        else:
            st.info("Aucun sort trouvé.")

    with tab_war:
        st.subheader("Performances de Guerre")
        st.write(f"**Attaques gagnées:** {data.get('attackWins', 0)}")
        st.write(f"**Défenses gagnées:** {data.get('defenseWins', 0)}")
        st.write(f"**Clan:** {data.
