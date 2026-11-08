import streamlit as st
from utils import sort_items, render_card, get_icon_emoji, HERO_PETS_LIST, SIEGE_MACHINES_LIST

def render_tab_troops(data, current_favorites):
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
                render_card(troop.get('name'), troop.get("level"), troop.get("maxLevel"), current_favorites, get_icon_emoji(troop.get('name', '')))
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
                render_card(siege.get('name'), siege.get("level"), siege.get("maxLevel"), current_favorites, get_icon_emoji(siege.get('name', '')))
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
                render_card(spell.get('name'), spell.get("level"), spell.get("maxLevel"), current_favorites, "🧪")
    else:
        st.info("Aucun sort trouvé.")
