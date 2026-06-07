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
    
    /* Bouton d'ouverture du menu latéral (Mobile) bien visible en orange */
    button[kind="header"] {
        color: #FF9800 !important;
    }
    [data-testid="collapsedControl"] {
        color: #FF9800 !important;
        background-color: #1A1A1A !important;
        border: 1px solid #FF9800 !important;
        border-radius: 5px;
    }
    
    /* Boutons et formulaires */
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
    
    /* Champs de saisie */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] { 
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
    
    /* Expanders */
    div[data-testid="stExpander"] { background-color: #1A1A1A !important; border: 1px solid #FF9800 !important; }
    div[data-testid="stExpander"] summary { color: #FF9800 !important; font-weight: bold !important; }
    
    /* Métriques */
    div[data-testid="stMetricValue"] { color: #FF9800 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION SUPABASE ---
SUPABASE_URL = "https://rjexlotreipfjbgpfcnt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqZXhsb3RyZWlwZmpiZ3BmY250Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MDUyOTkyNywiZXhwIjoyMDk2MTA1OTI3fQ.0vMnopwPCMQaOmzCPNcdc4HLqr1d1npoqL3xXNnxGQ8"

@st.cache_resource
def init_supabase():
    try: return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"🔑 Erreur Supabase : {e}")
        st.stop()

supabase = init_supabase()
URL_WEBHOOK_WHATSAPP = st.secrets.get("URL_WEBHOOK_WHATSAPP", "")

# --- GESTION MULTI-GROUPES (SIDEBAR) ---
st.sidebar.header("⚙️ Configuration")
groupe_actif = st.sidebar.text_input("👥 Groupe Actif", value="Haggis et les cafards", help="Tapez un nom existant pour rejoindre un groupe, ou un nouveau pour le créer.")
envoyer_wa = st.sidebar.checkbox("Activer les alertes WhatsApp", value=True)

def envoyer_alerte_whatsapp(pseudo, detail_conso, est_repas=False):
    if not URL_WEBHOOK_WHATSAPP or not envoyer_wa: return
    texte = f"🍽️ *Suivi de soirée ({groupe_actif})* : {pseudo} déclare un repas. 🥪" if est_repas else f"🍹 *Suivi de soirée ({groupe_actif})* : {pseudo} a pris : {detail_conso} 📈"
    try: requests.post(URL_WEBHOOK_WHATSAPP, json={"message": texte, "pseudo": pseudo})
    except: pass

# --- CHARGEMENT OPTIMISÉ AVEC CACHE TTL ---
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

# Vérification du changement de groupe
if "dernier_groupe" not in st.session_state or st.session_state.dernier_groupe != groupe_actif:
    st.session_state.dernier_groupe = groupe_actif
    st.cache_data.clear()

profils = charger_profils(groupe_actif)

if not profils:
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

# --- MOTEUR DE CALCUL MATHÉMATIQUE ULTRA-OPTIMISÉ ---
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

df_repas = pd.DataFrame(repas_nuage) if repas_nuage else pd.DataFrame(columns=['id', 'pseudo', 'created_at', 'groupe'])
if not df_repas.empty: df_repas['created_at'] = clean_tz(df_repas['created_at'])

df_graphique = pd.DataFrame(index=axe_temps)
idx_maintenant = df_graphique.index.get_indexer([maintenant_arrondi], method='nearest')[0]

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
            if not repas_perso.empty:
                repas_valides = repas_perso[(repas_perso['created_at'] >= t_drink - pd.Timedelta(hours=3)) & (repas_perso['created_at'] <= t_drink + pd.Timedelta(hours=1))]
                if not repas_valides.empty: a_mange = True
                
            t_pic = 1.0 if a_mange else 0.5 
            bio_factor = 0.8 if a_mange else 1.0
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

# ==========================================
# INTERFACE UTILISATEUR
# ==========================================
st.title("🍹 Suivi de soirée")
st.subheader(f"🌐 Groupe : {groupe_actif}")

st.markdown("<p style='text-align: right;'><a href='#faq' style='color: #FF9800; text-decoration: none;'>❓ Une question ? Consulter la FAQ en bas</a></p>", unsafe_allow_html=True)

# --- 0. ACCÈS ---
APP_URL = "https://lc-apero-eqdne2pvte4wak5sawi8kf.streamlit.app"
col_qr, col_texte = st.columns([1, 4])
with col_qr:
    img = qrcode.make(APP_URL) 
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    st.image(buf.getvalue(), width=100)
with col_texte:
    st.markdown("<h3 style='color: orange; margin-top: 0px;'>🔗 Accès à l'application</h3>", unsafe_allow_html=True)
    st.text_input("Lien à copier (cliquez dedans et Ctrl+C) :", value=APP_URL, label_visibility="collapsed")
st.divider()

# --- 1. DÉCLARATION ---
st.header("🍹 1. Déclarer")
choix_type = st.radio("Type d'entrée :", ["Un verre de l'amitié 🍺", "Un repas complet 🍽️"], horizontal=True)
moment_actuel = datetime.datetime.now().isoformat()

if "repas" in choix_type.lower():
    Qui = st.selectbox("Qui a mangé ?", list(profils.keys()))
    if st.button("Enregistrer le repas 💾"):
        supabase.table("meals").insert({"pseudo": Qui, "created_at": moment_actuel, "groupe": groupe_actif}).execute()
        st.cache_data.clear() 
        envoyer_alerte_whatsapp(Qui, "", est_repas=True)
        st.success(f"🍽️ Repas enregistré pour {Qui}")
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
        envoyer_alerte_whatsapp(Qui, boisson_label, est_repas=False)
        st.success(f"🍹 Verre enregistré pour {Qui}")
        st.rerun()
st.divider()

# --- 2. TABLEAU DE BORD INSTANTANÉ ---
st.header("📍 2. Tableau de bord")
if not profils:
    st.warning("Aucun profil disponible pour ce groupe.")
else:
    cols_dashboard = st.columns(len(profils))
    texte_whatsapp = f"🪳 *Point AlcooSuivi — Groupe {groupe_actif}* 🍻\n\n"

    for i, nom in enumerate(profils.keys()):
        taux_actuel = df_graphique[nom].iloc[idx_maintenant]
        taux_max = df_graphique[nom].max()
        donnees_futures = df_graphique[nom].loc[maintenant_arrondi:]
        
        if taux_actuel > 0.01 or donnees_futures.max() > 0.01:
            temps_sobre = donnees_futures[donnees_futures <= 0.01]
            retour_zero = temps_sobre.index[0].strftime("%H:%M") if not temps_sobre.empty else "Demain"
        else:
            retour_zero = "À jeun"
            
        if donnees_futures.max() < 0.5:
            heure_conduite = "Maintenant ✅"
        else:
            heure_pic = donnees_futures.idxmax()
            donnees_apres_pic = donnees_futures.loc[heure_pic:]
            temps_conduite = donnees_apres_pic[donnees_apres_pic < 0.5]
            heure_conduite = temps_conduite.index[0].strftime("%H:%M") if not temps_conduite.empty else "Trop tard 🛑"

        with cols_dashboard[i % len(cols_dashboard)]:
            st.markdown(f"#### {nom}")
            st.metric(label="Taux Actuel", value=f"{taux_actuel:.2f} g/L")
            st.markdown(f"**Max projeté :** {taux_max:.2f} g/L")
            st.markdown(f"**🚗 Conduite (<0.5) :** {heure_conduite}")
            st.markdown(f"**💧 À jeun (0.0) :** {retour_zero}")
            
        texte_whatsapp += f"• *{nom}* : {taux_actuel:.2f}g/L (Max: {taux_max:.2f}) — 🚗 Conduite: {heure_conduite}\n"

    texte_wa_encode = urllib.parse.quote(texte_whatsapp)
    lien_partage_whatsapp = f"https://api.whatsapp.com/send?text={texte_wa_encode}"
    st.markdown("<br>", unsafe_allow_html=True)
    st.link_button("📲 Partager le bilan sur WhatsApp", lien_partage_whatsapp)
st.divider()

# --- 3. GRAPHIQUE ---
st.header("📊 3. Courbes (Évolution)")
choix_vue = st.radio("Sélectionnez la période à afficher :", ["Standard (H-2 à H+6)", "Demi-journée (H-12 à H+12)", "Week-end (H-24 à H+12)"], horizontal=True)

h_avant, h_apres = (2, 6) if "Standard" in choix_vue else ((12, 12) if "Demi-journée" in choix_vue else (24, 12))

if not df_verres.empty and profils:
    fig = go.Figure()
    couleurs = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22', '#1abc9c', '#34495e', '#ff9ff3', '#00d2d3']
    for i, nom in enumerate(profils.keys()):
        fig.add_trace(go.Scatter(x=df_graphique.index, y=df_graphique[nom], mode='lines', name=nom, line=dict(width=3, color=couleurs[i % len(couleurs)])))

    fig.add_vline(x=maintenant_arrondi, line_width=2, line_dash="dash", line_color="orange")
    fig.add_hline(y=0.5, line_width=1, line_dash="dot", line_color="red", annotation_text="0.5 g/L (Conduite)", annotation_position="top right")

    vue_debut = (maintenant_arrondi - pd.Timedelta(hours=h_avant)).strftime('%Y-%m-%d %H:%M:%S')
    vue_fin = (maintenant_arrondi + pd.Timedelta(hours=h_apres)).strftime('%Y-%m-%d %H:%M:%S')

    fig.update_xaxes(fixedrange=True, title="Heure", range=[vue_debut, vue_fin], autorange=False)
    fig.update_yaxes(fixedrange=True, title="Taux (g/L)", rangemode="tozero")
    fig.update_layout(template="plotly_dark", hovermode="x unified", margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.info("Aucun verre enregistré.")
st.divider()

# --- 4. HISTORIQUE COMPACT ---
st.header("📋 4. Historique")
with st.expander("👀 Afficher / Masquer l'historique récent (24h)", expanded=False):
    df_verres_recent = df_verres[df_verres['created_at'] >= (maintenant_arrondi - pd.Timedelta(hours=24))].copy()
    if not df_verres_recent.empty:
        df_verres_recent['type'], df_verres_recent['details'] = '🍹', df_verres_recent['boisson']
    else:
        df_verres_recent = pd.DataFrame(columns=['id', 'pseudo', 'created_at', 'type', 'details'])

    df_repas_recent = df_repas[df_repas['created_at'] >= (maintenant_arrondi - pd.Timedelta(hours=24))].copy()
    if not df_repas_recent.empty:
        df_repas_recent['type'], df_repas_recent['details'] = '🍽️', 'Repas'
    else:
        df_repas_recent = pd.DataFrame(columns=['id', 'pseudo', 'created_at', 'type', 'details'])

    df_timeline = pd.concat([df_verres_recent[['id', 'pseudo', 'created_at', 'type', 'details']], df_repas_recent[['id', 'pseudo', 'created_at', 'type', 'details']]])

    if not df_timeline.empty:
        df_timeline = df_timeline.sort_values(by='created_at', ascending=False)
        for _, row in df_timeline.iterrows():
            c1, c2, c3, c4 = st.columns([1, 2, 4, 1])
            c1.markdown(f"**{row['type']}**")
            c2.write(row['created_at'].strftime("%H:%M"))
            c3.write(f"**{row['pseudo']}** : {row['details']}")
            if c4.button("❌", key=f"del_{row['type']}_{row['id']}"):
                supabase.table("drinks" if row['type'] == '🍹' else "meals").delete().eq("id", row['id']).execute()
                st.cache_data.clear()
                st.rerun()
    else:
        st.write("Aucune entrée récente.")
st.divider()

# --- 5. CONFIGURATION ÉQUIPE ---
with st.expander("⚙️ Gérer l'équipe (Poids, Ajouter, Supprimer)", expanded=False):
    onglet_Ajusteur, tab_Ajouter, tab_Supprimer = st.tabs(["✏️ Ajuster les poids", "➕ Ajouter un invité", "🗑️ Supprimer un profil"])
    
    with onglet_Ajusteur:
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
        if len(profils) >= 10: st.warning("🛑 Limite de 10 personnes atteinte pour ce groupe.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1: nouveau_nom = st.text_input("Nom de l'invité")
            with c2: nouveau_sexe = st.selectbox("Sexe", ["Homme", "Femme"])
            with c3: nouveau_poids_inv = st.number_input("Poids (kg)", 40, 150, 70)
            if st.button("Ajouter"):
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
with st.expander("🚨 Zone de danger (Remise à zéro)", expanded=False):
    with st.form("form_effacer"):
        mdp = st.text_input("Mot de passe :", type="password")
        choix_effacer = st.radio("Effacer :", ["Verres/Repas du groupe uniquement", "TOUT (Effacer aussi les profils du groupe)"])
        if st.form_submit_button("EXÉCUTER"):
            if mdp == "lolo":
                supabase.table("drinks").delete().eq("groupe", groupe_actif).execute()
                supabase.table("meals").delete().eq("groupe", groupe_actif).execute()
                if "TOUT" in choix_effacer:
                    supabase.table("profils").delete().eq("groupe", groupe_actif).execute()
                st.cache_data.clear()
                st.success("Réinitialisation réussie.")
                st.rerun()
st.divider()

# --- 7. FAQ ---
st.markdown("<div id='faq'></div>", unsafe_allow_html=True)
with st.expander("❓ FAQ - Guide d'utilisation", expanded=True):
    st.markdown("""
    ### Questions fréquentes
    * **Comment fonctionne le système de groupes ?**
      Changez le texte dans la section **"Groupe Actif"** dans la barre latérale. Taper un nom inédit crée instantanément un nouvel espace indépendant. Partagez ensuite ce même nom avec vos invités.
    * **Pourquoi déclarer un repas ?**
      La présence de nourriture dans l'estomac retarde la diffusion de l'alcool. Déclarer un repas permet à l'algorithme d'allonger le temps pour atteindre le pic d'alcoolémie, lissant ainsi les courbes pour mieux refléter la réalité.
    * **Quelle est la différence entre "Taux Actuel" et "Max projeté" ?**
      Le taux actuel correspond à l'estimation mathématique exacte à l'instant T. Le taux maximum projeté tient compte de la phase d'absorption des derniers verres enregistrés qui n'ont pas encore fini de faire monter votre alcoolémie.
    """)

# --- 8. MENTIONS LÉGALES ---
st.markdown("""
    <div style='text-align: center; color: #888888; font-size: 11px; margin-top: 30px; padding-bottom: 30px;'>
        ⚠️ <b>AVERTISSEMENT</b> : Simulation théorique purement indicative sans valeur légale. Ne remplace pas un éthylotest officiel. En cas de doute, ne prenez pas le volant.
    </div>
    """, unsafe_allow_html=True)
