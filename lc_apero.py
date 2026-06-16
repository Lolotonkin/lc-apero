import streamlit as st
from supabase import create_client, Client
import requests
import pandas as pd
import datetime
import qrcode
import io
import plotly.graph_objects as go
import numpy as np
import urllib.parse

# --- CONFIGURATION INITIALE & THÈME ---
st.set_page_config(page_title="Suivi de soirée 🍹", layout="wide", initial_sidebar_state="collapsed")

# Palette de couleurs globale (utilisée pour les chaises ET le graphique)
COULEURS_JOUEURS = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22', '#1abc9c', '#16a085', '#c0392b', '#8e44ad']

st.markdown("""
    <style>
    /* Thème général */
    .stApp, .stApp > header { background-color: #000000 !important; color: #FFFFFF !important; }
    h1, h2, h3, p, span, label, div[data-testid="stMarkdownContainer"] { color: #FFFFFF !important; }
    h1, h2 { color: #FF9800 !important; font-weight: bold !important; }
    
    /* Boutons généraux (harmonisation avec les expanders) */
    div[data-testid="stButton"] > button, 
    div[data-testid="stFormSubmitButton"] > button { 
        background-color: #1A1A1A !important; 
        color: #FF9800 !important; 
        font-weight: bold !important; 
        border: 1px solid #FF9800 !important; 
        border-radius: 8px !important;
    }
    div[data-testid="stButton"] > button:hover, 
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #333333 !important;
        border-color: #FFFFFF !important;
        color: #FFFFFF !important;
    }
    
    /* Champs de saisie & Selectbox (Fond sombre, bordure arrondie) */
    .stTextInput input, .stNumberInput input, div[data-baseweb="select"], div[data-baseweb="select"] > div { 
        background-color: #1A1A1A !important; 
        color: #FFFFFF !important; 
        border: 1px solid #FFFFFF !important; 
        border-radius: 8px !important;
    }
    
    /* Lien WhatsApp & Accès */
    div[data-testid="stLinkButton"] > a { 
        background-color: #1A1A1A !important; 
        color: #FF9800 !important; 
        font-weight: bold !important; 
        text-decoration: none !important;
        border: 1px solid #FF9800 !important;
        border-radius: 8px !important;
    }
    
    /* Expanders & Métriques */
    div[data-testid="stExpander"] { background-color: #1A1A1A !important; border: 1px solid #FF9800 !important; border-radius: 8px !important; margin-bottom: 5px; }
    
    /* Correction visibilité titres expanders */
    div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary * { 
        color: #FF9800 !important; 
        font-weight: bold !important; 
        font-size: 1.15em !important; 
    }
    
    div[data-testid="stMetricValue"] { color: #FF9800 !important; }

    /* Timeline CSS */
    .timeline-row { border-left: 3px solid #FF9800; padding-left: 15px; margin-bottom: 5px; }
    .time-badge { color: #FF9800; font-weight: bold; font-size: 1.2em; }
    .pseudo-text { color: #FFFFFF; font-weight: bold; font-size: 1.1em; }
    .details-text { color: #CCCCCC; font-size: 0.9em; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION SUPABASE ---
SUPABASE_URL = "https://rjexlotreipfjbgpfcnt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqZXhsb3RyZWlwZmpiZ3BmY250Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTt4MDUyOTkyNywiZXhwIjoyMDk2MTA1OTI3fQ.0vMnopwPCMQaOmzCPNcdc4HLqr1d1npoqL3xXNnxGQ8"

@st.cache_resource
def init_supabase():
    try: return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"🔑 Erreur Supabase : {e}")
        st.stop()

supabase = init_supabase()
URL_WEBHOOK_WHATSAPP = st.secrets.get("URL_WEBHOOK_WHATSAPP", "")

# --- FONCTIONS DONNÉES ---
@st.cache_data(ttl=2)
def obtenir_toutes_les_tables():
    try:
        rep = supabase.table("profils").select("groupe").execute()
        if rep.data:
            return sorted(list(set([p['groupe'] for p in rep.data if p.get('groupe')])))
        return ["Haggis et les cafards"]
    except:
        return ["Haggis et les cafards"]

# ==========================================
# EN-TÊTE PRINCIPAL
# ==========================================
col_titre, col_maj = st.columns([3, 1])
with col_titre:
    st.title("🍹 Suivi de soirée")
    st.markdown("<h5 style='color: #FF9800; margin-top: -15px;'>Version 3.5</h5>", unsafe_allow_html=True)
with col_maj:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Mettre à jour", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("<p style='text-align: right;'><a href='#faq' style='color: #FF9800; text-decoration: none;'>❓ Une question ? Consulter la FAQ en bas</a></p>", unsafe_allow_html=True)

# --- GESTION VARIABLES SESSION ---
tables_existantes = obtenir_toutes_les_tables()
if "Haggis et les cafards" not in tables_existantes:
    tables_existantes.insert(0, "Haggis et les cafards")

if "groupe_selectionne" not in st.session_state:
    st.session_state.groupe_selectionne = "Haggis et les cafards"

if st.session_state.groupe_selectionne not in tables_existantes:
    tables_existantes.append(st.session_state.groupe_selectionne)

# --- CHARGEMENT DES PROFILS ---
@st.cache_data(ttl=2)
def charger_profils(groupe):
    try:
        rep = supabase.table("profils").select("*").eq("groupe", groupe).execute()
        return {p['pseudo']: {"sexe": p['sexe'], "poids": p['poids'], "id": p['id']} for p in rep.data} if rep.data else {}
    except: return {}

groupe_actif = st.session_state.groupe_selectionne
profils = charger_profils(groupe_actif)

# Initialisation par défaut si vide et Haggis
if not profils and groupe_actif == "Haggis et les cafards":
    defauts = [
        {"pseudo": "Lolo", "sexe": "Homme", "poids": 75, "groupe": groupe_actif},
        {"pseudo": "Poums", "sexe": "Homme", "poids": 75, "groupe": groupe_actif},
        {"pseudo": "Nico", "sexe": "Homme", "poids": 75, "groupe": groupe_actif},
        {"pseudo": "Duj", "sexe": "Homme", "poids": 75, "groupe": groupe_actif}
    ]
    supabase.table("profils").insert(defauts).execute()
    st.cache_data.clear()
    profils = charger_profils(groupe_actif)

# --- 1. TABLE ACTIVE & DESSIN ---
with st.expander("🌐 1. Table active", expanded=True):
    options_menu = tables_existantes + ["➕ Créer une nouvelle table..."]
    index_defaut = options_menu.index(st.session_state.groupe_selectionne)

    choix_table = st.selectbox("Sélectionnez votre table :", options_menu, index=index_defaut)

    if choix_table == "➕ Créer une nouvelle table...":
        st.info("💡 Saisissez le nom de la nouvelle table ci-dessous.")
        col_nom, col_btn = st.columns([3, 1])
        with col_nom:
            nom_nouvelle_table = st.text_input("Nom de la table :", label_visibility="collapsed", placeholder="Ex: Mariage de Max")
        with col_btn:
            if st.button("Rejoindre 🚀", use_container_width=True):
                if nom_nouvelle_table.strip():
                    st.session_state.groupe_selectionne = nom_nouvelle_table.strip()
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Nom invalide.")
        groupe_actif = st.session_state.groupe_selectionne
    else:
        if choix_table != st.session_state.groupe_selectionne:
            st.session_state.groupe_selectionne = choix_table
            st.cache_data.clear()
            st.rerun()
        groupe_actif = choix_table
    
    envoyer_wa = st.checkbox("Activer les alertes WhatsApp", value=True)

    # --- DESSIN DE LA TABLE ET DES CHAISES ---
    if profils:
        fig_table = go.Figure()
        
        # Dessin de la table centrale
        fig_table.add_shape(type="circle", x0=-0.8, y0=-0.8, x1=0.8, y1=0.8, fillcolor="#1A1A1A", line_color="#FF9800", line_width=3)
        fig_table.add_annotation(x=0, y=0, text=groupe_actif, showarrow=False, font=dict(color="#FF9800", size=14, family="Arial"))
        
        # Dessin des chaises
        num_chairs = len(profils)
        angles = np.linspace(0, 2*np.pi, num_chairs, endpoint=False)
        rayon_chaises = 1.15
        rayon_texte = 1.6
        
        for idx, (nom, angle) in enumerate(zip(profils.keys(), angles)):
            cx = rayon_chaises * np.cos(angle)
            cy = rayon_chaises * np.sin(angle)
            tx = rayon_texte * np.cos(angle)
            ty = rayon_texte * np.sin(angle)
            couleur_chaise = COULEURS_JOUEURS[idx % len(COULEURS_JOUEURS)]
            
            # Chaise
            fig_table.add_shape(type="circle", x0=cx-0.2, y0=cy-0.2, x1=cx+0.2, y1=cy+0.2, fillcolor=couleur_chaise, line_color="#FFFFFF", line_width=2)
            # Nom
            fig_table.add_annotation(x=tx, y=ty, text=nom, showarrow=False, font=dict(color="#FFFFFF", size=12, family="Arial"))

        fig_table.update_layout(
            xaxis=dict(visible=False, range=[-2, 2]), 
            yaxis=dict(visible=False, range=[-2, 2]), 
            width=350, height=350, 
            margin=dict(l=0, r=0, t=10, b=10), 
            plot_bgcolor="rgba(0,0,0,0)", 
            paper_bgcolor="rgba(0,0,0,0)", 
            showlegend=False
        )
        st.plotly_chart(fig_table, use_container_width=True, config={'displayModeBar': False})

def envoyer_alerte_whatsapp(pseudo, detail_conso, type_event="Verre"):
    if not URL_WEBHOOK_WHATSAPP or not envoyer_wa: return
    if type_event == "Repas": texte = f"🍽️ *Suivi de soirée ({groupe_actif})* : {pseudo} déclare un repas complet. 🥪"
    elif type_event == "Grignotage": texte = f"🥨 *Suivi de soirée ({groupe_actif})* : {pseudo} grignote à l'apéro. 🥜"
    else: texte = f"🍹 *Suivi de soirée ({groupe_actif})* : {pseudo} a pris : {detail_conso} 📈"
    try: requests.post(URL_WEBHOOK_WHATSAPP, json={"message": texte, "pseudo": pseudo})
    except: pass

@st.cache_data(ttl=2)
def charger_donnees(groupe):
    try:
        boissons = supabase.table("drinks").select("*").eq("groupe", groupe).order("created_at", desc=False).execute()
        repas = supabase.table("meals").select("*").eq("groupe", groupe).order("created_at", desc=False).execute()
        return (boissons.data or []), (repas.data or [])
    except: return [], []

boissons_nuageuses, repas_nuage = charger_donnees(groupe_actif)

# --- MOTEUR DE CALCUL MATHÉMATIQUE ---
maintenant = pd.Timestamp.now(tz='Europe/Paris')
maintenant_arrondi = maintenant.floor('5min')
debut_calcul = maintenant_arrondi - pd.Timedelta(hours=24)
fin_calcul = maintenant_arrondi + pd.Timedelta(hours=12)
axe_temps = pd.date_range(start=debut_calcul, end=fin_calcul, freq='5min', tz='Europe/Paris')

PENTE_ELIMINATION_5MIN = 0.15 * (5 / 60)

def clean_tz(series):
    dt = pd.to_datetime(series, errors='coerce', format='mixed', utc=True)
    return dt.dt.tz_convert('Europe/Paris')

df_verres = pd.DataFrame(boissons_nuageuses) if boissons_nuageuses else pd.DataFrame(columns=['id', 'pseudo', 'boisson', 'alcool_g', 'created_at', 'groupe'])
if not df_verres.empty: 
    df_verres['created_at'] = clean_tz(df_verres['created_at'])
    df_verres = df_verres.dropna(subset=['created_at'])

df_repas = pd.DataFrame(repas_nuage) if repas_nuage else pd.DataFrame(columns=['id', 'pseudo', 'created_at', 'groupe', 'type'])
if not df_repas.empty: 
    df_repas['created_at'] = clean_tz(df_repas['created_at'])
    df_repas = df_repas.dropna(subset=['created_at'])
    if 'type' not in df_repas.columns: df_repas['type'] = 'Repas'

df_graphique = pd.DataFrame(index=axe_temps)
idx_maintenant = df_graphique.index.get_indexer([maintenant_arrondi], method='nearest')[0]

stats_joueurs = {}

for nom, info in profils.items():
    poids = info["poids"]
    coef_diffusion = 0.7 if info["sexe"] == "Homme" else 0.6
    taux_liste = []
    
    verres_perso = df_verres[df_verres['pseudo'] == nom] if not df_verres.empty else pd.DataFrame()
    repas_perso = df_repas[df_repas['pseudo'] == nom] if not df_repas.empty else pd.DataFrame()

    t_start_sim = debut_calcul
    if not verres_perso.empty:
        premier_verre = verres_perso['created_at'].min().floor('5min')
        if premier_verre < t_start_sim: t_start_sim = premier_verre
            
    axe_complet = pd.date_range(start=t_start_sim, end=fin_calcul, freq='5min', tz='Europe/Paris')
    apports_globaux = pd.Series(0.0, index=axe_complet)
    
    if not verres_perso.empty:
        for _, verre in verres_perso.iterrows():
            t_drink = verre['created_at']
            a_mange = False
            a_grignote = False
            
            if not repas_perso.empty:
                repas_complets = repas_perso[repas_perso['type'] == 'Repas']
                grignotages = repas_perso[repas_perso['type'] == 'Grignotage']
                
                if not repas_complets.empty:
                    valides_repas = repas_complets[(repas_complets['created_at'] >= t_drink - pd.Timedelta(hours=3)) & (repas_complets['created_at'] <= t_drink + pd.Timedelta(hours=1))]
                    if not valides_repas.empty: a_mange = True
                
                if not grignotages.empty:
                    valides_grig = grignotages[(grignotages['created_at'] >= t_drink - pd.Timedelta(hours=1.5)) & (grignotages['created_at'] <= t_drink + pd.Timedelta(hours=0.5))]
                    if not valides_grig.empty: a_grignote = True
                
            if a_mange: t_pic, bio_factor = 1.0, 0.8 
            elif a_grignote: t_pic, bio_factor = 0.75, 0.9 
            else: t_pic, bio_factor = 0.5, 1.0 
                
            c_max_theo = (verre['alcool_g'] / (poids * coef_diffusion)) * bio_factor
            
            t_start_search = t_drink.floor('5min')
            for steps in range(0, int(t_pic * 12) + 2):
                t = t_start_search + pd.Timedelta(minutes=5 * steps)
                if t in apports_globaux.index:
                    diff_heures_debut = (t - pd.Timedelta(minutes=5) - t_drink).total_seconds() / 3600.0
                    diff_heures_fin = (t - t_drink).total_seconds() / 3600.0
                    if diff_heures_fin > 0 and diff_heures_debut < t_pic:
                        t_deb_calc = max(0.0, diff_heures_debut)
                        t_fin_calc = min(t_pic, diff_heures_fin)
                        apport_5min = c_max_theo * ((t_fin_calc - t_deb_calc) / t_pic)
                        apports_globaux.loc[t] += max(0.0, apport_5min)

    taux_courant = 0.0
    taux_dict = {}
    for t in axe_complet:
        apport_5min = apports_globaux.loc[t]
        taux_courant += apport_5min
        if apport_5min == 0 and taux_courant > 0: taux_courant -= PENTE_ELIMINATION_5MIN
        taux_courant = max(0.0, taux_courant)
        taux_dict[t] = taux_courant
        
    for t in axe_temps: taux_liste.append(taux_dict.get(t, 0.0))
    df_graphique[nom] = taux_liste
    max_historique = max(taux_dict.values()) if taux_dict else 0.0
    
    if not verres_perso.empty:
        dernier_verre = verres_perso['created_at'].max()
        jours_ecoules = (maintenant.date() - dernier_verre.date()).days
        if jours_ecoules == 0: texte_jours = "Aujourd'hui 🍻"
        elif jours_ecoules == 1: texte_jours = "Hier 💧"
        else: texte_jours = f"{jours_ecoules} jours 💧"
    else:
        jours_ecoules = -1
        texte_jours = "Jamais bu 😇"
        
    stats_joueurs[nom] = {"max_ever": max_historique, "texte_jours": texte_jours, "jours_ecoules": jours_ecoules, "total_verres": len(verres_perso)}

# --- 2. DÉCLARATION ---
with st.expander("🍹 2. Déclarer une consommation", expanded=False):
    if not profils:
        st.error("⚠️ Cette table est vide. Descendez à la section '7. Gérer l'équipe' pour ajouter des invités !")
    else:
        choix_type = st.radio("Type d'entrée :", ["Un verre de l'amitié 🍺", "Un repas complet 🍽️", "Grignotage (Apéro) 🥨"], horizontal=True)
        
        oubli = st.checkbox("🕰️ J'ai oublié de le noter sur le moment (modifier l'heure)")
        maintenant_local = pd.Timestamp.now(tz='Europe/Paris')
        
        if oubli:
            if "heure_perso_val" not in st.session_state:
                st.session_state.heure_perso_val = maintenant_local.time().replace(second=0, microsecond=0)
            heure_perso = st.time_input("Heure de la consommation :", value=st.session_state.heure_perso_val, key="widget_heure_oubli")
            st.session_state.heure_perso_val = heure_perso 
            date_conso = maintenant_local.date()
            if heure_perso > maintenant_local.time() and maintenant_local.hour < 12: date_conso = date_conso - datetime.timedelta(days=1)
            dt_combine = datetime.datetime.combine(date_conso, heure_perso)
            moment_actuel = pd.Timestamp(dt_combine).tz_localize('Europe/Paris').isoformat()
            affichage_heure = heure_perso.strftime("%H:%M")
        else:
            if "heure_perso_val" in st.session_state: del st.session_state["heure_perso_val"]
            moment_actuel = maintenant_local.isoformat()
            affichage_heure = maintenant_local.strftime("%H:%M")

        if "repas" in choix_type.lower() or "grignotage" in choix_type.lower():
            type_repas = "Repas" if "repas" in choix_type.lower() else "Grignotage"
            Qui = st.selectbox("Qui a mangé ?", list(profils.keys()))
            if st.button("Enregistrer 💾"):
                supabase.table("meals").insert({"pseudo": Qui, "created_at": moment_actuel, "groupe": groupe_actif, "type": type_repas}).execute()
                st.cache_data.clear() 
                envoyer_alerte_whatsapp(Qui, f"{type_repas} à {affichage_heure}", type_event=type_repas)
                st.success(f"✔️ {type_repas} enregistré pour {Qui} à {affichage_heure}")
                st.rerun()
        else:
            c1, c2, c3 = st.columns(3)
            with c1: Qui = st.selectbox("Qui consumes ?", list(profils.keys()))
            with c2: Volume_cl = st.number_input("Volume (cl)", min_value=1, max_value=200, value=25, step=1)
            with c3: Degre_Alcool = st.number_input("Degré d'alcool (%)", min_value=0.5, max_value=90.0, value=5.0, step=0.5)

            if st.button("Enregistrer le verre 💾"):
                boisson_label = f"{Volume_cl}cl @ {Degre_Alcool}%"
                alcool_g = float((Volume_cl * 10) * (Degre_Alcool / 100) * 0.8)
                supabase.table("drinks").insert({"pseudo": Qui, "boisson": boisson_label, "alcool_g": alcool_g, "created_at": moment_actuel, "groupe": groupe_actif}).execute()
                st.cache_data.clear() 
                envoyer_alerte_whatsapp(Qui, f"{boisson_label} à {affichage_heure}", type_event="Verre")
                st.success(f"🍹 Verre enregistré pour {Qui} à {affichage_heure}")
                st.rerun()

# --- 3. TABLEAU DE BORD INSTANTANÉ ---
with st.expander("📍 3. Tableau de bord instantané", expanded=False):
    if not profils:
        st.warning("En attente de profils pour calculer les taux.")
    else:
        cols_dashboard = st.columns(len(profils))
        texte_whatsapp = f"🪳 *Point AlcooSuivi — Table {groupe_actif}* 🍻\n\n"

        for i, nom in enumerate(profils.keys()):
            taux_actuel = df_graphique[nom].iloc[idx_maintenant] if nom in df_graphique.columns else 0.0
            donnees_futures = df_graphique[nom].loc[maintenant_arrondi:] if nom in df_graphique.columns else pd.Series()
            taux_max_futur = donnees_futures.max() if not donnees_futures.empty else 0.0
            
            if taux_actuel > 0.01 or (not donnees_futures.empty and taux_max_futur > 0.01):
                temps_sobre = donnees_futures[donnees_futures <= 0.01]
                retour_zero = temps_sobre.index[0].strftime("%H:%M") if not temps_sobre.empty else "Demain"
            else: retour_zero = "À jeun"
                
            if donnees_futures.empty or taux_max_futur < 0.5: heure_conduite = "Maintenant ✅"
            else:
                heure_pic = donnees_futures.idxmax()
                donnees_apres_pic = donnees_futures.loc[heure_pic:]
                temps_conduite = donnees_apres_pic[donnees_apres_pic < 0.5]
                heure_conduite = temps_conduite.index[0].strftime("%H:%M") if not temps_conduite.empty else "Trop tard 🛑"

            with cols_dashboard[i % len(cols_dashboard)]:
                with st.container(border=True):
                    st.markdown(f"#### {nom}")
                    st.metric(label="Taux Actuel", value=f"{taux_actuel:.2f} g/L")
                    st.markdown(f"**Max projeté :** {taux_max_futur:.2f} g/L")
                    st.markdown(f"**🚗 Conduite (<0.5):** {heure_conduite}")
                    st.markdown(f"**💧 À jeun (0.0):** {retour_zero}")
                
            texte_whatsapp += f"• *{nom}* : {taux_actuel:.2f}g/L (Max: {taux_max_futur:.2f})\n"

        texte_wa_encode = urllib.parse.quote(texte_whatsapp)
        lien_partage_whatsapp = f"https://api.whatsapp.com/send?text={texte_wa_encode}"
        st.markdown("<br>", unsafe_allow_html=True)
        st.link_button("📲 Partager le bilan sur WhatsApp", lien_partage_whatsapp)
    
# --- 4. HALL OF FAME ---
record_absolu_groupe = max([s['max_ever'] for s in stats_joueurs.values()]) if stats_joueurs else 0.0

with st.expander("🏆 4. Hall of Fame (Records & Statistiques)", expanded=False):
    st.markdown(f"<h4 style='color: orange; margin-bottom: 20px;'>🔥 Record absolu de la table : {record_absolu_groupe:.2f} g/L</h4>", unsafe_allow_html=True)
    
    cols_stats = st.columns(len(profils) if profils else 1)
    for i, (nom, stats) in enumerate(stats_joueurs.items()):
        score = stats['max_ever']
        badge_record = ""
        if score == record_absolu_groupe and score > 0.01: badge_record += "👑 "
        if score >= 2.0: badge_record += "🧟‍♂️"
        elif score >= 1.5: badge_record += "🏴‍☠️"
        elif score >= 1.0: badge_record += "🥳"
        elif score >= 0.5: badge_record += "🍺"
        elif score > 0.0: badge_record += "👼"
        else: badge_record += "🚰"

        jours = stats['jours_ecoules']
        if jours == -1: badge_sobriete = "🕊️ Pureté"
        elif jours >= 30: badge_sobriete = "🧘 1 mois+"
        elif jours >= 14: badge_sobriete = "🛡️ 2 sem+"
        elif jours >= 7: badge_sobriete = "🌱 1 sem+"
        elif jours >= 5: badge_sobriete = "🐫 5j+"
        elif jours >= 3: badge_sobriete = "🔋 3j+"
        elif jours >= 1: badge_sobriete = "☀️ 1j+"
        else: badge_sobriete = "🔥 En activité"

        with cols_stats[i % len(cols_stats)]:
            with st.container(border=True):
                st.markdown(f"#### {nom}")
                st.markdown(f"**Record max :** {score:.2f} {badge_record}")
                st.markdown(f"**Dernier verre :** {stats['texte_jours']}")
                st.markdown(f"**Sobriété :** `{badge_sobriete}`")
                st.markdown(f"**Total bu :** {stats['total_verres']} v.")

# --- 5. GRAPHIQUE ---
with st.expander("📊 5. Courbes (Évolution)", expanded=False):
    if not df_verres.empty and profils:
        choix_vue = st.radio("Sélectionnez la période à afficher :", ["Standard (H-2 à H+6)", "Demi-journée (H-12 à H+12)", "Week-end (H-24 à H+12)"], horizontal=True)
        h_avant, h_apres = (2, 6) if "Standard" in choix_vue else ((12, 12) if "Demi-journée" in choix_vue else (24, 12))

        fig = go.Figure()
        for i, nom in enumerate(profils.keys()):
            if nom in df_graphique.columns:
                fig.add_trace(go.Scatter(x=df_graphique.index, y=df_graphique[nom], mode='lines', name=nom, line=dict(width=3, color=COULEURS_JOUEURS[i % len(COULEURS_JOUEURS)])))

        fig.add_vline(x=maintenant_arrondi, line_width=2, line_dash="dash", line_color="orange")
        fig.add_hline(y=0.5, line_width=1, line_dash="dot", line_color="red", annotation_text="0.5 g/L", annotation_position="top right")

        vue_debut = (maintenant_arrondi - pd.Timedelta(hours=h_avant)).strftime('%Y-%m-%d %H:%M:%S')
        vue_fin = (maintenant_arrondi + pd.Timedelta(hours=h_apres)).strftime('%Y-%m-%d %H:%M:%S')

        fig.update_xaxes(fixedrange=True, title="Heure", range=[vue_debut, vue_fin], autorange=False)
        fig.update_yaxes(fixedrange=True, title="Taux (g/L)", rangemode="tozero")
        fig.update_layout(template="plotly_dark", hovermode="x unified", margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("Aucun verre enregistré sur cette table.")

# --- 6. HISTORIQUE ---
with st.expander("📋 6. Historique de la soirée (Timeline 24h)", expanded=False):
    df_verres_recent = df_verres[df_verres['created_at'] >= (maintenant_arrondi - pd.Timedelta(hours=24))].copy() if not df_verres.empty else pd.DataFrame()
    if not df_verres_recent.empty: 
        df_verres_recent['icone'] = '🍹'
        df_verres_recent['details'] = df_verres_recent['boisson']
    else: df_verres_recent = pd.DataFrame(columns=['id', 'pseudo', 'created_at', 'icone', 'details'])

    df_repas_recent = df_repas[df_repas['created_at'] >= (maintenant_arrondi - pd.Timedelta(hours=24))].copy() if not df_repas.empty else pd.DataFrame()
    if not df_repas_recent.empty: 
        df_repas_recent['icone'] = df_repas_recent['type'].apply(lambda x: '🥨' if x == 'Grignotage' else '🍽️')
        df_repas_recent['details'] = df_repas_recent['type'].apply(lambda x: 'A grignoté' if x == 'Grignotage' else 'A pris un repas complet')
    else: df_repas_recent = pd.DataFrame(columns=['id', 'pseudo', 'created_at', 'icone', 'details'])

    df_timeline = pd.concat([df_verres_recent[['id', 'pseudo', 'created_at', 'icone', 'details']], df_repas_recent[['id', 'pseudo', 'created_at', 'icone', 'details']]])

    if not df_timeline.empty:
        df_timeline = df_timeline.sort_values(by='created_at', ascending=False)
        for _, row in df_timeline.iterrows():
            heure = row['created_at'].strftime('%H:%M')
            with st.container():
                c_time, c_content, c_suppr = st.columns([1.5, 5, 1])
                with c_time: st.markdown(f"<div style='margin-top: 10px; text-align: right;'><span class='time-badge'>{heure}</span></div>", unsafe_allow_html=True)
                with c_content:
                    st.markdown(f"<div class='timeline-row'><span style='font-size: 1.2em;'>{row['icone']}</span> <span class='pseudo-text'>{row['pseudo']}</span><br><span class='details-text'>{row['details']}</span></div>", unsafe_allow_html=True)
                with c_suppr:
                    if st.button("❌", key=f"del_{row['icone']}_{row['id']}", use_container_width=True):
                        table_del = "drinks" if row['icone'] == '🍹' else "meals"
                        supabase.table(table_del).delete().eq("id", row['id']).execute()
                        st.cache_data.clear()
                        st.rerun()
    else: st.info("La soirée n'a pas encore commencé... ou tout le monde est à l'eau ! 🚰")

# --- 7. CONFIGURATION ÉQUIPE ---
with st.expander(f"⚙️ 7. Gérer l'équipe (Participants de '{groupe_actif}')", expanded=False):
    onglet_Ajusteur, tab_Ajouter, tab_Supprimer = st.tabs(["✏️ Ajuster les poids", "➕ Ajouter un invité", "🗑️ Supprimer un profil"])
    
    with onglet_Ajusteur:
        if not profils: st.write("Aucun profil à ajuster.")
        else:
            with st.form("form_poids"):
                cols = st.columns(len(profils) if len(profils) > 0 else 1)
                nouveaux_poids = {}
                for i, (nom, info) in enumerate(profils.items()):
                    with cols[i % len(cols)]:
                        st.markdown(f"<h5 style='color: orange;'>{nom}</h5>", unsafe_allow_html=True)
                        nouveaux_poids[nom] = st.number_input("Poids (kg)", min_value=40, max_value=150, value=info["poids"], key=f"input_poids_{nom}")
                if st.form_submit_button("Enregistrer les poids 💾"):
                    for nom in profils.keys():
                        supabase.table("profils").update({"poids": nouveaux_poids[nom]}).eq("id", profils[nom]["id"]).execute()
                    st.cache_data.clear()
                    st.rerun()
                
    with tab_Ajouter:
        if len(profils) >= 10: st.warning("🛑 Limite de 10 personnes atteinte.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1: nouveau_nom = st.text_input("Nom de l'invité (Unique)")
            with c2: nouveau_sexe = st.selectbox("Sexe", ["Homme", "Femme"])
            with c3: nouveau_poids_inv = st.number_input("Poids (kg)", 40, 150, 70)
            if st.button("Ajouter à la table"):
                if nouveau_nom and nouveau_nom not in profils:
                    supabase.table("profils").insert({"pseudo": nouveau_nom, "sexe": nouveau_sexe, "poids": nouveau_poids_inv, "groupe": groupe_actif}).execute()
                    st.cache_data.clear()
                    st.rerun()

    with tab_Supprimer:
        if profils:
            nom_a_supprimer = st.selectbox("Supprimer qui ?", list(profils.keys()))
            if st.button("Confirmer Suppression ❌"):
                supabase.table("profils").delete().eq("id", profils[nom_a_supprimer]["id"]).execute()
                st.cache_data.clear()
                st.rerun()

# --- 8. PARTAGER L'APPLICATION ---
with st.expander("🔗 8. Partager l'application", expanded=False):
    APP_URL = "https://lc-apero-eqdne2pvte4wak5sawi8kf.streamlit.app"
    st.text_input("Lien direct à copier/coller :", value=APP_URL)
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_centre, _ = st.columns([1, 2]) # Pour centrer un peu le QR code
    with col_centre:
        img = qrcode.make(APP_URL) 
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        st.image(buf.getvalue(), width=150, caption="Scanner pour rejoindre la table")

# --- 9. FAQ ---
st.markdown("<div id='faq'></div>", unsafe_allow_html=True)
with st.expander("❓ 9. FAQ - Guide d'utilisation", expanded=False):
    with st.expander("Comment fonctionne le système de tables ?"):
        st.write("Utilisez le menu déroulant de la Section 1 pour naviguer entre les soirées ou en créer une nouvelle. Chaque table a son propre historique et ses propres invités.")
    with st.expander("Peut-on utiliser l'application à plusieurs téléphones ?"):
        st.write("Absolument ! L'application est connectée à une base de données en temps réel. Dès qu'une personne ajoute un verre, l'historique de la table est mis à jour pour tout le monde.")
    with st.expander("Faut-il enregistrer le verre au début ou à la fin de la consommation ?"):
        st.write("Toujours au **début** (lors de votre première gorgée). L'algorithme calcule l'absorption et la montée du taux de manière progressive après l'heure indiquée.")
    with st.expander("Que se passe-t-il si j'utilise l'option 'J'ai oublié' ?"):
        st.write("L'application insère le verre à l'heure exacte demandée dans le passé et recalcule instantanément toute l'évolution des taux depuis cette heure-là pour tout le monde.")
    with st.expander("Pourquoi déclarer un repas ou un grignotage ?"):
        st.write("Manger ne fait pas baisser l'alcoolémie, mais cela ralentit considérablement l'absorption de l'alcool dans le sang. L'algorithme lissera votre courbe en conséquence pour éviter un pic trop violent.")
    with st.expander("Comment l'application calcule-t-elle mon taux ?"):
        st.write("Elle se base sur une version adaptée de la formule de Widmark, prenant en compte l'alcool pur, votre poids, le coefficient lié au sexe biologique, et une élimination moyenne de 0,15 g/L par heure.")
    with st.expander("Oups, je me suis trompé de verre. Que faire ?"):
        st.write("Descendez à la section '6. Historique de la soirée' et cliquez sur la croix rouge (❌) à côté du verre pour l'effacer. Le graphique se mettra à jour tout seul.")
    with st.expander("Qu'est-ce que le 'Max projeté' ?"):
        st.write("C'est le pic d'alcoolémie à venir, c'est-à-dire le taux le plus élevé que vous atteindrez dans le futur, lié à l'absorption de vos derniers verres.")

# --- 10. VERSIONS & MISES À JOUR ---
with st.expander("🏷️ 10. Version & Notes de mise à jour", expanded=False):
    st.markdown("""
    **Version actuelle : V3.5**
    
    **Quoi de neuf dans cette mise à jour (V3.5) ?**
    * 🎨 **Harmonisation UX/UI** : Les champs de texte, les boutons et les listes déroulantes partagent désormais le même design "Dark/Orange" que les sections.
    * 🪑 **Vue Table Interactive** : Ajout d'une modélisation de la table en Section 1. Les chaises reprennent la couleur exacte des courbes du graphique de chaque joueur !
    * 🗂️ **Réorganisation Logique** : "Table Active" et "Partager l'application" sont désormais intégrées proprement dans la numérotation des sections. L'ordre QR Code / Lien a été inversé pour plus de lisibilité.
    * 🖼️ **Lisibilité accrue** : Le "Tableau de Bord" et le "Hall of Fame" encadrent désormais chaque personne individuellement pour une lecture beaucoup plus claire, avec des titres harmonisés.
    * ❓ **FAQ Dynamique** : Les questions de la FAQ sont désormais rangées dans des menus déroulants individuels pour éviter de surcharger l'écran.
    """)

# --- 11. ADMINISTRATION ---
with st.expander("🚨 11. Zone de danger (Gestion BDD)", expanded=False):
    with st.form("form_effacer"):
        mdp = st.text_input("Mot de passe administrateur :", type="password")
        choix_effacer = st.radio("Action souhaitée :", [
            f"🧹 Vider uniquement l'historique de '{groupe_actif}' (Garder les profils)", 
            f"🗑️ SUPPRIMER ENTIÈREMENT LA TABLE '{groupe_actif}'"
        ])
        if st.form_submit_button("EXÉCUTER L'ACTION"):
            if mdp == "lolo":
                if "Vider" in choix_effacer:
                    supabase.table("drinks").delete().eq("groupe", groupe_actif).execute()
                    supabase.table("meals").delete().eq("groupe", groupe_actif).execute()
                    st.success(f"Historique de {groupe_actif} effacé avec succès.")
                elif "SUPPRIMER" in choix_effacer:
                    supabase.table("drinks").delete().eq("groupe", groupe_actif).execute()
                    supabase.table("meals").delete().eq("groupe", groupe_actif).execute()
                    supabase.table("profils").delete().eq("groupe", groupe_actif).execute()
                    st.session_state.groupe_selectionne = "Haggis et les cafards"
                    st.success(f"La table '{groupe_actif}' a été complètement supprimée.")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")

# --- 12. MENTIONS LÉGALES ---
st.markdown("""
    <div style='text-align: center; color: #888888; font-size: 11px; margin-top: 30px; padding-bottom: 30px; line-height: 1.5;'>
        ⚠️ <b>AVERTISSEMENT LÉGAL ET DE SANTÉ</b><br><br>
        Les résultats fournis par cette application sont basés sur des modélisations mathématiques théoriques (formule de Widmark modifiée) 
        et ne sont donnés qu'à titre purement indicatif. En aucun cas ces données ne peuvent se substituer à un véritable éthylotest homologué, 
        à une prise de sang ou à un avis médical. Chaque métabolisme est unique et réagit différemment à l'alcool.<br><br>
        L'abus d'alcool est dangereux pour la santé, à consommer avec modération. En cas de doute, la règle d'or absolue s'applique : 
        <b>Si tu as bu, tu ne conduis pas !</b><br><br>
        <i>Et surtout, ne mange pas trop gras, trop sucré, trop salé...</i>
    </div>
    """, unsafe_allow_html=True)
