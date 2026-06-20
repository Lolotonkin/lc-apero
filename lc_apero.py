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

# --- GESTION DE LA LANGUE ---
if "lang" not in st.session_state:
    st.session_state.lang = "FR"

st.markdown("""
    <style>
    /* Thème général & Tailles réduites */
    .stApp, .stApp > header { background-color: #000000 !important; color: #FFFFFF !important; }
    
    /* --- NOUVEAU : CORRECTION POUR LE SCROLL MOBILE --- */
    .main, .stApp, .stPlotlyChart, div[data-testid="stPlotlyChart"] {
        touch-action: pan-y !important;
    }
    /* --------------------------------------------------- */

    h1 { color: #FF9800 !important; font-weight: bold !important; font-size: 2.0em !important; }
    h2 { color: #FF9800 !important; font-weight: bold !important; font-size: 1.5em !important; }
    h3, p, span, label, div[data-testid="stMarkdownContainer"] { color: #FFFFFF !important; }
    
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
    
    /* Correction visibilité titres expanders légèrement réduits */
    div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary * { 
        color: #FF9800 !important; 
        font-weight: bold !important; 
        font-size: 1.05em !important; 
    }
    
    div[data-testid="stMetricValue"] { color: #FF9800 !important; font-size: 1.8em !important; }

    /* Timeline CSS */
    .timeline-row { border-left: 3px solid #FF9800; padding-left: 15px; margin-bottom: 5px; }
    .time-badge { color: #FF9800; font-weight: bold; font-size: 1.1em; }
    .pseudo-text { color: #FFFFFF; font-weight: bold; font-size: 1.0em; }
    .details-text { color: #CCCCCC; font-size: 0.85em; }
    </style>
    """, unsafe_allow_html=True)

