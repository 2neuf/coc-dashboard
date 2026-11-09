import streamlit as st

def render_mode_ranked():
    st.subheader("⚔️ Suivi des Ligues Classées Hebdomadaires")
    
    # Exemple de sélection de semaine/période
    selected_week = st.selectbox("Sélectionner la semaine / période", ["Semaine 1 - Novembre", "Semaine 2 - Novembre"])
    
    # Simulation ou récupération sécurisée depuis la base de données
    try:
        # r_data = conn_db.execute("SELECT ... FROM ranked_table WHERE week = ?", (selected_week,)).fetchone()
        r_data = None # Mis à None pour simuler l'absence initiale de données
    except Exception as e:
        st.error(f"Erreur d'accès à la base de données : {e}")
        return

    # 🛡️ Protection indispensable pour éviter l'IndexError si la table est vide ou non initialisée
    if not r_data or len(r_data) < 12:
        st.info(f"📌 Aucune donnée enregistrée pour la période : **{selected_week}**.")
        st.markdown("Veuillez effectuer vos premiers enregistrements de matchs ou initialiser la table pour voir les statistiques.")
        
        # ➕ Ajout d'un formulaire interactif pour initialiser ou enregistrer des données
        with st.expander("➕ Ajouter / Initialiser des données pour cette période", expanded=True):
            with st.form(key=f"form_ranked_{selected_week}"):
                st.write(f"Saisie des données pour **{selected_week}**")
                
                # Champs de saisie du formulaire (à adapter selon vos colonnes SQL)
                status = st.selectbox("Statut", ["En cours", "Terminé"])
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    atk_done = st.number_input("Attaques réussies", min_value=0, value=0)
                    atk_max = st.number_input("Attaques max", min_value=0, value=8)
                    s3 = st.number_input("Étoiles 3⭐", min_value=0, value=0)
                    s2 = st.number_input("Étoiles 2⭐", min_value=0, value=0)
                with col_f2:
                    s1 = st.number_input("Étoiles 1⭐", min_value=0, value=0)
                    avg_dest = st.number_input("Destruction moyenne (%)", min_value=0.0, max_value=100.0, value=0.0)
                    def_done = st.number_input("Défenses subies", min_value=0, value=0)
                    def_max = st.number_input("Défenses max", min_value=0, value=8)

                t_atk = st.number_input("Total attaques", min_value=0, value=0)
                t_def = st.number_input("Total défenses", min_value=0, value=0)
                
                submit_button = st.form_submit_button(label="Enregistrer dans la base de données")
                
                if submit_button:
                    # TODO: Mettez ici votre logique d'insertion/mise à jour SQL avec les variables récupérées
                    st.success(f"Données enregistrées avec succès pour {selected_week} !")
                    st.rerun()
        return

    # Déstructuration sécurisée une fois qu'on a la garantie que r_data est complet
    status = r_data[1]
    atk_done = r_data[2]
    atk_max = r_data[3]
    s3 = r_data[4]
    s2 = r_data[5]
    s1 = r_data[6]
    avg_dest = r_data[7]
    def_done = r_data[8]
    def_nax = r_data[9]
    t_atk = r_data[10]
    t_def = r_data[11]

    # Affichage des métriques si les données existent
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Attaques réussies", f"{atk_done} / {atk_max}")
    with col2:
        st.metric("Étoiles 3⭐", s3)
    with col3:
        st.metric("Destruction moyenne", f"{avg_dest}%")
