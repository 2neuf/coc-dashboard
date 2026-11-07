import streamlit as st
import requests
import libsql_client
import urllib.parse
from datetime import datetime

st.set_page_config(page_title="CoC Multi-Account Dashboard", layout="wide", page_icon="🛡️")

# CSS pour uniformiser les cartes et styliser les barres de progression personnalisées
st.markdown("""
<style>
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
    .max-title {
        color: #22c55e !important;
        font-weight: bold;
    }
    .custom-progress-bg {
        background-color: #313244;
        border-radius: 4px;
        height: 8px;
        width: 100%;
        margin-top: 6px;
        overflow: hidden;
    }
    .custom-progress-fill-blue {
        background-color: #3b82f6;
        height: 100%;
        border-radius: 4px;
    }
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
            player_tag TEXT,
            item_name TEXT,
            PRIMARY KEY (player_tag, item_name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS compositions (
            comp_name TEXT PRIMARY KEY,
            details TEXT
        )
    """)
    
    conn.execute("""
        INSERT OR IGNORE INTO accounts (player_tag, name, town_hall, active_composition) 
        VALUES (?, ?, ?, ?)
    """, ["#YJ0U9P89V", "Mini", 18, "Aucune"])

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

HERO_PETS_LIST = [
    "L.A.S.S.I", "Mighty Yak", "Electro Owl", "Unicorn", 
    "Phoenix", "Poison Lizard", "Diggy", "Frosty", 
    "Spirit Fox", "Angry Jelly", "Sneezy"
]

SIEGE_MACHINES_LIST = [
    "Wall Wreck", "Battle Blimp", "Stone Slammer", 
    "Siege Barracks", "Log Launcher", "Flame Flinger", "Battle Drill"
]

# Dictionnaire complet et officiel des équipements par Héros
HERO_EQUIPMENT_MAPPING = {
    "Barbarian King": [
        "Giant Gauntlet", "Barbarian Puppet", "Earthquake Boots", 
        "Rage Vial", "Vambrace", "Spiky Ball"
    ],
    "Archer Queen": [
        "Giant Arrow", "Archer Puppet", "Invisibility Vial", 
        "Healer Puppet", "Magic Mirror", "Frozen Arrow"
    ],
    "Grand Warden": [
        "Life Gem", "Eternal Tome", "Healing Tome", "Fireball", "Lavaloon Puppet"
    ],
    "Royal Champion": [
        "Seeking Shield", "Hog Rider Puppet", "Haste Vial", 
        "Royal Gem", "Rocket Spear", "Electro Boots"
    ],
    "Minion Prince": [
        "Protector Puppet", "Henchman Pants", "Dark Orb", "Meteor Staff", "Dark Crown"
    ],
    "Dragon Duke": [
        "Fire Heart", "Blowtorch", "Electro Fang", "Jetpack", "Card Deck"
    ]
}

def get_icon_emoji(name):
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
            if st.button(fav_icon, key=f"fav_btn_{name}_{current_tag}", help="Favori"):
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
# 2. APP LAYOUT & NAVIGATION
# -------------------------------------------------------------------
st.title("🛡️ Clash of Clans Dashboard — Multi-Comptes")

try:
    init_db()
    st.sidebar.success("✅ Turso DB Connected")
except Exception as e:
    st.sidebar.error(f"❌ DB Error: {e}")

accounts_list = get_all_accounts()
account_options = {row[1]: row[0] for row in accounts_list}