# --- DICTIONNAIRE DE TRADUCTIONS ---
TRAD = {
    "FR": {
        "titre": "Suivi de soirée 🍹",
        "faq_lien": "❓ Une question ? Consulter la FAQ en bas",
        "sec1": "🌐 1. Vue d'ensemble de la salle de bar & Table active",
        "sec2": "🍹 2. Déclarer une consommation",
        "sec3": "📍 3. Tableau de bord instantané",
        "sec4": "🏆 4. Hall of Fame (Records & Statistiques)",
        "sec5": "📊 5. Courbes (Évolution)",
        "sec6": "📋 6. Historique de la soirée (Timeline 24h)",
        "sec7": "⚙️ 7. Gérer l'équipe (Participants)",
        "sec8": "🔗 8. Partager l'application",
        "sec9": "❓ 9. FAQ - Guide d'utilisation",
        "sec10": "🏷️ 10. Version & Notes de mise à jour",
        "sec11": "🚨 11. Zone de danger (Gestion BDD)",
        "sec12": "🔄 12. Mettre à jour l'application & Mentions légales",
        "btn_maj": "🔄 Mettre à jour les données",
        "table_choix": "Sélectionnez une table à rejoindre ou créez-en une :",
        "creer_table": "➕ Créer une nouvelle table...",
        "nom_table_placeholder": "Nom de la table (ex: Sopemea)",
        "btn_rejoindre": "Rejoindre 🚀",
        "btn_retour_bar": "🚪 Retourner à la grande salle du bar",
        "wa_alertes": "Activer les alertes WhatsApp",
        "type_entree": "Type d'entrée :",
        "verre_amitie": "Un verre de l'amitié 🍺",
        "repas_complet": "Un repas complet 🍽️",
        "grignotage": "Grignotage (Apéro) 🥨",
        "oubli_retro": "🕰️ J'ai oublié de le noter sur le moment (modifier l'heure)",
        "heure_conso": "Heure de la consommation :",
        "qui_mange": "Qui a mangé ?",
        "qui_consomme": "Qui consomme ?",
        "vol_cl": "Volume (cl)",
        "deg_alc": "Degré d'alcool (%)",
        "btn_enregistrer": "Enregistrer 💾",
        "btn_enregistrer_verre": "Enregistrer le verre 💾",
        "txt_attente_profils": "En attente de profils pour calculer les taux.",
        "taux_actuel": "Taux Actuel",
        "max_proj": "Max projeté :",
        "conduite": "🚗 Conduite (<0.5):",
        "ajeun": "💧 À jeun (0.0):",
        "partage_wa": "📲 Partager le bilan sur WhatsApp",
        "record_absolu": "🔥 Record absolu de la table :",
        "legende_titre": "💡 Signification des statuts d'alcoolémie :",
        "txt_historique_vide": "La soirée n'a pas encore commencé... ou tout le monde est à l'eau ! 🚰",
        "onglet_poids": "✏️ Ajuster les poids",
        "onglet_ajouter": "➕ Ajouter un invité",
        "onglet_suppr": "🗑️ Supprimer un profil",
        "btn_enr_poids": "Enregistrer les poids 💾",
        "nom_invite": "Nom de l'invité (Unique)",
        "btn_ajouter_table": "Ajouter à la table",
        "suppr_qui": "Supprimer qui ?",
        "btn_confirmer_suppr": "Confirmer Suppression ❌",
        "lien_direct": "Lien direct à copier/coller :",
        "qr_caption": "Scanner pour rejoindre la table",
        "danger_titre": "Action souhaitée :",
        "danger_vider": "🧹 Vider uniquement l'historique (Garder les profils)",
        "danger_suppr_tout": "🗑️ SUPPRIMER ENTIÈREMENT LA TABLE",
        "btn_executer": "EXÉCUTER L'ACTION",
        "admin_pwd": "Mot de passe administrateur :",
    },
    "EN": {
        "titre": "Party Tracker 🍹",
        "faq_lien": "❓ Questions? Check the FAQ below",
        "sec1": "🌐 1. Bar Room Overview & Active Table",
        "sec2": "🍹 2. Log a Consumption",
        "sec3": "📍 3. Instant Dashboard",
        "sec4": "🏆 4. Hall of Fame (Records & Statistics)",
        "sec5": "📊 5. Charts (Evolution)",
        "sec6": "📋 6. Party Timeline (24h)",
        "sec7": "⚙️ 7. Manage Team (Participants)",
        "sec8": "🔗 8. Share App",
        "sec9": "❓ 9. FAQ - User Guide",
        "sec10": "🏷️ 10. Version & Release Notes",
        "sec11": "🚨 11. Danger Zone (DB Management)",
        "sec12": "🔄 12. Refresh Application & Legal Warnings",
        "btn_maj": "🔄 Refresh Data",
        "table_choix": "Select a table to join or create a new one:",
        "creer_table": "➕ Create a new table...",
        "nom_table_placeholder": "Table name (e.g., Sopemea)",
        "btn_rejoindre": "Join 🚀",
        "btn_retour_bar": "🚪 Return to the main Bar Room",
        "wa_alertes": "Enable WhatsApp alerts",
        "type_entree": "Input type:",
        "verre_amitie": "A friendly drink 🍺",
        "repas_complet": "Full meal 🍽️",
        "grignotage": "Snacks (Appetizer) 🥨",
        "oubli_retro": "🕰️ I forgot to log it earlier (change time)",
        "heure_conso": "Time of consumption:",
        "qui_mange": "Who ate?",
        "qui_consomme": "Who is consuming?",
        "vol_cl": "Volume (cl)",
        "deg_alc": "Alcohol level (%)",
        "btn_enregistrer": "Save 💾",
        "btn_enregistrer_verre": "Save Drink 💾",
        "txt_attente_profils": "Waiting for profiles to calculate levels.",
        "taux_actuel": "Current Level",
        "max_proj": "Projected Max:",
        "conduite": "🚗 Driving (<0.5):",
        "ajeun": "💧 Sober (0.0):",
        "partage_wa": "📲 Share summary on WhatsApp",
        "record_absolu": "🔥 Absolute table record:",
        "legende_titre": "💡 Meaning of BAC status badges:",
        "txt_historique_vide": "The party hasn't started yet... or everyone is drinking water! 🚰",
        "onglet_poids": "✏️ Adjust weights",
        "onglet_ajouter": "➕ Add guest",
        "onglet_suppr": "🗑️ Delete a profile",
        "btn_enr_poids": "Save weights 💾",
        "nom_invite": "Guest name (Unique)",
        "btn_ajouter_table": "Add to table",
        "suppr_qui": "Delete whom?",
        "btn_confirmer_suppr": "Confirm Deletion ❌",
        "lien_direct": "Direct link to copy/paste:",
        "qr_caption": "Scan to join the table",
        "danger_titre": "Desired Action:",
        "danger_vider": "🧹 Clear history only (Keep profiles)",
        "danger_suppr_tout": "🗑️ COMPLETELY DELETE THE TABLE",
        "btn_executer": "EXECUTE ACTION",
        "admin_pwd": "Administrator password:",
    }
}

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
# EN-TÊTE PRINCIPAL & SÉLECTION LANGUE
# ==========================================
col_titre, col_lang = st.columns([3, 1])
with col_titre:
    st.title(TRAD[st.session_state.lang]["titre"])
    st.markdown("<h5 style='color: #FF9800; margin-top: -15px;'>Version 4.0</h5>", unsafe_allow_html=True)
with col_lang:
    lang_choix = st.radio("Langue", ["🇫🇷 FR", "🇬🇧 EN"], horizontal=True, label_visibility="collapsed")
    st.session_state.lang = "FR" if "🇫🇷" in lang_choix else "EN"

st.markdown(f"<p style='text-align: right;'><a href='#faq' style='color: #FF9800; text-decoration: none;'>{TRAD[st.session_state.lang]['faq_lien']}</a></p>", unsafe_allow_html=True)

# --- GESTION VARIABLES SESSION ---
tables_existantes = obtenir_toutes_les_tables()
if "Haggis et les cafards" not in tables_existantes:
    tables_existantes.insert(0, "Haggis et les cafards")

