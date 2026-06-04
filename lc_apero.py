import streamlit as st
from supabase import create_client, Client
import requests
import pandas as pd
import datetime
import qrcode
from PIL import Image
import io
import plotly.graph_objects as go

# --- CONFIGURATION INITIALE & THÈME ---
st.set_page_config(page_title="Haggis et les cafards 🪳", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #000000 !important; color: #FFFFFF !important; }
    h1, h2, h3, p, span, label, div.stMarkdown { color: #FFFFFF !important; }
    h1, h2 { color: #FF9800 !important; font-weight: bold !important; }
    .stButton>button { background-color: #FF9800 !important; color: #000000 !important; font-weight: bold !important; border: 2px solid #FFFFFF !important; }
    .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stTextInput input { background-color: #1A1A1A !important; color: #FFFFFF !important; border: 1px solid #FF9800 !important; }
    button[data-baseweb="tab"] { color: #FFFFFF !important; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #FF9800 !important; border-bottom-color: #FF9800 !important; }
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
    texte = f"🍽️ *AlcooSuivi* : {pseudo} déclare un repas. 🥪" if est_repas else f"🍹 *AlcooSuivi* : {pseudo} s'enfile un verre ({detail_conso}) 📈"
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

@st.cache_data(ttl=5) # Rafraîchissement régulier
def charger_donnees():
    try:
        boissons = supabase.table("drinks").select("*").order("created_at", desc=False).execute()
        repas = supabase.table("meals").select("*").order("created_at", desc=False).execute()
        return (boissons.data or []), (repas.data or [])
    except: return [], []

boissons_nuageuses, repas_nuage = charger_donnees()

# --- MOTEUR DE CALCUL (Préparation des données) ---
maintenant = pd.Timestamp.now(tz='Europe/Paris')
debut_suivi = maintenant - pd.Timedelta(hours=2)
fin_suivi = maintenant + pd.Timedelta(hours=6)
axe_temps = pd.date_range(start=debut_suivi, end=fin_suivi, freq='5min', tz='Europe/Paris')

def clean_tz(series):
    dt = pd.to_datetime(series)
    if dt.dt.tz is None: dt = dt.dt.tz_localize('UTC')
    return dt.dt.tz_convert('Europe/Paris')

if boissons_nuageuses:
    df_verres = pd.DataFrame(boissons_nuageuses)
    df_verres['created_at'] = clean_tz(df_verres['created_at'])
else:
    df_verres = pd.DataFrame(columns=['pseudo', 'boisson', 'alcool_g', 'created_at'])

if repas_nuage:
    df_repas = pd.DataFrame(repas_nuage)
    df_repas['created_at'] = clean_tz(df_repas['created_at'])
else:
    df_repas = pd.DataFrame(columns=['pseudo', 'created_at'])

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
            
            if diff_heures > 0:
                a_mange = False
                if not repas_perso.empty:
                    repas_avant = repas_perso[(repas_perso['created_at'] <= t_drink) & (repas_perso['created_at'] >= t_drink - pd.Timedelta(hours=2))]
                    if not repas_avant.empty: a_mange = True
                
                t_pic = 1.5 if a_mange else 0.75
                c_max = (verre['alcool_g'] / (poids * coef_diffusion)) * (0.8 if a_mange else 1.0)
                
                if diff_heures <= t_pic: taux_verre = c_max * (diff_heures / t_pic)
                else: taux_verre = c_max - (0.15 * (diff_heures - t_pic))
                
                taux_total_t += max(0.0, taux_verre)
        taux_liste.append(taux_total_t)
    df_graphique[nom] = taux_liste

# ==========================================
# INTERFACE UTILISATEUR
# ==========================================
st.title("🪳 Haggis et les cafards")

# --- 0. ACCÈS ---
col_qr, col_texte = st.columns([1, 4])
with col_qr:
    img = qrcode.make("https://apero-app.streamlit.app") 
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    st.image(buf.getvalue(), width=100)
with col_texte:
    st.markdown("<h3 style='color: orange;'>🔗 Accès à l'application</h3>", unsafe_allow_html=True)
    st.code("https://apero-app.streamlit.app", language="text")
st.divider()

# --- 1. DÉCLARATION (Mis en premier) ---
st.header("🍹 1. Déclarer une consommation")
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
st.header("📍 2. Tableau de bord en direct")

donnees_tableau = []
for nom in profils.keys():
    verres_nom = df_verres[df_verres['pseudo'] == nom] if not df_verres.empty else pd.DataFrame()
    
    if not verres_nom.empty:
        dernier_verre = verres_nom['created_at'].max()
        jours_sans = (maintenant - dernier_verre).days
        taux_actuel = df_graphique[nom].iloc[idx_maintenant]
        taux_max = df_graphique[nom].max()
        
        # Calcul heure de retour à jeun
        if taux_actuel > 0.01:
            heures_restantes = taux_actuel / 0.15
            retour_zero = (maintenant + pd.Timedelta(hours=heures_restantes)).strftime("%H:%M")
        else:
            retour_zero = "À jeun"
    else:
        taux_actuel = 0.0
        taux_max = 0.0
        jours_sans = "∞"
        retour_zero = "À jeun"
        
    donnees_tableau.append({
        "Membre": nom,
        "Taux Actuel (g/L)": f"{taux_actuel:.2f}",
        "Taux Max (g/L)": f"{taux_max:.2f}",
        "Jours sans alcool": jours_sans,
        "Heure de sobriété (0 g/L)": retour_zero
    })

st.dataframe(pd.DataFrame(donnees_tableau), use_container_width=True, hide_index=True)

# --- 3. GRAPHIQUE ---
st.header("📊 3. Courbes d'alcoolémie")
if not df_verres.empty:
    fig = go.Figure()
    couleurs = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22']
    
    for i, nom in enumerate(profils.keys()):
        fig.add_trace(go.Scatter(x=df_graphique.index, y=df_graphique[nom], mode='lines', name=nom, line=dict(width=3, color=couleurs[i % len(couleurs)])))

    fig.add_vline(x=maintenant, line_width=2, line_dash="dash", line_color="orange")
    fig.add_annotation(x=maintenant, y=df_graphique.max().max(), text="Maintenant", showarrow=False, xshift=40, font=dict(color="orange"))

    fig.update_layout(template="plotly_dark", xaxis_title="Heure", yaxis_title="Taux (g/L)", hovermode="x unified", margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aucun graphique à afficher pour le moment.")

# --- 4. HISTORIQUE ---
st.header("📋 4. Historique des entrées")
if not df_verres.empty:
    st.dataframe(df_verres[['pseudo', 'boisson', 'alcool_g', 'created_at']].tail(15), hide_index=True)
else:
    st.write("Aucune consommation enregistrée.")

st.divider()

# --- 5. CONFIGURATION ÉQUIPE (Rétractable) ---
with st.expander("⚙️ Gérer l'équipe (Ajuster poids & Ajouter invités)", expanded=False):
    onglet_Ajusteur, tab_Ajouter = st.tabs(["✏️ Ajuster les poids", "➕ Ajouter un invité"])
    with onglet_Ajusteur:
        cols = st.columns(len(profils))
        for i, (nom, info) in enumerate(profils.items()):
            with cols[i]:
                st.markdown(f"<h5 style='color: orange;'>{nom}</h5>", unsafe_allow_html=True)
                nouveau_poids = st.number_input("Poids (kg)", min_value=40, max_value=150, value=info["poids"], key=f"poids_{nom}")
                st.session_state.profils[nom]["poids"] = nouveau_poids
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
