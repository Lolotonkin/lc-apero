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
st.set_page_config(page_title="Haggis et les cafards 🪳", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Thème général */
    .stApp, .stApp > header { background-color: #000000 !important; color: #FFFFFF !important; }
    h1, h2, h3, p, span, label, div[data-testid="stMarkdownContainer"] { color: #FFFFFF !important; }
    h1, h2 { color: #FF9800 !important; font-weight: bold !important; }
    
    /* Boutons et formulaires (Forçage global) */
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
        border: 2px solid #FFFFFF !important; 
        text-decoration: none !important;
    }
    
    /* Expanders (Zone de danger, Gérer l'équipe) */
    div[data-testid="stExpander"] { background-color: #1A1A1A !important; border: 1px solid #FF9800 !important; }
    div[data-testid="stExpander"] summary { color: #FF9800 !important; font-weight: bold !important; }
    
    /* Métriques du tableau de bord */
    div[data-testid="stMetricValue"] { color: #FF9800 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION SUPABASE ---
SUPABASE_URL = "https://rjexlotreipfjbgpfcnt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqZXhsb3RyZWlwZmpiZ3BmY250Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MDUyOTkyNywiZXhwIjoyMDk2MTA1OTI3fQ.0vMnopwPCMQaOmzCPNcdc4HLqr1d1npoqL3xXNnxGQ8"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"🔑 Erreur Supabase : {e}")
    st.stop()

URL_WEBHOOK_WHATSAPP = st.secrets.get("URL_WEBHOOK_WHATSAPP", "")

def envoyer_alerte_whatsapp(pseudo, detail_conso, est_repas=False):
    if not URL_WEBHOOK_WHATSAPP: return
    texte = f"🍽️ *AlcooSuivi* : {pseudo} déclare un repas. 🥪" if est_repas else f"🍹 *AlcooSuivi* : {pseudo} a pris : {detail_conso} 📈"
    try: requests.post(URL_WEBHOOK_WHATSAPP, json={"message": texte, "pseudo": pseudo})
    except: pass

# --- SESSION & DONNÉES ---
if "profils" not in st.session_state:
    st.session_state.profils = {
        "Lolo'": {"sexe": "Homme", "poids": 75},
        "Poums'": {"sexe": "Homme", "poids": 75},
        "Nico'": {"sexe": "Homme", "poids": 75},
        "Duj'": {"sexe": "Homme", "poids": 75}
    }
profils = st.session_state.profils

def charger_donnees():
    try:
        boissons = supabase.table("drinks").select("*").order("created_at", desc=False).execute()
        repas = supabase.table("meals").select("*").order("created_at", desc=False).execute()
        return (boissons.data or []), (repas.data or [])
    except: return [], []

boissons_nuageuses, repas_nuage = charger_donnees()

# --- MOTEUR DE CALCUL MATHÉMATIQUE ---
maintenant = pd.Timestamp.now(tz='Europe/Paris')

# Fenêtre globale de calcul (12h en arrière pour capter tous les verres influents, et 8h dans le futur)
debut_calcul = maintenant - pd.Timedelta(hours=12)
fin_calcul = maintenant + pd.Timedelta(hours=8)
axe_temps = pd.date_range(start=debut_calcul, end=fin_calcul, freq='5min', tz='Europe/Paris')

def clean_tz(series):
    dt = pd.to_datetime(series)
    if dt.dt.tz is None: dt = dt.dt.tz_localize('UTC')
    return dt.dt.tz_convert('Europe/Paris')

if boissons_nuageuses:
    df_verres = pd.DataFrame(boissons_nuageuses)
    df_verres['created_at'] = clean_tz(df_verres['created_at'])
else:
    df_verres = pd.DataFrame(columns=['id', 'pseudo', 'boisson', 'alcool_g', 'created_at'])

if repas_nuage:
    df_repas = pd.DataFrame(repas_nuage)
    df_repas['created_at'] = clean_tz(df_repas['created_at'])
else:
    df_repas = pd.DataFrame(columns=['id', 'pseudo', 'created_at'])

df_graphique = pd.DataFrame(index=axe_temps)
idx_maintenant = df_graphique.index.get_indexer([maintenant], method='nearest')[0]

for nom, info in profils.items():
    poids = info["poids"]
    coef_diffusion = 0.7 if info["sexe"] == "Homme" else 0.6
    taux_liste = []
    
    verres_perso = df_verres[df_verres['pseudo'] == nom] if not df_verres.empty else pd.DataFrame()
    repas_perso = df_repas[df_repas['pseudo'] == nom] if not df_repas.empty else pd.DataFrame()

    for t in axe_temps:
        taux_total_t = 0.0
        for _, verre in verres_perso.iterrows():
            t_drink = verre['created_at']
            diff_heures = (t - t_drink).total_seconds() / 3600.0
            
            if diff_heures >= 0:
                a_mange = False
                if not repas_perso.empty:
                    repas_valides = repas_perso[(repas_perso['created_at'] >= t_drink - pd.Timedelta(hours=3)) & (repas_perso['created_at'] <= t_drink + pd.Timedelta(hours=1))]
                    if not repas_valides.empty: a_mange = True
                
                # Modèle d'absorption
                t_pic = 1.5 if a_mange else 0.75
                bio_factor = 0.8 if a_mange else 1.0
                c_max_theo = (verre['alcool_g'] / (poids * coef_diffusion)) * bio_factor
                c_pic = c_max_theo - (0.15 * t_pic)
                
                if c_pic > 0:
                    if diff_heures <= t_pic: 
                        taux_verre = c_pic * (diff_heures / t_pic)
                    else: 
                        taux_verre = c_pic - (0.15 * (diff_heures - t_pic))
                    taux_total_t += max(0.0, taux_verre)
                    
        taux_liste.append(taux_total_t)
    df_graphique[nom] = taux_liste

# ==========================================
# INTERFACE UTILISATEUR
# ==========================================
st.title("🪳 Haggis et les cafards")

# --- 0. ACCÈS ---
APP_URL = "https://lc-apero-eqdne2pvte4wak5sawi8kf.streamlit.app"
col_qr, col_texte = st.columns([1, 4])
with col_qr:
    img = qrcode.make(APP_URL) 
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    st.image(buf.getvalue(), width=100)
with col_texte:
    st.markdown("<h3 style='color: orange;'>🔗 Accès à l'application</h3>", unsafe_allow_html=True)
    st.text_input("Lien à copier (cliquez dedans et Ctrl+C) :", value=APP_URL, label_visibility="collapsed")
st.divider()

# --- 1. DÉCLARATION ---
st.header("🍹 1. Déclarer")
choix_type = st.radio("Type d'entrée :", ["Un verre de l'amitié 🍺", "Un repas complet 🍽️"], horizontal=True)
moment_actuel = datetime.datetime.now().isoformat()

if "repas" in choix_type.lower():
    Qui = st.selectbox("Qui a mangé ?", list(profils.keys()))
    if st.button("Enregistrer le repas 💾"):
        supabase.table("meals").insert({"pseudo": Qui, "created_at": moment_actuel}).execute()
        envoyer_alerte_whatsapp(Qui, "", est_repas=True)
        st.success(f"🍽️ Repas enregistré pour {Qui}")
        st.rerun()
else:
    c1, c2, c3 = st.columns(3)
    with c1: Qui = st.selectbox("Qui consomme ?", list(profils.keys()))
    with c2: Volume_ml = st.number_input("Volume (ml)", min_value=10, max_value=1000, value=250, step=10)
    with c3: Degre_Alcool = st.number_input("Degré d'alcool (%)", min_value=0.0, max_value=100.0, value=5.0, step=0.5)

    if st.button("Enregistrer le verre 💾"):
        boisson_label = f"{Volume_ml}ml @ {Degre_Alcool}%"
        alcool_g = float(Volume_ml * (Degre_Alcool / 100) * 0.8)
        supabase.table("drinks").insert({"pseudo": Qui, "boisson": boisson_label, "alcool_g": alcool_g, "created_at": moment_actuel}).execute()
        envoyer_alerte_whatsapp(Qui, boisson_label, est_repas=False)
        st.success(f"🍹 Verre enregistré pour {Qui}")
        st.rerun()
st.divider()

# --- 2. TABLEAU DE BORD INSTANTANÉ ---
st.header("📍 2. Tableau de bord")
cols_dashboard = st.columns(len(profils))
texte_whatsapp = "🪳 *Haggis et les cafards — Point AlcooSuivi* 🍻\n\n"

for i, nom in enumerate(profils.keys()):
    taux_actuel = df_graphique[nom].iloc[idx_maintenant]
    taux_max = df_graphique[nom].max()
    
    donnees_futures = df_graphique[nom].loc[maintenant:]
    
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

    with cols_dashboard[i]:
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

# --- 3. GRAPHIQUE (FENÊTRE H-2 À H+6 VISUELLE) ---
st.header("📊 3. Courbes (Évolution)")
if not df_verres.empty:
    fig = go.Figure()
    couleurs = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22']
    
    for i, nom in enumerate(profils.keys()):
        fig.add_trace(go.Scatter(x=df_graphique.index, y=df_graphique[nom], mode='lines', name=nom, line=dict(width=3, color=couleurs[i % len(couleurs)])))

    fig.add_vline(x=maintenant, line_width=2, line_dash="dash", line_color="orange")
    fig.add_hline(y=0.5, line_width=1, line_dash="dot", line_color="red", annotation_text="0.5 g/L (Conduite)", annotation_position="top right")

    # RESTRICTION DE LA VUE : Forçage absolu de l'axe X pour éviter le dézoom de Plotly
    vue_debut = (maintenant - pd.Timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
    vue_fin = (maintenant + pd.Timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S')

    fig.update_xaxes(
        fixedrange=True, 
        title="Heure", 
        range=[vue_debut, vue_fin], 
        autorange=False
    )
    fig.update_yaxes(fixedrange=True, title="Taux (g/L)", rangemode="tozero")
    
    fig.update_layout(template="plotly_dark", hovermode="x unified", margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.info("Aucun verre n'a encore été enregistré pour modéliser une courbe.")

st.divider()

# --- 4. HISTORIQUE & SUPPRESSION ---
st.header("📋 4. Historique (12 dernières heures)")

df_verres_recent = df_verres[df_verres['created_at'] >= (maintenant - pd.Timedelta(hours=12))].sort_values(by='created_at', ascending=False)
df_repas_recent = df_repas[df_repas['created_at'] >= (maintenant - pd.Timedelta(hours=12))].sort_values(by='created_at', ascending=False)

if not df_verres_recent.empty or not df_repas_recent.empty:
    col_hist1, col_hist2 = st.columns(2)
    
    with col_hist1:
        st.subheader("🍺 Verres récents")
        for _, row in df_verres_recent.iterrows():
            c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
            c1.write(row['created_at'].strftime("%H:%M"))
            c2.write(row['boisson'])
            c3.write(row['pseudo'])
            if c4.button("❌", key=f"del_drink_{row['id']}"):
                supabase.table("drinks").delete().eq("id", row['id']).execute()
                st.rerun()

    with col_hist2:
        st.subheader("🍽️ Repas récents")
        for _, row in df_repas_recent.iterrows():
            c1, c2, c3 = st.columns([2, 4, 1])
            c1.write(row['created_at'].strftime("%H:%M"))
            c2.write(row['pseudo'])
            if c3.button("❌", key=f"del_meal_{row['id']}"):
                supabase.table("meals").delete().eq("id", row['id']).execute()
                st.rerun()
else:
    st.write("Aucune entrée récente.")

st.divider()

# --- 5. CONFIGURATION ÉQUIPE ---
with st.expander("⚙️ Gérer l'équipe (Ajuster poids & Ajouter invités)", expanded=False):
    onglet_Ajusteur, tab_Ajouter = st.tabs(["✏️ Ajuster les poids", "➕ Ajouter un invité"])
    with onglet_Ajusteur:
        with st.form("form_poids"):
            cols = st.columns(len(profils))
            nouveaux_poids = {}
            for i, (nom, info) in enumerate(profils.items()):
                with cols[i]:
                    st.markdown(f"<h5 style='color: orange;'>{nom}</h5>", unsafe_allow_html=True)
                    nouveaux_poids[nom] = st.number_input("Poids (kg)", min_value=40, max_value=150, value=info["poids"], key=f"input_poids_{nom}")
            
            submit_poids = st.form_submit_button("Enregistrer les poids 💾")
            if submit_poids:
                for nom in profils.keys():
                    st.session_state.profils[nom]["poids"] = nouveaux_poids[nom]
                st.success("Poids mis à jour avec succès !")
                st.rerun()
                
    with tab_Ajouter:
        c1, c2, c3 = st.columns(3)
        with c1: nouveau_nom = st.text_input("Nom de l'invité")
        with c2: nouveau_sexe = st.selectbox("Sexe", ["Homme", "Femme"])
        with c3: nouveau_poids_inv = st.number_input("Poids invité (kg)", min_value=40, max_value=150, value=70)
        if st.button("Ajouter à l'équipe"):
            if nouveau_nom and nouveau_nom not in st.session_state.profils:
                st.session_state.profils[nouveau_nom] = {"sexe": nouveau_sexe, "poids": nouveau_poids_inv}
                st.success(f"✔️ {nouveau_nom} ajouté !")
                st.rerun()

# --- 6. ADMINISTRATION ---
with st.expander("🚨 Zone de danger (Remise à zéro)", expanded=False):
    st.write("⚠️ *Cette action effacera toutes les données de la base.*")
    with st.form("form_effacer"):
        mdp = st.text_input("Tapez le mot de passe :", type="password")
        if st.form_submit_button("TOUT EFFACER"):
            if mdp == "lolo":
                supabase.table("drinks").delete().neq("id", 0).execute()
                supabase.table("meals").delete().neq("id", 0).execute()
                st.success("Données effacées.")
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")

st.divider()

# --- 7. MENTIONS LÉGALES & PRÉVENTION ---
st.markdown("""
    <div style='text-align: center; color: #888888; font-size: 11px; margin-top: 30px; padding-bottom: 30px; line-height: 1.5;'>
        ⚠️ <b>AVERTISSEMENT</b> : Cette application est un outil de simulation basé sur des calculs théoriques. 
        Les taux d'alcoolémie affichés sont purement indicatifs et n'ont aucune valeur légale. Ils ne remplacent en aucun cas un éthylotest officiel. 
        Le métabolisme de chacun variant selon de nombreux facteurs (fatigue, stress, médicaments, vitesse de consommation), <b>en cas de doute, ne prenez jamais le volant.</b>
        <br><br>
        <i>« L'abus d'alcool est dangereux pour la santé, à consommer avec modération. »</i>
    </div>
    """, unsafe_allow_html=True)