if "groupe_selectionne" not in st.session_state:
    st.session_state.groupe_selectionne = "Haggis et les cafards"

if "salle_bar_active" not in st.session_state:
    st.session_state.salle_bar_active = True

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

# --- NOUVEAU : CORRECTION DE L'ERREUR SUPABASE (TRY/EXCEPT) ---
# Initialisation par défaut si vide et Haggis
if not profils and groupe_actif == "Haggis et les cafards":
    defauts = [
        {"pseudo": "Lolo", "sexe": "Homme", "poids": 75, "groupe": groupe_actif},
        {"pseudo": "Poums", "sexe": "Homme", "poids": 75, "groupe": groupe_actif},
        {"pseudo": "Nico", "sexe": "Homme", "poids": 75, "groupe": groupe_actif},
        {"pseudo": "Duj", "sexe": "Homme", "poids": 75, "groupe": groupe_actif}
    ]
    try:
        supabase.table("profils").insert(defauts).execute()
        st.cache_data.clear()
        profils = charger_profils(groupe_actif)
    except Exception as e:
        print(f"Erreur d'insertion des profils (ignorée) : {e}")
# --------------------------------------------------------------

# --- CALCUL PRÉLIMINAIRE DES TAUX POUR LES BADGES DU PLAN DE TABLE ---
@st.cache_data(ttl=2)
def charger_donnees(groupe):
    try:
        boissons = supabase.table("drinks").select("*").eq("groupe", groupe).order("created_at", desc=False).execute()
        repas = supabase.table("meals").select("*").eq("groupe", groupe).order("created_at", desc=False).execute()
        return (boissons.data or []), (repas.data or [])
    except: return [], []

boissons_nuageuses, repas_nuage = charger_donnees(groupe_actif)

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
        if jours_ecoules == 0: texte_jours = "Aujourd'hui 🍻" if st.session_state.lang == "FR" else "Today 🍻"
        elif jours_ecoules == 1: texte_jours = "Hier 💧" if st.session_state.lang == "FR" else "Yesterday 💧"
        else: texte_jours = f"{jours_ecoules} j. 💧" if st.session_state.lang == "FR" else f"{jours_ecoules} d. 💧"
    else:
        jours_ecoules = -1
        texte_jours = "Jamais bu 😇" if st.session_state.lang == "FR" else "Sober 😇"
        
    stats_joueurs[nom] = {"max_ever": max_historique, "texte_jours": texte_jours, "jours_ecoules": jours_ecoules, "total_verres": len(verres_perso)}

# Fonction utilitaire pour trouver le badge graphique
def determiner_badge(score):
    if score >= 2.0: return "🧟‍♂️"
    elif score >= 1.5: return "🏴‍☠️"
    elif score >= 1.0: return "🥳"
    elif score >= 0.5: return "🍺"
    elif score > 0.01: return "👼"
    return "🚰"

record_absolu_groupe = max([s['max_ever'] for s in stats_joueurs.values()]) if stats_joueurs else 0.0