st.sidebar.header("Gestion des Comptes")
selected_account_name = st.sidebar.selectbox("Choisir le compte actif", list(account_options.keys()))
current_tag = account_options[selected_account_name]
player_name = selected_account_name

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
            "INSERT OR REPLACE INTO accounts (player_tag, name, town_hall, active_composition) VALUES (?, ?, ?, COALESCE((SELECT active_composition FROM accounts WHERE player_tag = ?), 'Aucune'))",
            [data["tag"], player_name, data["townHallLevel"], data["tag"]]
        )
    except Exception as e:
        st.warning(f"Could not update Turso DB: {e}")

    tab_overview, tab_army, tab_troops, tab_config = st.tabs([
        "📊 Vue d'ensemble", 
        "⚔️ Héros, Familiers & Équipements", 
        "🧪 Troupes, Engins & Sorts", 
        "⚙️ Paramétrage Compositions"
    ])

    # -------------------------------------------------------------------
    # TAB 1: VUE D'ENSEMBLE MULTI-COMPTES
    # -------------------------------------------------------------------
    with tab_overview:
        st.subheader("📊 Vue d'ensemble de tous les joueurs")
        
        all_accs = get_all_accounts()
        overview_data = []
        
        conn_db = get_db_client()
        for acc in all_accs:
            p_tag, p_name, p_th, p_comp = acc[0], acc[1], acc[2], acc[3]
            
            p_data, p_err = fetch_player_data(p_tag)
            if not p_err and p_data:
                l_info = p_data.get("league")
                p_trophies = p_data.get("trophies", 0)
                if l_info and isinstance(l_info, dict) and l_info.get("name"):
                    l_name = l_info.get("name")
                else:
                    l_name = f"Légende ({p_trophies} 🏆)" if p_trophies >= 5000 else f"{p_trophies} 🏆"
            else:
                l_name = "Inconnu"
            
            comp_details_text = "Aucune"
            if p_comp and p_comp != "Aucune":
                comp_res = conn_db.execute("SELECT details FROM compositions WHERE comp_name = ?", [p_comp])
                if comp_res.rows:
                    comp_details_text = f"📌 {p_comp} — {comp_res.rows[0][0]}"
                else:
                    comp_details_text = p_comp

            overview_data.append({
                "Pseudo": p_name,
                "HDV": f"TH {p_th}",
                "Ligue": l_name,
                "Composition d'attaque": comp_details_text
            })
            
        st.dataframe(overview_data, width='stretch')

    # -------------------------------------------------------------------
    # TAB 2: HEROS, FAMILIERS & EQUIPEMENTS
    # -------------------------------------------------------------------
    with tab_army:
        st.subheader("👑 Héros")
        heroes = data.get("heroes", [])
        home_heroes = [h for h in heroes if h.get("village") == "home"]
        sorted_heroes = sort_items(home_heroes, current_favorites)
        if sorted_heroes:
            hero_cols = st.columns(len(sorted_heroes))
            for idx, hero in enumerate(sorted_heroes):
                with hero_cols[idx]:
                    render_card(hero['name'], hero.get("level"), hero.get("maxLevel"), current_tag, current_favorites, get_icon_emoji(hero['name']))
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
                    render_card(eq['name'], eq.get("level"), eq.get("maxLevel"), current_tag, current_favorites, get_icon_emoji(eq['name']))
        else:
            st.info("Aucun équipement trouvé.")

    # -------------------------------------------------------------------
    # TAB 3: TROUPES, ENGINS & SORTS
    # -------------------------------------------------------------------
    with tab_troops:
        st.subheader("🧪 Progression des Troupes (Village Principal)")
        raw_troops = [t for t in data.get("troops", []) if t.get("village"] == "home"]
        
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
        spells = [s for s in data.get("spells", []) if s.get("village"] == "home"]
        sorted_spells = sort_items(spells, current_favorites)
        
        if sorted_spells:
            spell_cols = st.columns(4)
            for idx, spell in enumerate(sorted_spells):
                col = spell_cols[idx % 4]
                with col:
                    render_card(spell['name'], spell.get("level"), spell.get("maxLevel"), current_tag, current_favorites, "🧪")
        else:
            st.info("Aucun sort trouvé.")

    # -------------------------------------------------------------------
    # TAB 4: PARAMÉTRAGE DES COMPOSITIONS D'ATTAQUE (Équipements par Héros garantis)
    # -------------------------------------------------------------------
    with tab_config:
        st.subheader("⚙️ Paramétrage des Compositions d'Attaque")
        
        comp_title = st.text_input("Nom de la composition (ex: Root Rider Spam)")
        
        st.markdown("### 👑 Sélection des Héros")
        available_heroes = [h['name'] for h in data.get("heroes", []) if h.get("village"] == "home"]
            
        hero_labels = [f"{get_icon_emoji(h)} {h}" for h in available_heroes]
        hero_map = {f"{get_icon_emoji(h)} {h}": h for h in available_heroes}
        
        selected_hero_labels = st.multiselect("Choisissez les héros à inclure", hero_labels, key="hero_multiselect")
        selected_heroes_comp = [hero_map[l] for l in selected_hero_labels]
        
        hero_custom_links = {}

        if selected_heroes_comp:
            st.markdown("---")
            st.markdown("### 🔗 Configuration des Héros sélectionnés (Familier & Équipements)")
            
            for hero in selected_heroes_comp:
                hero_icon = get_icon_emoji(hero)
                st.markdown(f"**{hero_icon} {hero}**")
                
                col_p, col_eq = st.columns(2)
                with col_p:
                    pet_options = ["Aucun"] + HERO_PETS_LIST
                    pet_labels = [f"{get_icon_emoji(p)} {p}" if p != "Aucun" else "🚫 Aucun" for p in pet_options]
                    selected_pet_idx = st.selectbox(f"Familier pour {hero}", range(len(pet_options)), format_func=lambda x: pet_labels[x], key=f"pet_{hero}")
                    pet_choice = pet_options[selected_pet_idx]
                
                with col_eq:
                    # Utiliser directement la liste officielle du dictionnaire pour ce héros (pour ne rien rater !)
                    hero_specific_eqs = HERO_EQUIPMENT_MAPPING.get(hero, [e['name'] for e in data.get("heroEquipment", [])])
                    
                    eq_labels = [f"{get_icon_emoji(e)} {e}" for e in hero_specific_eqs]
                    eq_map = {f"{get_icon_emoji(e)} {e}": e for e in hero_specific_eqs}
                    
                    selected_eq_labels = st.multiselect(f"Équipements pour {hero} (max 2)", eq_labels, key=f"eq_{hero}")
                    eq_choices = [eq_map[label] for label in selected_eq_labels]
                    
                    # Message d'invitation/alerte immédiat sous le champ si aucun équipement n'est sélectionné
                    if not eq_choices:
                        st.warning(f"⚠️ Veuillez joindre et sélectionner les équipements de **{hero}** (maximum 2).")
                
                hero_custom_links[hero] = {"pet": pet_choice, "equipment": eq_choices}
                st.divider()

        st.markdown("### 🧪 Troupes & Sorts de la Compo")
        available_troops = [t['name'] for t in raw_troops if not should_exclude(t.get("name", ""))]
        troop_labels = [f"{get_icon_emoji(t)} {t}" for t in available_troops]
        troop_map = {f"{get_icon_emoji(t)} {t}": t for t in available_troops}
        selected_troop_labels = st.multiselect("Sélectionner les Troupes", troop_labels, key="troops_multiselect")
        selected_troops_comp = [troop_map[l] for l in selected_troop_labels]
        
        available_spells = [s['name'] for s in spells]
        spell_labels = [f"🧪 {s}" for s in available_spells]
        spell_map = {f"🧪 {s}": s for s in available_spells}
        selected_spell_labels = st.multiselect("Sélectionner les Sorts", spell_labels, key="spells_multiselect")
        selected_spells_comp = [spell_map[l] for l in selected_spell_labels]
        
        if st.button("Enregistrer la composition", type="primary"):
            if not comp_title:
                st.error("❌ Veuillez saisir un nom pour la composition.")
            else:
                too_many_eq = False
                for h, config in hero_custom_links.items():
                    if len(config['equipment']) > 2:
                        too_many_eq = True
                        st.error(f"❌ Le héros {h} possède plus de 2 équipements sélectionnés (maximum 2 autorisés).")
                
                if not too_many_eq:
                    heroes_summary_list = []
                    for h, config in hero_custom_links.items():
                        pet_display = f"{get_icon_emoji(config['pet'])} {config['pet']}" if config['pet'] != "Aucun" else "Aucun"
                        eq_display = ", ".join([f"{get_icon_emoji(e)} {e}" for e in config['equipment']]) if config['equipment'] else "Aucun (À renseigner)"
                        heroes_summary_list.append(f"{get_icon_emoji(h)} {h} (Pet: {pet_display} | Équipements: {eq_display})")

                    troops_display = ", ".join([f"{get_icon_emoji(t)} {t}" for t in selected_troops_comp]) if selected_troops_comp else "Aucune"
                    spells_display = ", ".join([f"🧪 {s}" for s in selected_spells_comp]) if selected_spells_comp else "Aucun"

                    comp_details = f"Héros -> {' / '.join(heroes_summary_list) if heroes_summary_list else 'Aucun'} | Troupes: {troops_display} | Sorts: {spells_display}"
                    
                    conn = get_db_client()
                    conn.execute("INSERT OR REPLACE INTO compositions (comp_name, details) VALUES (?, ?)", [comp_title, comp_details])
                    st.success(f"Composition '{comp_title}' enregistrée avec succès !")
                    st.rerun()

        st.divider()
        st.subheader("🎯 Assigner une composition au joueur actif")
        
        conn = get_db_client()
        comps_res = conn.execute("SELECT comp_name FROM compositions")
        all_comps = [row[0] for row in comps_res.rows]
        
        if all_comps:
            current_assigned = conn.execute("SELECT active_composition FROM accounts WHERE player_tag = ?", [current_tag]).rows[0][0]
            selected_comp = st.selectbox("Choisir la compo pour ce joueur", all_comps, index=all_comps.index(current_assigned) if current_assigned in all_comps else 0)
            
            if st.button("Sauvegarder l'association pour ce compte"):
                update_account_composition(current_tag, selected_comp)
                st.success(f"Composition '{selected_comp}' assignée à {player_name} !")
                st.rerun()
        else:
            st.info("Aucune composition enregistrée pour le moment. Créez-en une ci-dessus.")
