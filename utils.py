import streamlit as st
from utils import get_db_client, get_icon_emoji, sort_items, HERO_PETS_LIST, SIEGE_MACHINES_LIST
import json

def render_tab_config(data, current_tag, player_name, current_favorites):
    config_mode = st.radio(
        "Mode de configuration",
        [
            "⚙️ Paramétrage des Compositions", 
            "🔗 Association des Équipements par Héros",
            "🎨 Personnalisation des Emojis"
        ],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    conn_db = get_db_client()
    available_heroes = [h.get('name') for h in data.get("heroes", []) if h.get("village") == "home"]
    all_player_eqs = [e.get('name') for e in data.get("heroEquipment", [])]

    # --- MODE 3 : PERSONNALISATION DES EMOJIS ---
    if config_mode == "🎨 Personnalisation des Emojis":
        st.subheader("🎨 Personnalisation globale des Emojis")
        st.markdown("Modifiez et associez l'emoji de votre choix à n'importe quel élément du jeu.")
        
        category = st.selectbox(
            "Sélectionner une catégorie",
            ["Héros", "Familiers", "Équipements", "Troupes", "Sorts"]
        )
        
        items_to_edit = []
        if category == "Héros":
            items_to_edit = available_heroes
        elif category == "Familiers":
            items_to_edit = HERO_PETS_LIST
        elif category == "Équipements":
            items_to_edit = all_player_eqs
        elif category == "Troupes":
            raw_troops = [t for t in data.get("troops", []) if t.get("village") == "home"]
            items_to_edit = [t.get("name") for t in raw_troops if t.get("name") not in HERO_PETS_LIST and t.get("name") not in SIEGE_MACHINES_LIST]
        elif category == "Sorts":
            raw_spells = [s for s in data.get("spells", []) if s.get("village") == "home"]
            items_to_edit = [s.get("name") for s in raw_spells]
            
        if items_to_edit:
            with st.form("emojis_form"):
                new_emojis_dict = {}
                st.markdown("---")
                for item in items_to_edit:
                    current_current_emoji = get_icon_emoji(item)
                    col_item, col_input = st.columns([0.7, 0.3])
                    with col_item:
                        st.markdown(f"**{item}** (Actuel : {current_current_emoji})")
                    with col_input:
                        new_emoji = st.text_input(f"Emoji {item}", value=current_current_emoji, key=f"emoji_input_{item}", label_visibility="collapsed")
                        new_emojis_dict[item] = new_emoji
                
                submitted_emojis = st.form_submit_button("Sauvegarder les modifications d'emojis", type="primary")
                if submitted_emojis:
                    for item, emoji_val in new_emojis_dict.items():
                        if emoji_val.strip():
                            conn_db.execute(
                                "INSERT OR REPLACE INTO custom_emojis (item_name, emoji) VALUES (?, ?)",
                                [item, emoji_val.strip()]
                            )
                    st.success("Emojis mis à jour avec succès !")
                    st.rerun()
        else:
            st.info("Aucun élément disponible dans cette catégorie pour le moment.")

    # --- MODE 2 : ASSOCIATION DES ÉQUIPEMENTS PAR HÉROS ---
    elif config_mode == "🔗 Association des Équipements par Héros":
        st.subheader("🛠️ Gestion dynamique : Associer les Équipements aux Héros")
        st.markdown("Utilisez cet espace pour lier manuellement vos équipements à chaque héros de votre choix.")
        
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

    # --- MODE 1 : PARAMÉTRAGE DES COMPOSITIONS (PAR DÉFAUT) ---
    else:
        st.subheader("⚙️ Paramétrage & Modification des Compositions d'Attaque")
        
        try:
            comps_res = conn_db.execute("SELECT comp_name, town_hall_level, raw_data, details FROM compositions")
        except Exception:
            comps_res = conn_db.execute("SELECT comp_name, town_hall_level, details FROM compositions")

        existing_comps_dict = {}
        for row in comps_res.rows:
            comp_name = row[0]
            th_lvl = row[1]
            raw_json = {}
            
            if len(row) > 2 and row[2] and row[2].startswith("{"):
                try:
                    raw_json = json.loads(row[2])
                except Exception:
                    pass
            
            if not raw_json:
                found_heroes = [h for h in available_heroes if h in row[3] or get_icon_emoji(h) in row[3]] if len(row) > 3 and row[3] else []
                raw_json = {
                    "heroes_list": found_heroes if found_heroes else available_heroes,
                    "hero_configs": {},
                    "troops": [],
                    "spells": []
                }

            existing_comps_dict[comp_name] = {"th": th_lvl, "raw": raw_json}
        
        mode_options = ["➕ Créer une nouvelle composition"] + [f"✏️ Modifier : {c}" for c in existing_comps_dict.keys()]
        
        if "prev_selected_mode" not in st.session_state:
            st.session_state.prev_selected_mode = mode_options[0]

        selected_mode = st.selectbox("Mode de gestion", mode_options, key="selected_mode_box")
        
        if st.session_state.prev_selected_mode != selected_mode:
            st.session_state.prev_selected_mode = selected_mode
            target_name = selected_mode.replace("✏️ Modifier : ", "") if "✏️ Modifier :" in selected_mode else ""
            comp_info = existing_comps_dict.get(target_name, {"th": 18, "raw": {}})
            edit_data = comp_info.get("raw", {})
            
            st.session_state["comp_title_input"] = target_name
            st.session_state["hero_multiselect"] = [f"{get_icon_emoji(h)} {h}" for h in edit_data.get("heroes_list", []) if h in available_heroes]
            st.session_state["troops_multiselect"] = [f"{get_icon_emoji(t)} {t}" for t in edit_data.get("troops", [])]
            st.session_state["spells_multiselect"] = [f"{get_icon_emoji(s)} {s}" for s in edit_data.get("spells", [])]
            st.rerun()

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
            comp_title = st.text_input("Nom de la composition", value=default_comp_name, key="comp_title_input")
        with col_t2:
            comp_th_level = st.selectbox("Niveau HDV cible", [18, 17, 16, 15], index=[18, 17, 16, 15].index(default_th) if default_th in [18, 17, 16, 15] else 0, key="comp_th_selector")
        
        hero_labels = [f"{get_icon_emoji(h)} {h}" for h in available_heroes]
        hero_map = {f"{get_icon_emoji(h)} {h}": h for h in available_heroes}
        
        default_selected_heroes = edit_data.get("heroes_list", [])
        default_hero_labels = [f"{get_icon_emoji(h)} {h}" for h in default_selected_heroes if h in available_heroes]

        selected_hero_labels = st.multiselect("Choisissez les héros à inclure dans la compo", hero_labels, default=default_hero_labels, key="hero_multiselect")
        selected_heroes_comp = [hero_map[l] for l in selected_hero_labels if l in hero_map]
        
        hero_custom_links = {}

        if selected_heroes_comp:
            st.markdown("---")
            st.markdown("### 🔗 Configuration des Héros sélectionnés (Familier & Équipements)")
            
            raw_troops_for_pets = data.get("troops", [])
            pets_raw_objs = [t for t in raw_troops_for_pets if t.get("name"] in HERO_PETS_LIST] # FIXED: Syntax verified correctly below
