import streamlit as st
from utils import get_db_client, update_account_composition

def render_tab_overview():
    st.subheader("📊 Vue d'ensemble de tous les joueurs et Compositions")
    
    conn = get_db_client()
    
    # Récupérer tous les comptes depuis Turso
    accounts_res = conn.execute("SELECT player_tag, name, town_hall, active_composition FROM accounts")
    accounts = accounts_res.rows
    
    # Récupérer la liste des compositions disponibles
    comps_res = conn.execute("SELECT comp_name, town_hall_level FROM compositions")
    all_comps = comps_res.rows
    comp_options = [row[0] for row in all_comps]
    
    if not accounts:
        st.info("Aucun compte enregistré.")
        return

    # Tableau interactif des comptes avec modification rapide de la composition
    for acc in accounts:
        tag, name, th, active_comp = acc[0], acc[1], acc[2], acc[3]
        
        with st.container(border=True):
            col_info, col_edit = st.columns([0.7, 0.3])
            
            with col_info:
                st.markdown(f"**🛡️ {name}** (`{tag}`) — **TH {th}**")
                st.markdown(f"Composition active : :blue[**{active_comp if active_comp else 'Aucune'}**]")
            
            with col_edit:
                if comp_options:
                    # Index actuel de la compo
                    current_idx = comp_options.index(active_comp) if active_comp in comp_options else 0
                    
                    # Sélecteur rapide et bouton de validation par compte
                    with st.form(key=f"form_comp_{tag}"):
                        new_comp = st.selectbox("Modifier compo", comp_options, index=current_idx, key=f"sel_{tag}", label_visibility="collapsed")
                        submitted = st.form_submit_button("✏️ Modifier")
                        if submitted:
                            update_account_composition(tag, new_comp)
                            st.success(f"Compo mise à jour pour {name} !")
                            st.rerun()
                else:
                    st.caption("⚠️ Aucune compo créée (allez dans l'onglet Paramétrage).")
