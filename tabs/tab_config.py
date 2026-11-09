import streamlit as st
from utils import get_db_client, get_icon_emoji, sort_items, HERO_PETS_LIST, SIEGE_MACHINES_LIST
import json

def render_tab_config(data, current_tag, player_name, current_favorites):
    st.subheader("🛠️ Gestion dynamique : Associer les Équipements aux Héros")
    st.markdown("Utilisez cet espace pour lier manuellement vos équipements à chaque héros de votre choix.")
    
    conn_db = get_db_client()
    available_heroes = [h.get('name') for h in data.get("heroes", []) if h.get("village") == "home"]
    all_player_eqs = [e.get('name') for e in data.get("heroEquipment", [])]
    
    if available_heroes and all_player_eqs:
        if "hero_selector_mapping" not in st.session_state:
            st.session_state.hero_selector_mapping = available_heroes[0]

        def on_hero_change():
            hero = st.session_state.hero_selector_mapping
            res_linked = conn_db.execute("SELECT equipment_name FROM hero_equipment_config WHERE hero_name = ?", [hero])
            already_linked_eqs = [row[0] for row in res_linked.rows]
            st.session_state.mapping_multiselect = [f"{get_icon_emoji(eq)} {eq}" for eq in already_linked_eqs if eq in all_player_eqs]

        selected_hero_to_map = st.selectbox(
            "Sélectionner un héros", 
            available_heroes, 
            key="hero_selector_mapping",
            on_change=on_hero_change
        )

        multiselect_key = "mapping_multiselect"
        if multiselect_key not in st.session_state:
            res_linked = conn_db.execute("SELECT equipment_name FROM hero_equipment_config WHERE hero_name = ?", [selected_hero_to_map])
            already_linked_eqs = [row[0] for row in res_linked.rows]
            st.session_state[multiselect_key] = [f"{get_icon_emoji(eq)} {eq}" for eq in already_linked_eqs if eq in all_player_eqs]

        res_taken = conn_db.execute("SELECT equipment_name FROM hero_equipment_config WHERE hero_name != ?", [selected_hero_to_map])
        taken_equipments = {row[0] for row in res_taken.rows}

        available_eqs_for_this_hero = [
            eq for eq in all_player_eqs 
            if eq not in taken_equipments or eq in [e.replace(get_icon_emoji(e), "").strip() for e in st.session_state.get(multiselect_key, [])]
        ]

        eq_labels = [f"{get_icon_emoji(eq)} {eq}" for eq in available_eqs_for_this_hero]
        eq_map = {f"{get_icon_emoji(eq)} {eq}": eq for eq in available_eqs_for_this_hero}

        with st.form("mapping_form"):
            selected_mapped_labels = st.multiselect(
                "Cocher les équipements de ce héros", 
                eq_labels, 
                key=multiselect_key
            )
            
            submitted_mapping = st.form_submit_button("Sauvegarder l'association des équipements")
            if submitted_mapping:
                conn_db.execute("DELETE FROM hero_equipment_config WHERE hero_name = ?", [selected_hero_to_map])
                for label in selected_mapped_labels:
                    if label in eq_map:
                        eq_name = eq_map[label]
                        conn_db.execute("INSERT INTO hero_equipment_config (hero_name, equipment_name) VALUES (?, ?)", [selected_hero_to_map, eq_name])
                st.success(f"Association enregistrée pour {selected_hero_to_map} !")
                st.rerun()
    else:
        st.info("Aucun héros ou équipement détecté par l'API pour ce joueur.")

    st.divider()
    st.subheader("⚙️ Paramétrage & Modification des Compositions d'Attaque")
    
    # Récupérer les compositions existantes
    comps_res = conn_db.execute("SELECT comp_name, town_hall_level, raw_data FROM compositions")
    existing_comps_dict = {}
    for row in comps_res.rows:
        try:
            raw_json = json.loads(row[2]) if len(row) > 2 and row[2] else {}
        except Exception:
            raw_json = {}
        existing_comps_dict[row[0]] = {"th": row[1], "raw": raw_json}
    
    mode_options = ["➕ Créer une nouvelle composition"] + [f"✏️ Modifier : {c}" for c in existing_comps_dict.keys()]
    selected_mode = st.selectbox("Mode de gestion", mode_options)
    
    default_comp_name = ""
    default_th = 18
    edit_data = {}
    
    if "✏️ Modifier :" in selected_mode:
        target_comp_name = selected_mode.replace("✏️ Modifier : ", "")
        default_comp_name = target_comp_name
        if target_comp_name in existing_comps_dict:
            default_th = existing_comps_dict[target_comp_name]["th"]
            edit_data = existing_comps_dict[target_comp_name]["raw"]

    col_t1, col_t2 = st.columns([0.75, 0.25])
    with col_t1:
        comp_title = st.text_input("Nom de la composition", value=default_comp_name)
    with col_t2:
        comp_th_level = st.selectbox("Niveau HDV cible", [18, 17, 16, 15], index=[18, 17, 16, 15].index(default_th) if default_th in [18, 17, 16, 15] else 0, key="comp_th_selector")
    
    hero_labels = [f"{get_icon_emoji(h)} {h}" for h in available_heroes]
    hero_map = {f"{get_icon_emoji(h)} {h}": h for h in available_heroes}
    
    # Pré-sélection des héros si on est en mode modification
    default_selected_heroes = edit_data.get("heroes_list", [])
    default_hero_labels = [f"{get_icon_emoji(h)} {h}" for h in default_selected_heroes if h in available_heroes]

    selected_hero_labels = st.multiselect("Choisissez les héros à inclure dans la compo", hero_labels, default=default_hero_labels, key="hero_multiselect")
    selected_heroes_comp = [hero_map[l] for l in selected_hero_labels]
    
    hero_custom_links = {}

    if selected_heroes_comp:
        st.markdown("---")
        st.markdown("### 🔗 Configuration des Héros sélectionnés (Familier & Équipements)")
        
        raw_troops_for_pets = data.get("troops", [])
        pets_raw_objs = [t for t in raw_troops_for_pets if t.get("name") in HERO_PETS_LIST]
        sorted_pets_objs = sort_items(pets_raw_objs, current_favorites)
        all_player_pets = [p.get('name'] for p in sorted_pets_objs]

        saved_hero_configs = edit_data.get("hero_configs", {})

        for hero in selected_heroes_comp:
            hero_icon = get_icon_emoji(hero)
            st.markdown(f"**{hero_icon} {hero}**")
            
            hero_saved_cfg = saved_hero_configs.get(hero, {})
            saved_pet = hero_saved_cfg.get("pet", "Aucun")
            saved_eqs = hero_saved_cfg.get("equipment", [])

            col_p, col_eq = st.columns(2)
            with col_p:
                other_heroes_pets = [cfg["pet"] for h_name, cfg in hero_custom_links.items() if h_name != hero]
                available_pets_for_hero = ["Aucun"] + [p for p in all_player_pets if p not in other_heroes_pets]
                
                pet_labels = [f"{get_icon_emoji(p)} {p}" if p != "Aucun" else "🚫 Aucun" for p in available_pets_for_hero]
                
                default_pet_idx = 0
                if saved_pet in available_pets_for_hero:
                    default_pet_idx = available_pets_for_hero.index(saved_pet)

                selected_pet_idx = st.selectbox(f"Familier pour {hero}", range(len(available_pets_for_hero)), index=default_pet_idx, format_func=lambda x: pet_labels[x], key=f"pet_{hero}")
                pet_choice = available_pets_for_hero[selected_pet_idx]
            
            with col_eq:
                res_cfg = conn_db.execute("SELECT equipment_name FROM hero_equipment_config WHERE hero_name = ?", [hero])
                hero_specific_eqs = [row[0] for row in res_cfg.rows]
                
                if not hero_specific_eqs:
                    hero_specific_eqs = all_player_eqs
                
                eq_labels_hero = [f"{get_icon_emoji(e)} {e}" for e in hero_specific_eqs]
                eq_map_hero = {f"{get_icon_emoji(e)} {e}": e for e in hero_specific_eqs}
                
                default_eq_labels = [f"{get_icon_emoji(e)} {e}" for e in saved_eqs if e in hero_specific_eqs]

                selected_eq_labels = st.multiselect(f"Équipements pour {hero} (max 2)", eq_labels_hero, default=default_eq_labels, key=f"eq_{hero}")
                eq_choices = [eq_map_hero[label] for label in selected_eq_labels]
            
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

    troops_raw_objs = [t for t in raw_troops if not should_exclude(t.get("name", ""))]
    sorted_troops_objs = sort_items(troops_raw_objs, current_favorites)
    available_troops = [t.get('name') for t in sorted_troops_objs]
    
    troop_labels = [f"{get_icon_emoji(t)} {t}" for t in available_troops]
    troop_map = {f"{get_icon_emoji(t)} {t}": t for t in available_troops}
    
    default_troops = edit_data.get("troops", [])
    default_troop_labels = [f"{get_icon_emoji(t)} {t}" for t in default_troops if t in available_troops]

    selected_troop_labels = st.multiselect("Sélectionner les Troupes", troop_labels, default=default_troop_labels, key="troops_multiselect")
    selected_troops_comp = [troop_map[l] for l in selected_troop_labels]
    
    spells_raw_objs = [s for s in data.get("spells", []) if s.get("village") == "home"]
    sorted_spells_objs = sort_items(spells_raw_objs, current_favorites)
    available_spells = [s.get('name') for s in sorted_spells_objs]
    
    spell_labels = [f"{get_icon_emoji(s)} {s}" for s in available_spells]
    spell_map = {f"{get_icon_emoji(s)} {s}": s for s in available_spells}
    
    default_spells = edit_data.get("spells", [])
    default_spell_labels = [f"{get_icon_emoji(s)} {s}" for s in default_spells if s in available_spells]

    selected_spell_labels = st.multiselect("Sélectionner les Sorts", spell_labels, default=default_spell_labels, key="spells_multiselect")
    selected_spells_comp = [spell_map[l] for l in selected_spell_labels]
    
    if st.button("Enregistrer / Mettre à jour la composition", type="primary"):
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
                    pet_display = f"{get_icon_emoji(config['pet'])}" if config['pet'] != "Aucun" else ""
                    eq_display = " ".join([f"{get_icon_emoji(e)}" for e in config['equipment']]) if config['equipment'] else ""
                    heroes_summary_list.append(f"{get_icon_emoji(h)} {pet_display} {eq_display}")

                troops_display = " ".join([f"{get_icon_emoji(t)}" for t in selected_troops_comp]) if selected_troops_comp else ""
                spells_display = " ".join([f"{get_icon_emoji(s)}" for s in selected_spells_comp]) if selected_spells_comp else ""

                comp_details = f"{' '.join(heroes_summary_list)} | {troops_display} | {spells_display}"
                
                # Structuration JSON pour mémoriser les sélections exactes et les réinjecter lors des modifications futures
                raw_payload = {
                    "heroes_list": selected_heroes_comp,
                    "hero_configs": hero_custom_links,
                    "troops": selected_troops_comp,
                    "spells": selected_spells_comp
                }
                
                conn = get_db_client()
                # Assurez-vous que la table compositions possède la colonne raw_data (ou l'ajouter si besoin)
                try:
                    conn.execute("ALTER TABLE compositions ADD COLUMN raw_data TEXT")
                except Exception:
                    pass

                conn.execute(
                    "INSERT OR REPLACE INTO compositions (comp_name, details, town_hall_level, raw_data) VALUES (?, ?, ?, ?)", 
                    [comp_title, comp_details, comp_th_level, json.dumps(raw_payload)]
                )
                st.success(f"Composition '{comp_title}' enregistrée avec succès !")
                st.rerun()
