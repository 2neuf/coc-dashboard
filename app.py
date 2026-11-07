import streamlit as st
import requests
import libsql_client
from datetime import datetime, timedelta

st.set_page_config(page_title="CoC Multi-Account Dashboard", layout="wide", page_icon="🛡️")

# -------------------------------------------------------------------
# 1. DATABASE & API SETUP
# -------------------------------------------------------------------
@st.cache_resource
def get_db_client():
    url = st.secrets["TURSO_DATABASE_URL"]
    auth_token = st.secrets["TURSO_AUTH_TOKEN"]
    
    # Conversion de libsql:// en https:// pour forcer le transport HTTP stable
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
        
    conn = libsql_client.create_client_sync(url=url, auth_token=auth_token)
    return conn

def init_db():
    conn = get_db_client()
    # Create basic tables if they don't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            player_tag TEXT PRIMARY KEY,
            name TEXT,
            town_hall INTEGER,
            gold_pass_boost INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS builder_timers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_tag TEXT,
            builder_slot INTEGER,
            building_name TEXT,
            finish_time DATETIME
        )
    """)
    conn.commit()

# Helper function to query CoC API
def fetch_player_data(player_tag: str):
    # Format tag (replace # with %23 for URL safety)
    formatted_tag = player_tag.strip().replace("#", "%23")
    url = f"https://api.clashofclans.com/v1/players/{formatted_tag}"
    headers = {
        "Authorization": f"Bearer {st.secrets['COC_API_TOKEN']}",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json(), None
    else:
        return None, f"Error {response.status_code}: {response.json().get('message', 'Failed to fetch data')}"

# -------------------------------------------------------------------
# 2. APP LAYOUT
# -------------------------------------------------------------------
st.title("🛡️ Clash of Clans Dashboard — MVP")

# Initialize DB tables
try:
    init_db()
    st.sidebar.success("✅ Turso DB Connected")
except Exception as e:
    st.sidebar.error(f"❌ DB Error: {e}")

st.sidebar.header("Account Setup")
player_tag_input = st.sidebar.text_input("Enter Player Tag", placeholder="#2ABC1234")

if st.sidebar.button("Fetch Account Data"):
    if player_tag_input:
        st.session_state["active_tag"] = player_tag_input
    else:
        st.sidebar.warning("Please enter a valid tag!")

# Display Data if Tag is provided
if "active_tag" in st.session_state and st.session_state["active_tag"]:
    current_tag = st.session_state["active_tag"]
    
    with st.spinner("Fetching data from Supercell API..."):
        data, err = fetch_player_data(current_tag)
    
    if err:
        st.error(err)
    else:
        # Save or update account in Turso DB
        try:
            conn = get_db_client()
            conn.execute(
                "INSERT OR REPLACE INTO accounts (player_tag, name, town_hall) VALUES (?, ?, ?)",
                (data["tag"], data["name"], data["townHallLevel"])
            )
            conn.commit()
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
        tab_army, tab_farm, tab_war = st.tabs(["⚔️ Army & Equipment", "🚜 Farm & Builders", "🛡️ War & CWL"])

        with tab_army:
            st.subheader("Heroes & Hero Equipment")
            
            # Heroes
            heroes = data.get("heroes", [])
            if heroes:
                hero_cols = st.columns(len(heroes))
                for idx, hero in enumerate(heroes):
                    with hero_cols[idx]:
                        st.metric(hero['name'], f"Lvl {hero['level']} / {hero['maxLevel']}")
            else:
                st.info("No hero data available.")
                
            st.subheader("Hero Equipment")
            equipment = [item for item in data.get("heroEquipment", [])]
            if equipment:
                eq_cols = st.columns(min(4, len(equipment)))
                for idx, eq in enumerate(equipment):
                    col_idx = idx % 4
                    eq_cols[col_idx].write(f"**{eq['name']}**: Level {eq['level']} (Max {eq['maxLevel']})")
            else:
                st.info("No equipment unlocked/found.")

        with tab_farm:
            st.subheader("Builder Timers & Resources")
            st.info("Next step: We will add custom inputs to track active builder upgrades and resources here.")

        with tab_war:
            st.subheader("War Performance")
            st.write(f"**Attacks Won:** {data.get('attackWins', 0)}")
            st.write(f"**Defenses Won:** {data.get('defenseWins', 0)}")
            st.write(f"**Clan:** {data.get('clan', {}).get('name', 'No Clan')}")
