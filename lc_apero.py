import streamlit as st
from supabase import create_client, Client
import requests
import pandas as pd
import datetime
import qrcode
import io
import plotly.graph_objects as go
import urllib.parse

# --- CONFIGURATION INITIALE & THÈME ---
st.set_page_config(page_title="Suivi de soirée 🍹", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Thème général */
    .stApp, .stApp > header { background-color: #000000 !important; color: #FFFFFF !important; }
    h1, h2, h3, p, span, label, div[data-testid="stMarkdownContainer"] { color: #FFFFFF !important; }
    h1, h2 { color: #FF9800 !important; font-weight: bold !important; }
    
    /* Boutons généraux */
    div[data-testid="stButton"] > button, 
    div[data-testid="stFormSubmitButton"] > button { 
        background-color: #FF9800 !important; 
        color: #000000 !important; 
        font-weight: bold !important; 
        border: 2px solid #FFFFFF !important; 
    }
    div[data-testid="stButton"] > button:hover, 
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #e68a00 !important;
        border-color: #FF9800 !important;
    }
    
    /* Champs de saisie & Selectbox */
    .stTextInput input, .stNumberInput input, div[data-baseweb="select"] { 
        background-color: #1A1A1A !important; 
        color: #FFFFFF !important; 
        border: 1px solid #FF9800 !important; 
    }
    
    /* Lien WhatsApp & Accès */
    div[data-testid="stLinkButton"] > a { 
        background-color: #FF9800 !important; 
        color: #000000 !important; 
        font-weight: bold !important; 
        text-decoration: none !important;
        border: 2px solid #FFFFFF !important;
    }
    
    /* Expanders & Métriques */
    div[data-testid="stExpander"] { background-color: #1A1A1A !important; border: 1px solid #FF9800 !important; }
    div[data-testid="stExpander"] summary { color: #FF9800 !important; font-weight: bold !important; }
    div[data-testid="stMetricValue"] { color: #FF9800 !important; }

    /* Timeline CSS */
    .timeline-row { 
        border-left: 3px solid #FF9800; 
        padding-left: 15px; 
        margin-bottom: 5px; 
    }
    .time-badge { 
        color: #FF9800; 
        font-weight: bold; 
        font-size: 1.2em; 
    }
    .pseudo-text { 
        color: #FFFFFF; 
        font-weight: bold; 
        font-size: 1.1em;
    }
    .details-text {
        color: #CCCCCC;
        font-size: 0.9em;
    }
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

# --- FONCTION DE RÉCUPÉRATION DES TABLES (GROUPES) ---
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
# INTERFACE UTILISATEUR PRINCIPALE
# ==========================================
st.title("🍹 Suivi de soirée")
st.markdown("<p style='text-align: right;'><a href='#faq' style='color: #FF9800; text-decoration: none;'>❓ Une question ? Consulter la FAQ en bas</a></p>", unsafe_allow_html=True)

# --- GESTION DU CHOIX DE LA TABLE ---
st.markdown("### 🌐 Table active")
tables_existantes = obtenir_toutes_les_tables()
if "Haggis et les cafards" not in tables_existantes:
    tables_existantes.insert(0, "Haggis et les cafards")

if "groupe_selectionne" not in st.session_state:
    st.session_state.groupe_selectionne = "Haggis et les cafards"

if st.session_state.groupe_selectionne not in tables_existantes:
    tables_existantes.append(st.session_state.groupe_selectionne)

options_menu = tables_existantes + ["➕ Créer une nouvelle table..."]
index_defaut = options_menu.index(st.session_state.groupe_selectionne)

choix_table = st.selectbox("Sélectionnez votre table :", options_menu, index=index_defaut, label_visibility="collapsed")

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

with st.expander("⚙️ Paramètres de l'application", expanded=False):
    envoyer_wa = st.checkbox("Activer les alertes WhatsApp", value=True)

def envoyer_alerte_whatsapp(pseudo, detail_conso, type_event="Verre"):
    if not URL_WEBHOOK_WHATSAPP or not envoyer_wa: return
    if type_event == "Repas":
        texte = f"🍽️ *Suivi de soirée ({groupe_actif})* : {pseudo} déclare un repas complet. 🥪"
    elif type_event == "Grignotage":
        texte = f"🥨 *Suivi de soirée ({groupe_actif})* : {pseudo} grignote à l'apéro. 🥜"
    else:
        texte = f"🍹 *Suivi de soirée ({groupe_actif})* : {pseudo} a pris : {detail_conso} 📈"
    try: requests.post(URL_WEBHOOK_WHATSAPP, json={"message": texte, "pseudo": pseudo})
    except: pass

st.divider()

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data(ttl=2)
def charger_profils(groupe):
    try:
        rep = supabase.table("profils").select("*").eq("groupe", groupe).execute()
        return {p['pseudo']: {"sexe": p['sexe'], "poids": p['poids'], "id": p['id']} for p in rep.data} if rep.data else {}
    except: return {}

@st.cache_data(ttl=2)
def charger_donnees(groupe):
    try:
        boissons = supabase.table("drinks").select("*").eq("groupe", groupe).order("created_at", desc=False).execute()
        repas = supabase.table("meals").select("*").eq("groupe", groupe).order("created_at", desc=False).execute()
        return (boissons.data or []), (repas.data or [])
    except: return [], []

profils = charger_profils(groupe_actif)

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

boissons_nuageuses, repas_nuage = charger_donnees(groupe_actif)

# --- MOTEUR DE CALCUL MATHÉMATIQUE ---
maintenant = pd.Timestamp.now(tz='Europe/Paris')
maintenant_arrondi = maintenant.floor('5min')
debut_calcul = maintenant_arrondi - pd.Timedelta(hours=24)
fin_calcul = maintenant_arrondi + pd.Timedelta(hours=12)
axe_temps = pd.date_range(start=debut_calcul, end=fin_calcul, freq='5min', tz='Europe/Paris')

PENTE_ELIMINATION_5MIN = 0.15 * (5 / 60)

def clean_tz(series):
    dt = pd.to_datetime(series)
    if dt.dt.tz is None: dt = dt.dt.tz_localize('UTC')
    return dt.dt.tz_convert('Europe/Paris')

df_verres = pd.DataFrame(boissons_nuageuses) if boissons_nuageuses else pd.DataFrame(columns=['id', 'pseudo', 'boisson', 'alcool_g', 'created_at', 'groupe'])
if not df_verres.empty: df_verres['created_at'] = clean_tz(df_verres['created_at'])

df_repas = pd.DataFrame(repas_nuage) if repas_nuage else pd.DataFrame(columns=['id', 'pseudo', 'created_at', 'groupe', 'type'])
if not df_repas.empty: 
    df_repas['created_at'] = clean_tz(df_repas['created_at'])
    if 'type' not in df_repas.columns:
        df_repas['type'] = 'Repas'

df_graphique = pd.DataFrame(index=axe_temps)
idx_maintenant = df_graphique.index.get_indexer([maintenant_arrondi], method='nearest')[0]

# Dictionnaire pour stocker les statistiques globales
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
                
            if a_mange:
                t_pic = 1.0 
                bio_factor = 0.8 
            elif a_grignote:
                t_pic = 0.75 
                bio_factor = 0.9 
            else:
                t_pic = 0.5 
                bio_factor = 1.0 
                
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
        if apport_5min == 0 and taux_courant > 0:
            taux_courant -= PENTE_ELIMINATION_5MIN
        taux_courant = max(0.0, taux_courant)
        taux_dict[t] = taux_courant
        
    for t in axe_temps:
        taux_liste.append(taux_dict.get(t, 0.0))
        
    df_graphique[nom] = taux_liste
    
    # EXTRACTION DES STATISTIQUES GLOBALES
    max_historique = max(taux_dict.values()) if taux_dict else 0.0
    
    if not verres_perso.empty:
        dernier_verre = verres_perso['created_at'].max()
        delta = maintenant - dernier_verre
        if delta.days == 0: texte_jours = "Aujourd'hui 🍻"
        elif delta.days == 1: texte_jours = "1 jour 💧"
        else: texte_jours = f"{delta.days} jours 💧"
    else:
        texte_jours = "Jamais bu 😇"
        
    stats_joueurs[nom] = {
        "max_ever": max_historique,
        "texte_jours": texte_jours,
        "total_verres": len(verres_perso)
    }

# --- 0. ACCÈS ---
APP_URL = "https://lc-apero-eqdne2pvte4wak5sawi8kf.streamlit.app"
col_qr, col_texte = st.columns([1, 4])
with col_qr:
    img = qrcode.make(APP_URL) 
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    st.image(buf.getvalue(), width=100)
with col_texte:
    st.markdown("<h3 style='color: orange; margin-top: 0px;'>🔗 Partager l'application</h3>", unsafe_allow_html=True)
    st.text_input("Lien à copier :", value=APP_URL, label_visibility="collapsed")
st.divider()

# --- 1. DÉCLARATION ---
st.header("🍹 1. Déclarer")
if not profils:
    st.error("⚠️ Cette table est vide. Descendez à la section '5. Gérer l'équipe' pour ajouter des invités !")
else:
    choix_type = st.radio("Type d'entrée :", ["Un verre de l'amitié 🍺", "Un repas complet 🍽️", "Grignotage (Apéro) 🥨"], horizontal=True)
    
    oubli = st.checkbox("🕰️ J'ai oublié de le noter sur le moment (modifier l'heure)")
    maintenant_local = pd.Timestamp.now(tz='Europe/Paris')
    
    if oubli:
        heure_perso = st.time_input("Heure de la consommation :", value=maintenant_local.time())
        date_conso = maintenant_local.date()
        
        if heure_perso > maintenant_local.time() and maintenant_local.hour < 12:
            date_conso = date_conso - datetime.timedelta(days=1)
            
        dt_combine = datetime.datetime.combine(date_conso, heure_perso)
        moment_actuel = pd.Timestamp(dt_combine).tz_localize('Europe/Paris').isoformat()
        affichage_heure = heure_perso.strftime("%H:%M")
    else:
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
        with c1: Qui = st.selectbox("Qui consomme ?", list(profils.keys()))
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
st.divider()

# --- 2. TABLEAU DE BORD INSTANTANÉ ---
st.header("📍 2. Tableau de bord")
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
        else:
            retour_zero = "À jeun"
            
        if donnees_futures.empty or taux_max_futur < 0.5:
            heure_conduite = "Maintenant ✅"
        else:
            heure_pic = donnees_futures.idxmax()
            donnees_apres_pic = donnees_futures.loc[heure_pic:]
            temps_conduite = donnees_apres_pic[donnees_apres_pic < 0.5]
            heure_conduite = temps_conduite.index[0].strftime("%H:%M") if not temps_conduite.empty else "Trop tard 🛑"

        with cols_dashboard[i % len(cols_dashboard)]:
            st.markdown(f"#### {nom}")
            st.metric(label="Taux Actuel", value=f"{taux_actuel:.2f} g/L")
            st.markdown(f"**Max projeté :** {taux_max_futur:.2f} g/L")
            st.markdown(f"**🚗 Conduite (<0.5) :** {heure_conduite}")
            st.markdown(f"**💧 À jeun (0.0) :** {retour_zero}")
            
        texte_whatsapp += f"• *{nom}* : {taux_actuel:.2f}g/L (Max: {taux_max_futur:.2f})\n"

    texte_wa_encode = urllib.parse.quote(texte_whatsapp)
    lien_partage_whatsapp = f"https://api.whatsapp.com/send?text={texte_wa_encode}"
    st.markdown("<br>", unsafe_allow_html=True)
    st.link_button("📲 Partager le bilan sur WhatsApp", lien_partage_whatsapp)
    
    # --- NOUVEAU : HALL OF FAME ---
    with st.expander("🏆 Hall of Fame (Records & Statistiques globales)", expanded=False):
        st.markdown("<h4 style='color: orange; margin-bottom: 20px;'>Médailles & Sobriété</h4>", unsafe_allow_html=True)
        cols_stats = st.columns(len(profils))
        for i, (nom, stats) in enumerate(stats_joueurs.items()):
            with cols_stats[i % len(cols_stats)]:
                st.markdown(f"**{nom}**")
                st.markdown(f"**Record absolu :** {stats['max_ever']:.2f} g/L 🥇")
                st.markdown(f"**Dernier verre :** {stats['texte_jours']}")
                st.markdown(f"**Total bu :** {stats['total_verres']} verres")
st.divider()

# --- 3. GRAPHIQUE ---
st.header("📊 3. Courbes (Évolution)")
if not df_verres.empty and profils:
    choix_vue = st.radio("Sélectionnez la période à afficher :", ["Standard (H-2 à H+6)", "Demi-journée (H-12 à H+12)", "Week-end (H-24 à H+12)"], horizontal=True)
    h_avant, h_apres = (2, 6) if "Standard" in choix_vue else ((12, 12) if "Demi-journée" in choix_vue else (24, 12))

    fig = go.Figure()
    couleurs = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22', '#1abc9c']
    for i, nom in enumerate(profils.keys()):
        if nom in df_graphique.columns:
            fig.add_trace(go.Scatter(x=df_graphique.index, y=df_graphique[nom], mode='lines', name=nom, line=dict(width=3, color=couleurs[i % len(couleurs)])))

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
st.divider()

# --- 4. HISTORIQUE - VUE TIMELINE ---
st.header("📋 4. Historique de la soirée")

with st.expander("👀 Afficher la Timeline (24h)", expanded=True):
    df_verres_recent = df_verres[df_verres['created_at'] >= (maintenant_arrondi - pd.Timedelta(hours=24))].copy() if not df_verres.empty else pd.DataFrame()
    if not df_verres_recent.empty: 
        df_verres_recent['icone'] = '🍹'
        df_verres_recent['details'] = df_verres_recent['boisson']
    else: 
        df_verres_recent = pd.DataFrame(columns=['id', 'pseudo', 'created_at', 'icone', 'details'])

    df_repas_recent = df_repas[df_repas['created_at'] >= (maintenant_arrondi - pd.Timedelta(hours=24))].copy() if not df_repas.empty else pd.DataFrame()
    if not df_repas_recent.empty: 
        df_repas_recent['icone'] = df_repas_recent['type'].apply(lambda x: '🥨' if x == 'Grignotage' else '🍽️')
        df_repas_recent['details'] = df_repas_recent['type'].apply(lambda x: 'A grignoté (Apéro)' if x == 'Grignotage' else 'A pris un repas complet')
    else: 
        df_repas_recent = pd.DataFrame(columns=['id', 'pseudo', 'created_at', 'icone', 'details'])

    df_timeline = pd.concat([df_verres_recent[['id', 'pseudo', 'created_at', 'icone', 'details']], df_repas_recent[['id', 'pseudo', 'created_at', 'icone', 'details']]])

    if not df_timeline.empty:
        df_timeline = df_timeline.sort_values(by='created_at', ascending=False)
        
        for _, row in df_timeline.iterrows():
            heure = row['created_at'].strftime('%H:%M')
            icone = row['icone']
            pseudo = row['pseudo']
            details = row['details']
            
            with st.container():
                c_time, c_content, c_suppr = st.columns([1.5, 5, 1])
                
                with c_time:
                    st.markdown(f"<div style='margin-top: 10px; text-align: right;'><span class='time-badge'>{heure}</span></div>", unsafe_allow_html=True)
                    
                with c_content:
                    st.markdown(f"""
                    <div class='timeline-row'>
                        <span style='font-size: 1.2em;'>{icone}</span> <span class='pseudo-text'>{pseudo}</span><br>
                        <span class='details-text'>{details}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with c_suppr:
                    if st.button("❌", key=f"del_{icone}_{row['id']}", use_container_width=True):
                        table_del = "drinks" if icone == '🍹' else "meals"
                        supabase.table(table_del).delete().eq("id", row['id']).execute()
                        st.cache_data.clear()
                        st.rerun()
    else:
        st.info("La soirée n'a pas encore commencé... ou tout le monde est à l'eau ! 🚰")
st.divider()

# --- 5. CONFIGURATION ÉQUIPE ---
st.header("⚙️ 5. Gérer l'équipe")
with st.expander(f"Modifier les participants de '{groupe_actif}'", expanded=not profils):
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
st.divider()

# --- 6. ADMINISTRATION ---
st.header("🚨 6. Zone de danger")
with st.expander("Gérer la base de données", expanded=False):
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
st.divider()

# --- 7. FAQ ---
st.markdown("<div id='faq'></div>", unsafe_allow_html=True)
with st.expander("❓ FAQ - Guide d'utilisation", expanded=False):
    st.markdown("""
    ### Foire Aux Questions
    
    * **Comment fonctionne le système de tables ?**
      Utilisez le menu déroulant tout en haut pour naviguer entre les soirées ou en créer une nouvelle en choisissant `➕ Créer une nouvelle table...`. Chaque table a son propre historique et ses propres invités.
      
    * **Peut-on utiliser l'application à plusieurs sur des téléphones différents ?**
      Absolument ! L'application est connectée à une base de données en temps réel. Scannez le QR code ou partagez le lien : dès qu'une personne ajoute un verre sur son téléphone, l'historique de la table est mis à jour pour tout le monde.
      
    * **Faut-il enregistrer le verre au début ou à la fin de la consommation ?**
      Toujours au **début** (lors de votre première gorgée). L'algorithme calcule l'absorption et la montée du taux de manière progressive *après* l'heure indiquée. Si vous l'ajoutez à la fin, votre courbe sera artificiellement décalée dans le temps.
      
    * **Que se passe-t-il si j'utilise l'option "J'ai oublié" pour ajouter un verre dans le passé ?**
      L'application insère le verre à l'heure exacte demandée. L'historique (Timeline) se met à jour chronologiquement en plaçant le verre à sa juste place dans le passé, et l'algorithme recalcule instantanément toute l'évolution des taux depuis cette heure-là.
      
    * **Comment l'application gère-t-elle le passage de minuit pour les verres oubliés ?**
      Si vous ajoutez un verre à 01h30 du matin et indiquez "23h45" dans l'heure oubliée, le système comprend automatiquement (si vous êtes le matin avant midi) qu'il s'agit de 23h45 de la veille au soir, évitant ainsi de placer le verre dans le futur.
      
    * **Pourquoi l'application me demande-t-elle de déclarer un repas ou un grignotage ?**
      Manger ne fait pas baisser l'alcoolémie, mais cela ralentit considérablement l'absorption de l'alcool dans le sang. L'algorithme lissera la courbe en conséquence. Un repas complet repousse le pic d'absorption sur une période d'environ 3 heures, tandis qu'un grignotage d'apéro le repousse sur environ 1 heure et demie.
      
    * **Comment l'application calcule-t-elle mon taux ?**
      Elle se base sur une version adaptée de la formule scientifique de Widmark. Elle prend en compte la quantité d'alcool pur ingérée, votre poids, et un coefficient de diffusion lié à votre sexe biologique. Le taux d'élimination est fixé à une moyenne standard de 0,15 g/L par heure.
      
    * **Que se passe-t-il si je modifie le poids de quelqu'un en cours de soirée ?**
      L'algorithme recalculera instantanément l'intégralité de sa courbe depuis son tout premier verre pour s'adapter rétroactivement à sa nouvelle donnée corporelle.
      
    * **Oups, je me suis trompé de verre ou de personne. Que faire ?**
      Descendez à la section "4. Historique de la soirée". Vous y verrez toutes les consommations des dernières 24h. Cliquez simplement sur la croix rouge (❌) à côté de l'entrée concernée pour l'effacer définitivement, le graphique se mettra à jour.
      
    * **Qu'est-ce que le "Max projeté" dans le tableau de bord ?**
      C'est le pic d'alcoolémie à venir, c'est-à-dire le taux le plus élevé que vous atteindrez dans le futur, sans tenir compte des pics passés. Si vous êtes déjà en phase d'élimination (taux qui descend), votre "Max projeté" sera simplement votre taux actuel.
    """)

# --- 8. VERSIONS & MISES À JOUR ---
with st.expander("🏷️ Version & Notes de mise à jour", expanded=False):
    st.markdown("""
    **Version actuelle : V2.3 (Mise à jour majeure des Stats)**
    
    **Quoi de neuf dans cette mise à jour (V2.3) ?**
    * 🏆 **Hall of Fame :** Ajout d'un encart "Statistiques globales" (Record du taux le plus haut jamais atteint, nombre de jours sans boire, total des verres ingérés).
    * 🕰️ **Saisie rétroactive intelligente :** Ajout de la case à cocher "J'ai oublié" permettant de forcer l'heure d'un verre ou d'un repas.
    * 📋 **Reclassement automatique dans la Timeline :** Les consommations passées oubliées s'insèrent au bon endroit chronologique dans l'historique et recalculent proprement la courbe.
    * 🔮 **Correction du Max Projeté :** L'indicateur principal du tableau de bord ne prend désormais en compte que l'avenir.
    """)

# --- 9. MENTIONS LÉGALES ---
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
