import streamlit as st
import requests
import libsql_client
import urllib.parse
from datetime import datetime, timedelta

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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS builder_timers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_tag TEXT,
            builder_slot INTEGER,
            building_name TEXT,
            finish_time TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resource_logs (
            player_tag TEXT,
            updated_at TEXT,
            gold INTEGER,
            elixir INTEGER,
            dark_elixir INTEGER,
            shiny_ore INTEGER,
            glowy_ore INTEGER,
            starry_ore INTEGER
        )
    """)

import urllib.parse
import re

def fetch_player_data(player_tag: str):
    # Nettoyage rigoureux : enlève les espaces et force les majuscules
    clean_tag = player_tag.strip().upper()
    
    # S'assure que le tag commence bien par un #
    if not clean_tag.startswith("#"):
        clean_tag = "#" + clean_tag
        
    # Encodage sécurisé de l'URL pour l'API Supercell
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
        return None, f"Error {response.status_code}: {response.json().get('message', 'Failed to fetch data')}"
# -------------------------------------------------------------------
# 2. APP LAYOUT
# -------------------------------------------------------------------
st.title("🛡️ Clash of Clans Dashboard — MVP")

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

if "active_tag" in st.session_state and st.session_state["active_tag"]:
    current_tag = st.session_state["active_tag"]
    
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
        tab_army, tab_farm, tab_war = st.tabs(["⚔️ Army & Equipment", "🚜 Farm & Builders", "🛡️ War & CWL"])

        with tab_army:
            st.subheader("Heroes & Hero Equipment")
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
            st.subheader("🚜 Builder Timers & Upgrades")
            
            with st.form("builder_form"):
                col_b1, col_b2, col_b3 = st.columns(3)
                with col_b1:
                    b_slot = st.selectbox("Builder Slot", [1, 2, 3, 4, 5, 6])
                with col_b2:
                    b_name = st.text_input("Building / Upgrade Name", placeholder="Archer Tower 15")
                with col_b3:
                    b_days = st.number_input("Days to complete", min_value=0.0, max_value=30.0, value=3.0, step=0.5)
                
                submitted = st.form_submit_button("Assign Builder")
                if submitted and b_name:
                    finish_time = datetime.now() + timedelta(days=b_days)
                    try:
                        conn = get_db_client()
                        conn.execute("DELETE FROM builder_timers WHERE player_tag = ? AND builder_slot = ?", [current_tag, b_slot])
                        conn.execute(
                            "INSERT INTO builder_timers (player_tag, builder_slot, building_name, finish_time) VALUES (?, ?, ?, ?)",
                            [current_tag, b_slot, b_name, finish_time.strftime("%Y-%m-%d %H:%M:%S")]
                        )
                        st.success(f"Builder {b_slot} assigned to {b_name}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving builder: {e}")

            st.markdown("### Active Builders Status")
            try:
                conn = get_db_client()
                rs = conn.execute("SELECT builder_slot, building_name, finish_time FROM builder_timers WHERE player_tag = ?", [current_tag])
                rows = rs.rows
                
                if rows:
                    for row in rows:
                        slot, name, f_time_str = row[0], row[1], row[2]
                        f_time = datetime.strptime(f_time_str, "%Y-%m-%d %H:%M:%S")
                        time_left = f_time - datetime.now()
                        
                        col_info, col_action = st.columns([4, 1])
                        with col_info:
                            if time_left.total_seconds() > 0:
                                days, remainder = divmod(int(time_left.total_seconds()), 86400)
                                hours, remainder = divmod(remainder, 3600)
                                minutes, _ = divmod(remainder, 60)
                                st.info(f"🔨 **Builder {slot}**: {name} — Finishes in **{days}d {hours}h {minutes}m**")
                            else:
                                st.success(f"✨ **Builder {slot}**: {name} — **Ready!**")
                        with col_action:
                            if st.button("Free Builder", key=f"free_{slot}"):
                                conn.execute("DELETE FROM builder_timers WHERE player_tag = ? AND builder_slot = ?", [current_tag, slot])
                                st.rerun()
                else:
                    st.info("No active builders tracked. Use the form above to assign one!")
            except Exception as e:
                st.warning(f"Could not load builders: {e}")

        with tab_war:
            st.subheader("War Performance")
            st.write(f"**Attacks Won:** {data.get('attackWins', 0)}")
            st.write(f"**Defenses Won:** {data.get('defenseWins', 0)}")
            st.write(f"**Clan:** {data.get('clan', {}).get('name', 'No Clan')}")
