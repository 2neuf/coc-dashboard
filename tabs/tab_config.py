import streamlit as st
from utils import get_db_client, get_icon_emoji, update_account_composition, HERO_PETS_LIST, SIEGE_MACHINES_LIST

def render_tab_config(data, current_tag, player_name):
    st.subheader("🛠️ Gestion dynamique : Associer les Équipements aux Héros")
    st.markdown("Utilisez cet espace pour lier manuellement vos équipements à chaque héros de votre choix.")
    
    conn_db = get_db_client()
    available_heroes = [h.get('name') for h in data.get("heroes", []) if h.get("village") == "home"]
    all_player_eqs = [e.get('name') for e in data.get("heroEquipment", [])]
    
    if available_heroes and all_player_eqs:
        with st.form("mapping_form"):
            selected_hero_to_map = st.selectbox("Sélectionner un héros", available_heroes, key="hero_selector_mapping")
            
            res_linked = conn_db.execute("SELECT equipment_name FROM hero_equipment_config WHERE hero_name = ?", [selected_hero_to_map])
            already_linked_eqs = [row[0] for row in res_linked.rows]
            
            eq_labels = [f"{get_icon_emoji(eq)} {eq}" for eq in all_player_eqs]
            eq_map = {f"{get_icon_emoji(eq)} {eq}": eq for eq in all_player_eqs}
            default_selection = [f"{get_icon_emoji(eq)} {eq}" for eq in already_linked_eqs if eq in all_player_eqs]
            
            selected_mapped_labels = st.multiselect(
                "Cocher les équipements de ce héros", 
                eq_labels, 
                default=default_selection, 
                key=f"mapping_multiselect_{selected_hero_to_map}"
            )
            
            submitted_mapping = st.form_submit_button("Sauvegarder l'association des équipements")
            if submitted_mapping:
                conn_db.execute("DELETE FROM hero_equipment_config WHERE hero_name = ?", [selected_hero_to_map])
                for label in selected_mapped_labels:
                    eq_name = eq_map[label]
                    conn_db.execute("INSERT INTO hero_equipment_config (hero_name, equipment_name) VALUES (?, ?)", [selected_hero_to_map, eq_name])
                st.success(f"Association enregistrée pour {selected_hero_to_map} !")
                st.rerun()
    else:
        st.info("Aucun héros ou équipement détecté par l'API pour ce joueur.")

    st.divider()
    st.subheader("⚙️ Paramétrage des Compositions d'Attaque")
    
    comp_title = st.text_input("Nom de la composition (ex: Root Rider Spam)")
    
    hero_labels = [f"{get_icon_emoji(h)} {h}" for h in available_heroes]
    hero_map = {f"{get_icon_emoji(h)} {h}": h for h in available_heroes}
    
    selected_hero_labels = st.multiselect("Choisissez les héros à inclure dans la compo", hero_labels, key="hero_multiselect")
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
                res_cfg = conn_db.execute("SELECT equipment_name FROM hero_equipment_config WHERE hero_name = ?", [hero])
                hero_specific_eqs = [row[0] for row in res_cfg.rows]
                
                if not hero_specific_eqs:
                    hero_specific_eqs = all_player_eqs
                
                eq_labels_hero = [f"{get_icon_emoji(e)} {e}" for e in hero_specific_eqs]
                eq_map_hero = {f"{get_icon_emoji(e)} {e}": e for e in hero_specific_eqs}
                
                selected_eq_labels = st.multiselect(f"Équipements pour {hero} (max 2)", eq_labels_hero, key=f"eq_{hero}")
                eq_choices = [eq_map_hero[label] for label in selected_eq_labels]
                
                if not eq_choices:
                    st.warning(f"⚠️ Veuillez configurer et sélectionner les équipements de **{hero}** dans l'outil de gestion ci-dessus ou les cocher ici.")
            
            hero_custom_links[hero] = {"pet": pet_choice, "equipment": eq_choices}
            st.divider()

    st.markdown("### 🧪 Troupes & Sorts de la Compo")
    raw_troops = [t for t in data.get("troops", []) if t.get("village") == "home"]
    
    def should_exclude(name):
        name_lower = name.lower()
        is_super = "super" in name_lower or name in ["Sneaky Goblin", "Rocket Balloon", "Inferno Dragon"]
        is_pet = name in HERO_PETS_LIST
        is_siege = name in SIEGE_MACHINES_LIST
        return is_super or is_pet or is_siege

    available_troops = [t.get('name') for t in raw_troops if not should_exclude(t.get("name", ""))]
    troop_labels = [f"{get_icon_emoji(t)} {t}" for t in available_troops]
    troop_map = {f"{get_icon_emoji(t)} {t}": t for t in available_troops}
    selected_troop_labels = st.multiselect("Sélectionner les Troupes", troop_labels, key="troops_multiselect")
    selected_troops_comp = [troop_map[l] for l in selected_troop_labels]
    
    spells = [s for s in data.get("spells", []) if s.get("village") == "home"]
    available_spells = [s.get('name') for s in spells]
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
