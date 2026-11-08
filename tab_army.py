import streamlit as st
from utils import sort_items, render_card, get_icon_emoji, HERO_PETS_LIST

def render_tab_army(data, current_tag, current_favorites):
    st.subheader("👑 Héros")
    heroes = data.get("heroes", [])
    home_heroes = [h for h in heroes if h.get("village") == "home"]
    sorted_heroes = sort_items(home_heroes, current_favorites)
    if sorted_heroes:
        hero_cols = st.columns(len(sorted_heroes))
        for idx, hero in enumerate(sorted_heroes):
            with hero_cols[idx]:
                render_card(hero.get('name'), hero.get("level"), hero.get("maxLevel"), current_tag, current_favorites, get_icon_emoji(hero.get('name', '')))
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
                render_card(pet.get('name'), pet.get("level"), pet.get("maxLevel"), current_tag, current_favorites, get_icon_emoji(pet.get('name', '')))
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
                render_card(eq.get('name'), eq.get("level"), eq.get("maxLevel"), current_tag, current_favorites, get_icon_emoji(eq.get('name', '')))
    else:
        st.info("Aucun équipement trouvé.")
