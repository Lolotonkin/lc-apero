import streamlit as st
from supabase import create_client, Client
import requests
import pandas as pd
import datetime
import qrcode
from PIL import Image
import io
import plotly.graph_objects as go

# --- CONFIGURATION INITIALE & THÈME HAUT CONTRASTE ---
st.set_page_config(
    page_title="Haggis et les cafards 🪳", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Style CSS forcé
st.markdown("""
    <style>
    .stApp { background-color: #000000 !important; color: #FFFFFF !important; }
    h1, h2, h3, p, span, label { color: #FFFFFF !important; }
    h1, h2 { color: #FF9800 !important; font-weight: bold !important; }
    .stButton>button { background-color: #FF9800 !important; color: #000000 !important; font-weight: bold !important; border: 2px solid #FFFFFF !important; }
    .stNumberInput input, .stSelectbox div[data-baseweb="select"] { background-color: #1A1A1A !important; color: #FFFFFF !important; border: 1px solid #FF9800 !important; }
    button[data-baseweb="tab"] { color: #FFFFFF !important; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #FF9800 !important; border-bottom-color: #FF9800 !important; }
    </style>
    """, unsafe_allow_html=True)

# Connexion Supabase
SUPABASE_URL = "https://rjexlotreipfjbgpfcnt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqZXhsb3RyZWlwZmpiZ3BmY250Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MDUyOTkyNywiZXhwIjoyMDk2MTA1OTI3fQ.0vMnopwPCMQaOmzCPNcdc4HLqr1d1npoqL3xXNnxGQ8"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"🔑 Erreur d'initialisation Supabase : {e}")
    st.stop()

URL_WEBHOOK_WHATSAPP = st.secrets.get("URL_WEBHOOK_WHATSAPP", "")

# --- ENVOI DES ALERTES WHATSAPP ---
def envoyer_alerte_whatsapp(pseudo, detail_conso, est_repas=False):
    if not URL_WEBHOOK_WHATSAPP: return
    if est_repas:
        texte = f"🍽️ *AlcooSuivi* : {pseudo} vient de déclarer un repas ! L'absorption sera ralentie. 🥪"
    else:
        texte = f"🍹 *AlcooSuivi* : {pseudo} vient de s'enfiler un verre ! ({detail_conso}) 📈"
    try:
        requests.post(URL_WEBHOOK_WHATSAPP, json={"message": texte, "pseudo": pseudo})
    except Exception:
        pass

# --- CONFIGURATION ÉQUIPE ---
if "profils" not in st.session_state:
    st.session_state.profils = {
        "Lolo'": {"sexe": "Homme", "poids": 75},
        "Poums'": {"sexe": "Homme", "poids": 75},
        "Nico'": {"sexe": "Homme", "poids": 75},
        "Duj'": {"sexe": "Homme", "poids": 75}
    }
profils = st.session_state.profils

# --- CHARGEMENT CLOUD ---
def charger_donnees_depuis_cloud():
    try:
        boissons = supabase.table("drinks").select("*").order("created_at", desc=False).execute()
        repas = supabase.table("meals").select("*").order("created_at", desc=False).execute()
        return (boissons.data if boissons.data else []), (repas.data if repas.data else [])
    except Exception as e:
        st.error(f"⚠️ Erreur Cloud : {e}")
        return [], []

boissons_nuageuses, repas_nuage = charger_donnees_depuis_cloud()

# ==========================================
# INTERFACE UTILISATEUR
# ==========================================

st.title("🪳 Haggis et les cafards — Suivi d'absorption")

# --- 0. ACCÈS ---
col_qr, col_texte = st.columns([1, 4])
with col_qr:
    img = qrcode.make("https://apero-app.streamlit.app") 
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    st.image(buf.getvalue(), width=100)
with col_texte:
    st.markdown("<h3 style='color: orange;'>🔗 Accès à l'application</h3>", unsafe_allow_html=True)
    st.write("Scannez le QR Code pour rejoindre le dashboard.")
st.divider()

# --- 1. CONFIGURATION ---
st.header("👥 1. Configuration de l'équipe")
onglet_Ajusteur, tab_Ajouter = st.tabs(["✏️ Ajuster les poids", "➕ Ajouter un invité"])

with onglet_Ajusteur:
    cols = st.columns(len(profils))
    for i, (nom, info) in enumerate(profils.items()):
        with cols[i]:
            st.markdown(f"<h4 style='color: orange;'>{nom}</h4>", unsafe_allow_html=True)
            nouveau_poids = st.number_input(f"Poids (kg)", min_value=40, max_value=150, value=info["poids"], key=f"poids_{nom}")
            st.session_state.profils[nom]["poids"] = nouveau_poids

with tab_Ajouter:
    col1, col2, col3 = st.columns(3)
    with col1: nouveau_nom = st.text_input("Nom de l'invité")
    with col2: nouveau_sexe = st.selectbox("Sexe", ["Homme", "Femme"])
    with col3: nouveau_poids_inv = st.number_input("Poids invité (kg)", min_value=40, max_value=150, value=70)
    
    if st.button("Ajouter à l'équipe"):
        if nouveau_nom and nouveau_nom not in st.session_state.profils:
            st.session_state.profils[nouveau_nom] = {"sexe": nouveau_sexe, "poids": nouveau_poids_inv}
            st.success(f"✔️ {nouveau_nom} a rejoint la table !")
            st.rerun()
st.divider()

# --- 2. DÉCLARATION ---
st.header("🍹 2. Déclaration des consommations")
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