# --- 1. CONFIGURATION DE LA SALLE DE BAR ET TABLE ACTIVE ---
with st.expander(TRAD[st.session_state.lang]["sec1"], expanded=True):
    
    # CAS A : VUE SALLE DE BAR GLOBALE INTERACTIVE (SANS MENUS DÉROULANTS REDONDANTS)
    if st.session_state.salle_bar_active:
        st.markdown(f"### 🚪 Grand Salon des Tables")
        
        # Dessin Plotly adaptatif
        fig_salle = go.Figure()
        
        num_tables = len(tables_existantes)
        for idx, t_name in enumerate(tables_existantes):
            # Espacement élargi pour donner de la place aux grands carrés
            x_pos = (idx % 2) * 4.0
            y_pos = -(idx // 2) * 4.0
            
            # Nouvelles couleurs plus modernes et translucides
            if t_name == groupe_actif:
                fill_color = "rgba(255, 152, 0, 0.2)" # Fond orange
                line_color = "#FF9800"
            else:
                fill_color = "rgba(52, 152, 219, 0.15)" # Fond bleu
                line_color = "#3498db"
                
            # Tronquer le nom s'il est vraiment trop long pour entrer dans le carré
            nom_affiche = t_name if len(t_name) < 18 else t_name[:15] + "..."
            
            # Injection de la table (grand carré avec texte au centre)
            fig_salle.add_trace(go.Scatter(
                x=[x_pos],
                y=[y_pos],
                mode="markers+text",
                marker=dict(
                    symbol="square", 
                    size=100, 
                    color=fill_color, 
                    line=dict(width=4, color=line_color)
                ),
                text=[f"<b>{nom_affiche}</b>"],
                textposition="middle center",
                textfont=dict(color="#FFFFFF", size=13, family="Arial"),
                customdata=[t_name],
                hovertext=[f"Rejoindre la table : {t_name}"],
                hoverinfo="text"
            ))

        # Position de la table d'ajout virtuelle
        if num_tables < 10:
            x_add = (num_tables % 2) * 4.0
            y_add = -(num_tables // 2) * 4.0
            
            fig_salle.add_trace(go.Scatter(
                x=[x_add],
                y=[y_add],
                mode="markers+text",
                marker=dict(
                    symbol="square",
                    size=100, 
                    color="rgba(46, 204, 113, 0.1)", 
                    line=dict(width=3, color="#2ecc71", dash="dash")
                ),
                text=[f"<b>➕ Créer</b>"],
                textposition="middle center",
                textfont=dict(color="#2ecc71", size=13, family="Arial"),
                customdata=["CREER_TABLE"],
                hoverinfo="text"
            ))

        max_rows = (num_tables // 2) + 1
        fig_salle.update_layout(
            xaxis=dict(visible=False, range=[-2.0, 6.0], fixedrange=True), 
            yaxis=dict(visible=False, range=[-(max_rows * 4.0) + 1.0, 2.0], fixedrange=True), 
            height=250 + (max_rows * 130), 
            margin=dict(l=10, r=10, t=10, b=10), 
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False
        )
        
        # Capture de l'événement de sélection natif
        select_data = st.plotly_chart(fig_salle, use_container_width=True, on_select="rerun", config={'displayModeBar': False})
        
        # Interception directe du clic
        if select_data and "selection" in select_data and "points" in select_data["selection"]:
            points = select_data["selection"]["points"]
            if len(points) > 0:
                clicked_customdata = points[0].get("customdata")
                if clicked_customdata == "CREER_TABLE":
                    st.session_state.afficher_creation_table = True
                elif clicked_customdata in tables_existantes:
                    st.session_state.groupe_selectionne = clicked_customdata
                    st.session_state.salle_bar_active = False
                    st.session_state.afficher_creation_table = False
                    st.cache_data.clear()
                    st.rerun()

        # Bloc d'insertion si déclenchement de la création
        if st.session_state.get("afficher_creation_table", False):
            st.markdown("---")
            if len(tables_existantes) >= 10:
                st.error("🛑 Limite de 10 tables atteinte. Impossible de créer une nouvelle table.")
            else:
                col_nom, col_btn = st.columns([3, 1])
                with col_nom:
                    nom_nouvelle_table = st.text_input("Nom :", label_visibility="collapsed", placeholder=TRAD[st.session_state.lang]["nom_table_placeholder"])
                with col_btn:
                    if st.button(TRAD[st.session_state.lang]["btn_rejoindre"], use_container_width=True):
                        if nom_nouvelle_table.strip():
                            nom_t = nom_nouvelle_table.strip()
                            
                            try:
                                supabase.table("profils").insert({
                                    "pseudo": "Hôte", 
                                    "sexe": "Homme", 
                                    "poids": 75, 
                                    "groupe": nom_t
                                }).execute()
                            except:
                                pass
                            
                            st.session_state.groupe_selectionne = nom_t
                            st.session_state.salle_bar_active = False
                            st.session_state.afficher_creation_table = False
                            st.cache_data.clear()
                            st.rerun()

    # CAS B : VUE DE LA TABLE ACTIVE AVEC SES CHAISES, COULEURS ET BADGES
    else:
        st.markdown(f"### 🍹 Table active : {groupe_actif}")
        if st.button(TRAD[st.session_state.lang]["btn_retour_bar"], use_container_width=True):
            st.session_state.salle_bar_active = True
            st.rerun()
            
        envoyer_wa = st.checkbox(TRAD[st.session_state.lang]["wa_alertes"], value=True)

        if profils:
            fig_table = go.Figure()
            fig_table.add_shape(type="circle", x0=-0.8, y0=-0.8, x1=0.8, y1=0.8, fillcolor="#1A1A1A", line_color="#FF9800", line_width=3)
            fig_table.add_annotation(x=0, y=0, text=groupe_actif, showarrow=False, font=dict(color="#FF9800", size=13, family="Arial", weight="bold"))
            
            num_chairs = len(profils)
            angles = np.linspace(0, 2*np.pi, num_chairs, endpoint=False)
            rayon_chaises = 1.2
            rayon_texte = 1.65
            
            for idx, (nom, info) in enumerate(profils.items()):
                angle = angles[idx]
                cx = rayon_chaises * np.cos(angle)
                cy = rayon_chaises * np.sin(angle)
                tx = rayon_texte * np.cos(angle)
                ty = rayon_texte * np.sin(angle)
                couleur_chaise = COULEURS_JOUEURS[idx % len(COULEURS_JOUEURS)]
                
                t_actuel = df_graphique[nom].iloc[idx_maintenant] if nom in df_graphique.columns else 0.0
                b_emoji = determiner_badge(t_actuel)
                
                score_max_joueur = stats_joueurs.get(nom, {}).get("max_ever", 0.0)
                prefixe_couronne = "👑" if (score_max_joueur == record_absolu_groupe and record_absolu_groupe > 0.01) else ""
                
                fig_table.add_shape(type="circle", x0=cx-0.2, y0=cy-0.2, x1=cx+0.2, y1=cy+0.2, fillcolor=couleur_chaise, line_color="#FFFFFF", line_width=2)
                fig_table.add_annotation(x=cx, y=cy, text=b_emoji, showarrow=False, font=dict(size=11))
                fig_table.add_annotation(x=tx, y=ty, text=f"{prefixe_couronne}{nom}", showarrow=False, font=dict(color="#FFFFFF", size=11, family="Arial"))

            fig_table.update_layout(
                xaxis=dict(visible=False, range=[-2.2, 2.2], fixedrange=True), 
                yaxis=dict(visible=False, range=[-2.2, 2.2], fixedrange=True), 
                width=350, height=350, 
                margin=dict(l=0, r=0, t=10, b=10), 
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False
            )
            st.plotly_chart(fig_table, use_container_width=True, config={'displayModeBar': False})

def envoyer_alerte_whatsapp(pseudo, detail_conso, type_event="Verre"):
    if not URL_WEBHOOK_WHATSAPP or not envoyer_wa: return
    if type_event == "Repas": texte = f"🍽️ *Suivi de soirée ({groupe_actif})* : {pseudo} déclare un repas complet. 🥪"
    elif type_event == "Grignotage": texte = f"🥨 *Suivi de soirée ({groupe_actif})* : {pseudo} grignote à l'apéro. 🥜"
    else: texte = f"🍹 *Suivi de soirée ({groupe_actif})* : {pseudo} a pris : {detail_conso} 📈"
    try: requests.post(URL_WEBHOOK_WHATSAPP, json={"message": texte, "pseudo": pseudo})
    except: pass

# --- 2. DÉCLARATION DES CONSOMMATIONS ---
with st.expander(TRAD[st.session_state.lang]["sec2"], expanded=False):
    if not profils:
        st.error("⚠️ Cette table est vide. Descendez à la section '7. Gérer l'équipe' pour ajouter des invités !")
    else:
        choix_type = st.radio(TRAD[st.session_state.lang]["type_entree"], [TRAD[st.session_state.lang]["verre_amitie"], TRAD[st.session_state.lang]["repas_complet"], TRAD[st.session_state.lang]["grignotage"]], horizontal=True)
        
        oubli = st.checkbox(TRAD[st.session_state.lang]["oubli_retro"])
        maintenant_local = pd.Timestamp.now(tz='Europe/Paris')
        
        if oubli:
            if "heure_perso_val" not in st.session_state:
                st.session_state.heure_perso_val = maintenant_local.time().replace(second=0, microsecond=0)
            heure_perso = st.time_input(TRAD[st.session_state.lang]["heure_conso"], value=st.session_state.heure_perso_val, key="widget_heure_oubli")
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

        if "repas" in choix_type.lower() or "meal" in choix_type.lower() or "grignotage" in choix_type.lower() or "snack" in choix_type.lower():
            type_repas = "Repas" if ("repas" in choix_type.lower() or "meal" in choix_type.lower()) else "Grignotage"
            Qui = st.selectbox(TRAD[st.session_state.lang]["qui_mange"], list(profils.keys()))
            if st.button(TRAD[st.session_state.lang]["btn_enregistrer"]):
                supabase.table("meals").insert({"pseudo": Qui, "created_at": moment_actuel, "groupe": groupe_actif, "type": type_repas}).execute()
                st.cache_data.clear() 
                envoyer_alerte_whatsapp(Qui, f"{type_repas} à {affichage_heure}", type_event=type_repas)
                st.success(f"✔️ {type_repas} enregistré pour {Qui} à {affichage_heure}")
                st.rerun()
        else:
            c1, c2, c3 = st.columns(3)
            with c1: Qui = st.selectbox(TRAD[st.session_state.lang]["qui_consomme"], list(profils.keys()))
            with c2: Volume_cl = st.number_input(TRAD[st.session_state.lang]["vol_cl"], min_value=1, max_value=200, value=25, step=1)
            with c3: Degre_Alcool = st.number_input(TRAD[st.session_state.lang]["deg_alc"], min_value=0.5, max_value=90.0, value=5.0, step=0.5)

            if st.button(TRAD[st.session_state.lang]["btn_enregistrer_verre"]):
                boisson_label = f"{Volume_cl}cl @ {Degre_Alcool}%"
                alcool_g = float((Volume_cl * 10) * (Degre_Alcool / 100) * 0.8)
                supabase.table("drinks").insert({"pseudo": Qui, "boisson": boisson_label, "alcool_g": alcool_g, "created_at": moment_actuel, "groupe": groupe_actif}).execute()
                st.cache_data.clear() 
                envoyer_alerte_whatsapp(Qui, f"{boisson_label} à {affichage_heure}", type_event="Verre")
                st.success(f"🍹 Verre enregistré pour {Qui} à {affichage_heure}")
                st.rerun()

# --- 3. TABLEAU DE BORD INSTANTANÉ ---
with st.expander(TRAD[st.session_state.lang]["sec3"], expanded=False):
    if not profils:
        st.warning(TRAD[st.session_state.lang]["txt_attente_profils"])
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
            else: retour_zero = "À jeun" if st.session_state.lang == "FR" else "Sober"
                
            if donnees_futures.empty or taux_max_futur < 0.5: heure_conduite = "Maintenant ✅" if st.session_state.lang == "FR" else "Now ✅"
            else:
                heure_pic = donnees_futures.idxmax()
                donnees_apres_pic = donnees_futures.loc[heure_pic:]
                temps_conduite = donnees_apres_pic[donnees_apres_pic < 0.5]
                heure_conduite = temps_conduite.index[0].strftime("%H:%M") if not temps_conduite.empty else "Trop tard 🛑" if st.session_state.lang == "FR" else "Too late 🛑"

            with cols_dashboard[i % len(cols_dashboard)]:
                with st.container(border=True):
                    st.markdown(f"#### {nom}")
                    st.metric(label=TRAD[st.session_state.lang]["taux_actuel"], value=f"{taux_actuel:.2f} g/L")
                    st.markdown(f"**{TRAD[st.session_state.lang]['max_proj']}** {taux_max_futur:.2f} g/L")
                    st.markdown(f"**{TRAD[st.session_state.lang]['conduite']}** {heure_conduite}")
                    st.markdown(f"**{TRAD[st.session_state.lang]['ajeun']}** {retour_zero}")
                
            texte_whatsapp += f"• *{nom}* : {taux_actuel:.2f}g/L (Max: {taux_max_futur:.2f})\n"

        texte_wa_encode = urllib.parse.quote(texte_whatsapp)
        lien_partage_whatsapp = f"https://api.whatsapp.com/send?text={texte_wa_encode}"
        st.markdown("<br>", unsafe_allow_html=True)
        st.link_button(TRAD[st.session_state.lang]["partage_wa"], lien_partage_whatsapp)
    
# --- 4. HALL OF FAME & SIGNIFICATION BADGES ---
with st.expander(TRAD[st.session_state.lang]["sec4"], expanded=False):
    st.markdown(f"<h4 style='color: orange; margin-bottom: 10px;'>{TRAD[st.session_state.lang]['record_absolu']} {record_absolu_groupe:.2f} g/L</h4>", unsafe_allow_html=True)
    
    st.markdown(f"**{TRAD[st.session_state.lang]['legende_titre']}**")
    col_leg1, col_leg2, col_leg3 = st.columns(3)
    with col_leg1:
        st.markdown("* `🧟‍♂️` **Zombie** : >= 2.0 g/L\n* `🏴‍☠️` **Pirate** : >= 1.5 g/L")
    with col_leg2:
        st.markdown("* `🥳` **Fêtard** : >= 1.0 g/L\n* `🍺` **Limite conduite** : >= 0.5 g/L")
    with col_leg3:
        st.markdown("* `👼` **Ange (Joyeux)** : > 0.0 g/L\n* `🚰` **À l'eau (Sobre)** : 0.0 g/L")
    
    st.markdown("---")
    
    cols_stats = st.columns(len(profils) if profils else 1)
    for i, (nom, stats) in enumerate(stats_joueurs.items()):
        score = stats['max_ever']
        badge_record = ""
        if score == record_absolu_groupe and score > 0.01: badge_record += "👑 "
        badge_record += determiner_badge(score)

        jours = stats['jours_ecoules']
        if jours == -1: badge_sobriete = "🕊️ Pureté" if st.session_state.lang == "FR" else "🕊️ Pure"
        elif jours >= 30: badge_sobriete = "🧘 1 mois+"
        elif jours >= 14: badge_sobriete = "🛡️ 2 sem+"
        elif jours >= 7: badge_sobriete = "🌱 1 sem+"
        elif jours >= 5: badge_sobriete = "🐫 5j+"
        elif jours >= 3: badge_sobriete = "🔋 3j+"
        elif jours >= 1: badge_sobriete = "☀️ 1j+"
        else: badge_sobriete = "🔥 En activité" if st.session_state.lang == "FR" else "🔥 Active"

        with cols_stats[i % len(cols_stats)]:
            with st.container(border=True):
                st.markdown(f"#### {nom}")
                st.markdown(f"**Record max :** {score:.2f} {badge_record}")
                st.markdown(f"**Dernier verre :** {stats['texte_jours']}")
                st.markdown(f"**Sobriété :** `{badge_sobriete}`")
                st.markdown(f"**Total bu :** {stats['total_verres']} v.")

# --- 5. GRAPHIQUE ---
with st.expander(TRAD[st.session_state.lang]["sec5"], expanded=False):
    if not df_verres.empty and profils:
        choix_vue = st.radio("Période / Period :", ["Standard (H-2 à H+6)", "Demi-journée (H-12 à H+12)", "Week-end (H-24 à H+12)"], horizontal=True, label_visibility="collapsed")
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
        st.info("Aucun verre enregistré sur cette table." if st.session_state.lang == "FR" else "No drinks logged yet.")

# --- 6. HISTORIQUE ---
with st.expander(TRAD[st.session_state.lang]["sec6"], expanded=False):
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
    else: st.info(TRAD[st.session_state.lang]["txt_historique_vide"])

# --- 7. CONFIGURATION ÉQUIPE ---
with st.expander(TRAD[st.session_state.lang]["sec7"], expanded=False):
    onglet_Ajusteur, tab_Ajouter, tab_Supprimer = st.tabs([TRAD[st.session_state.lang]["onglet_poids"], TRAD[st.session_state.lang]["onglet_ajouter"], TRAD[st.session_state.lang]["onglet_suppr"]])
    
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
                if st.form_submit_button(TRAD[st.session_state.lang]["btn_enr_poids"]):
                    for nom in profils.keys():
                        supabase.table("profils").update({"poids": nouveaux_poids[nom]}).eq("id", profils[nom]["id"]).execute()
                    st.cache_data.clear()
                    st.rerun()
                
    with tab_Ajouter:
        if len(profils) >= 10: st.warning("🛑 Limite de 10 personnes atteinte.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1: nouveau_nom = st.text_input(TRAD[st.session_state.lang]["nom_invite"])
            with c2: nouveau_sexe = st.selectbox("Sexe", ["Homme", "Femme"] if st.session_state.lang == "FR" else ["Homme", "Femme"])
            with c3: nouveau_poids_inv = st.number_input("Poids (kg)", 40, 150, 70)
            if st.button(TRAD[st.session_state.lang]["btn_ajouter_table"]):
                if nouveau_nom and nouveau_nom not in profils:
                    try:
                        supabase.table("profils").insert({"pseudo": nouveau_nom, "sexe": "Homme" if nouveau_sexe == "Homme" else "Femme", "poids": nouveau_poids_inv, "groupe": groupe_actif}).execute()
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"🚨 Supabase a refusé l'insertion du profil. Raison : {e}")

    with tab_Supprimer:
        if profils:
            nom_a_supprimer = st.selectbox(TRAD[st.session_state.lang]["suppr_qui"], list(profils.keys()))
            if st.button(TRAD[st.session_state.lang]["btn_confirmer_suppr"]):
                supabase.table("profils").delete().eq("id", profils[nom_a_supprimer]["id"]).execute()
                st.cache_data.clear()
                st.rerun()

# --- 8. PARTAGER L'APPLICATION ---
with st.expander(TRAD[st.session_state.lang]["sec8"], expanded=False):
    APP_URL = "https://lc-apero-eqdne2pvte4wak5sawi8kf.streamlit.app"
    st.markdown(f"**{TRAD[st.session_state.lang]['lien_direct']}**")
    st.text_input("URL", value=APP_URL, label_visibility="collapsed")
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_centre, _ = st.columns([1, 2])
    with col_centre:
        img = qrcode.make(APP_URL) 
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        st.image(buf.getvalue(), width=150, caption=TRAD[st.session_state.lang]["qr_caption"])

# --- 9. FAQ ---
st.markdown("<div id='faq'></div>", unsafe_allow_html=True)
with st.expander(TRAD[st.session_state.lang]["sec9"], expanded=False):
    
    with st.expander("Comment fonctionne le système de tables ?" if st.session_state.lang == "FR" else "How does the table system work?"):
        st.write("Utilisez l'interface de la Section 1 pour créer ou rejoindre des tables indépendantes. Chaque table a son propre historique et ses propres invités." if st.session_state.lang == "FR" else "Use the Section 1 interface to create or join independent tables. Each table has its own history and guests.")
        
    with st.expander("Comment inviter des amis sur ma table ?" if st.session_state.lang == "FR" else "How do I invite friends to my table?"):
        st.write("Allez dans la section '8. Partager l'application'. Vous y trouverez un QR Code que vos amis peuvent scanner, ainsi qu'un lien direct à leur envoyer." if st.session_state.lang == "FR" else "Go to section '8. Share App'. You will find a QR Code for your friends to scan, and a direct link to send them.")

    with st.expander("Peut-on utiliser l'application à plusieurs téléphones ?" if st.session_state.lang == "FR" else "Can we use the app on multiple phones?"):
        st.write("Absolument ! Tout est synchronisé en temps réel sur la base de données cloud." if st.session_state.lang == "FR" else "Absolutely! Everything is synced in real-time on the cloud database.")

    with st.expander("Est-ce que je peux corriger un verre si je me suis trompé ?" if st.session_state.lang == "FR" else "Can I correct a drink if I made a mistake?"):
        st.write("Oui ! Allez dans la section '6. Historique de la soirée'. Vous trouverez une croix rouge (❌) à côté de chaque consommation pour la supprimer." if st.session_state.lang == "FR" else "Yes! Go to section '6. Party Timeline'. You will find a red cross (❌) next to each drink to delete it.")

    with st.expander("Pourquoi déclarer un repas ou un grignotage ?" if st.session_state.lang == "FR" else "Why log a meal or a snack?"):
        st.write("Manger ralentit grandement la vitesse d'absorption de l'alcool dans le sang. Le système prend en compte cette digestion pour lisser votre pic d'alcoolémie." if st.session_state.lang == "FR" else "Eating slows down alcohol absorption. The system accounts for this digestion to smooth out your BAC peak.")

    with st.expander("Pourquoi mon taux d'alcool continue de monter alors que je ne bois plus ?" if st.session_state.lang == "FR" else "Why does my BAC keep rising when I stopped drinking?"):
        st.write("C'est physiologique ! L'alcool met entre 30 minutes (à jeun) et 1 heure (pendant un repas) pour atteindre le sang. Le pic est donc toujours décalé par rapport au moment où vous buvez." if st.session_state.lang == "FR" else "It's physiological! Alcohol takes 30 mins (sober) to 1 hour (with a meal) to reach the blood. The peak is always delayed.")

    with st.expander("Comment sont attribués les badges (Pirate, Zombie...) ?" if st.session_state.lang == "FR" else "How are the badges (Pirate, Zombie...) assigned?"):
        st.write("Ils dépendent de votre taux (g/L) : Ange (>0), Fêtard (>=1.0), Pirate (>=1.5), et Zombie (>=2.0). C'est juste pour le fun, restez prudents !" if st.session_state.lang == "FR" else "They depend on your BAC (g/L): Angel (>0), Partygoer (>=1.0), Pirate (>=1.5), and Zombie (>=2.0). It's just for fun, stay safe!")

    with st.expander("Que signifie le bouton 'Mettre à jour les données' ?" if st.session_state.lang == "FR" else "What does the 'Refresh Data' button do?"):
        st.write("Il force l'application à re-télécharger toutes les informations depuis la base de données. Très utile si vous avez un petit décalage réseau !" if st.session_state.lang == "FR" else "It forces the app to re-download all information from the database. Very useful if you have a slight network delay!")


# --- 10. VERSIONS & MISES À JOUR ---
with st.expander(TRAD[st.session_state.lang]["sec10"], expanded=False):
    st.markdown("""
    **Version actuelle : V4.0 (International & Lounge Room)**
    
    * 🌍 **Bilingue complet** : Support natif Français & Anglais.
    * 🚪 **Salon de Bar (Lounge View)** : Navigation visuelle et graphique à travers l'ensemble des tables actives.
    * 🪑 **Chaises de table interactives** : Les sièges intègrent en temps réel le niveau d'alcoolémie actuel et le statut du leader (couronne).
    * 📱 **Optimisation Tactile** : Blocage total des zooms intempestifs sur les schémas géométriques pour éviter d'entraver le défilement.
    * 🔄 **Bouton Relocalisé** : Le rafraîchissement des données se fait désormais au bas de la page.
    """)

# --- 11. ADMINISTRATION ---
with st.expander(TRAD[st.session_state.lang]["sec11"], expanded=False):
    with st.form("form_effacer"):
        mdp = st.text_input(TRAD[st.session_state.lang]["admin_pwd"], type="password")
        choix_effacer = st.radio(TRAD[st.session_state.lang]["danger_titre"], [
            TRAD[st.session_state.lang]["danger_vider"], 
            TRAD[st.session_state.lang]["danger_suppr_tout"]
        ])
        if st.form_submit_button(TRAD[st.session_state.lang]["btn_executer"]):
            if mdp == "lolo":
                if "Vider" in choix_effacer or "Clear" in choix_effacer:
                    supabase.table("drinks").delete().eq("groupe", groupe_actif).execute()
                    supabase.table("meals").delete().eq("groupe", groupe_actif).execute()
                    st.success(f"Historique de {groupe_actif} effacé.")
                else:
                    supabase.table("drinks").delete().eq("groupe", groupe_actif).execute()
                    supabase.table("meals").delete().eq("groupe", groupe_actif).execute()
                    supabase.table("profils").delete().eq("groupe", groupe_actif).execute()
                    st.session_state.groupe_selectionne = "Haggis et les cafards"
                    st.session_state.salle_bar_active = True
                    st.success(f"Table '{groupe_actif}' supprimée.")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Mot de passe incorrect." if st.session_state.lang == "FR" else "Incorrect password.")

# --- 12. MISE A JOUR & MENTIONS LÉGALES ---
with st.expander(TRAD[st.session_state.lang]["sec12"], expanded=True):
    if st.button(TRAD[st.session_state.lang]["btn_maj"], use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown("""
        <div style='text-align: center; color: #888888; font-size: 11px; margin-top: 15px; line-height: 1.5;'>
            ⚠️ <b>AVERTISSEMENT LÉGAL ET DE SANTÉ / LEGAL WARNING</b><br><br>
            Les résultats fournis par cette application sont basés sur des modélisations mathématiques théoriques (formule de Widmark modifiée) 
            et ne sont donnés qu'à titre purement indicatif. En aucun cas ces données ne peuvent se substituer à un véritable éthylotest homologué. 
            Si tu as bu, tu ne conduis pas !<br><br>
            <i>BAC metrics are purely theoretical. Do not rely on this to drive. If you drink, don't drive!</i>
        </div>
        """, unsafe_allow_html=True)
