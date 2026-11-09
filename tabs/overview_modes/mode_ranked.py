import streamlit as st

def render_mode_ranked():
    st.subheader("⚔️ Suivi des Ligues Classées Hebdomadaires")
    
    # Exemple de sélection de semaine/période
    selected_week = st.selectbox("Sélectionner la semaine / période", ["Semaine 1 - Novembre", "Semaine 2 - Novembre"])
    
    # Simulation ou récupération sécurisée depuis la base de données
    # (Remplace cette partie par ta requête SQL existante qui récupère r_data)
    try:
        # Supposons que tu récupères r_data ici via ta connexion DB :
        # r_data = conn_db.execute("SELECT ... FROM ranked_table WHERE week = ?", (selected_week,)).fetchone()
        r_data = None # Mis à None pour simuler l'absence initiale de données
    except Exception as e:
        st.error(f"Erreur d'accès à la base de données : {e}")
        return

    # 🛡️ Protection indispensable pour éviter l'IndexError si la table est vide ou non initialisée
    if not r_data or len(r_data) < 12:
        st.info(f"📌 Aucune donnée enregistrée pour la période : **{selected_week}**.")
        st.markdown("Veuillez effectuer vos premiers enregistrements de matchs ou initialiser la table pour voir les statistiques.")
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