# --- 3. GRAPHIQUE & ALCOOLÉMIE (Nouveau Modèle) ---
st.header("📊 3. Évolution des courbes d'alcoolémie")

if boissons_nuageuses:
    def clean_tz(series):
        dt = pd.to_datetime(series)
        if dt.dt.tz is None: dt = dt.dt.tz_localize('UTC')
        return dt.dt.tz_convert('Europe/Paris')

    df_verres = pd.DataFrame(boissons_nuageuses)
    df_verres['created_at'] = clean_tz(df_verres['created_at'])
    df_repas = pd.DataFrame(repas_nuage) if repas_nuage else pd.DataFrame(columns=['pseudo', 'created_at'])
    if not df_repas.empty: df_repas['created_at'] = clean_tz(df_repas['created_at'])

    # Fenêtre : Il y a 2h -> Dans 6h
    maintenant = pd.Timestamp.now(tz='Europe/Paris')
    debut_suivi = maintenant - pd.Timedelta(hours=2)
    fin_suivi = maintenant + pd.Timedelta(hours=6)
    axe_temps = pd.date_range(start=debut_suivi, end=fin_suivi, freq='5min', tz='Europe/Paris')
    
    df_graphique = pd.DataFrame(index=axe_temps)
    
    for nom, info in profils.items():
        poids = info["poids"]
        coef_diffusion = 0.7 if info["sexe"] == "Homme" else 0.6
        taux_liste = []
        
        # Filtre des événements passés de la personne
        verres_perso = df_verres[df_verres['pseudo'] == nom]
        repas_perso = df_repas[df_repas['pseudo'] == nom] if not df_repas.empty else pd.DataFrame()

        for t in axe_temps:
            taux_total_t = 0.0
            
            for _, verre in verres_perso.iterrows():
                t_drink = verre['created_at']
                diff_heures = (t - t_drink).total_seconds() / 3600.0
                
                # Si le verre a été bu avant l'instant t
                if diff_heures > 0:
                    a_mange = False
                    if not repas_perso.empty:
                        # A-t-il mangé dans les 2 heures avant ce verre ?
                        repas_avant = repas_perso[(repas_perso['created_at'] <= t_drink) & 
                                                  (repas_perso['created_at'] >= t_drink - pd.Timedelta(hours=2))]
                        if not repas_avant.empty:
                            a_mange = True
                    
                    # Paramètres d'absorption
                    t_pic = 1.5 if a_mange else 0.75 # 1h30 si mangé, 45min à jeun
                    c_max = (verre['alcool_g'] / (poids * coef_diffusion)) * (0.8 if a_mange else 1.0)
                    
                    if diff_heures <= t_pic:
                        # Phase de montée (absorption)
                        taux_verre = c_max * (diff_heures / t_pic)
                    else:
                        # Phase de descente (élimination à 0.15 g/L/h)
                        taux_verre = c_max - (0.15 * (diff_heures - t_pic))
                    
                    taux_total_t += max(0.0, taux_verre)
            
            taux_liste.append(taux_total_t)
            
        df_graphique[nom] = taux_liste

    # Affichage des métriques actuelles
    st.markdown("<h3 style='color: orange;'>📍 Taux d'alcoolémie actuel</h3>", unsafe_allow_html=True)
    res_cols = st.columns(len(profils))
    
    # On cherche l'index le plus proche de "maintenant" pour afficher le taux
    idx_maintenant = df_graphique.index.get_indexer([maintenant], method='nearest')[0]
    
    for i, nom in enumerate(profils.keys()):
        taux_actuel = df_graphique[nom].iloc[idx_maintenant]
        couleur = "🟢" if taux_actuel < 0.2 else "🟠" if taux_actuel < 0.5 else "🔴"
        with res_cols[i]: st.metric(label=nom, value=f"{taux_actuel:.2f} g/L", delta=couleur)

    # --- NOUVEAU GRAPHIQUE PLOTLY ---
    fig = go.Figure()
    couleurs_lignes = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22']
    
    for i, nom in enumerate(profils.keys()):
        fig.add_trace(go.Scatter(
            x=df_graphique.index, y=df_graphique[nom], 
            mode='lines', name=nom, 
            line=dict(width=3, color=couleurs_lignes[i % len(couleurs_lignes)])
        ))

    # Ligne verticale pour l'heure actuelle
    fig.add_vline(x=maintenant, line_width=2, line_dash="dash", line_color="orange")
    fig.add_annotation(x=maintenant, y=df_graphique.max().max(), text="Maintenant", showarrow=False, xshift=40, font=dict(color="orange"))

    fig.update_layout(
        template="plotly_dark",
        xaxis_title="Heure",
        yaxis_title="Taux (g/L)",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=30, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("<h3 style='color: orange;'>📋 Historique des entrées</h3>", unsafe_allow_html=True)
    st.dataframe(df_verres[['pseudo', 'boisson', 'alcool_g', 'created_at']].tail(10))

else:
    st.info("Aucune donnée disponible.")

# --- 4. ADMINISTRATION (SÉCURISÉE EN BAS) ---
st.write("---")
with st.expander("⚙️ Administration (Zone de danger)"):
    st.write("⚠️ *Cette action effacera toutes les données de la soirée.*")
    with st.form("form_effacer"):
        mdp = st.text_input("Mot de passe :", type="password")
        valide = st.form_submit_button("🚨 TOUT EFFACER")
        if valide:
            if mdp == "lolo":
                supabase.table("drinks").delete().neq("id", 0).execute()
                supabase.table("meals").delete().neq("id", 0).execute()
                st.success("Données effacées.")
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
