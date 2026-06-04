import streamlit as st
from supabase import create_client, Client
import requests
import pandas as pd
import datetime

# --- CONFIGURATION INITIALE & THÈME HAUT CONTRASTE ---
st.set_page_config(
    page_title="Haggis et les cafards 🪳", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Style CSS forcé pour un contraste maximal (Blanc/Orange sur Noir)
st.markdown("""
    <style>
    /* Fond de l'application et texte principal */
    .stApp {
        background-color: #000000 !important;
        color: #FFFFFF !important;
    }
    
    /* Titres principaux */
    h1, h2, h3, p, span, label {
        color: #FFFFFF !important;
    }
    h1, h2 {
        color: #FF9800 !important;
        font-weight: bold !important;
    }
    
    /* Boutons */
    .stButton>button {
        background-color: #FF9800 !important;
        color: #000000 !important;
        font-weight: bold !important;
        border: 2px solid #FFFFFF !important;
    }
    
    /* Champs de saisie (Inputs, Selectbox) */
    .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1A1A1A !important;
        color: #FFFFFF !important;
        border: 1px solid #FF9800 !important;
    }
    
    /* Onglets (Tabs) */
    button[data-baseweb="tab"] {
        color: #FFFFFF !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #FF9800 !important;
        border-bottom-color: #FF9800 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Connexion sécurisée directe à Supabase
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
    if not URL_WEBHOOK_WHATSAPP:
        return
    if est_repas:
        texte = f"🍽️ *AlcooSuivi* : {pseudo} vient de déclarer un repas ! L'absorption des prochains verres sera ralentie (Modèle image_8.png). 🥪"
    else:
        texte = f"🍹 *AlcooSuivi* : {pseudo} vient de s'enfiler un verre ! ({detail_conso}) ! La courbe grimpe ! 📈"
    try:
        requests.post(URL_WEBHOOK_WHATSAPP, json={"message": texte, "pseudo": pseudo})
    except Exception:
        pass

# --- CONFIGURATION ÉQUIPE ---
if "profils" not in st.session_state:
    st.session_state.profils = {
        "Lolo": {"sexe": "Homme", "poids": 75},
        "Poum": {"sexe": "Homme", "poids": 75},
        "Nico": {"sexe": "Homme", "poids": 75},
        "Duj": {"sexe": "Homme", "poids": 75}
    }
profils = st.session_state.profils

# --- CHARGEMENT DEPUIS LE CLOUD ---
def charger_donnees_depuis_cloud():
    try:
        boissons = supabase.table("drinks").select("*").order("created_at", desc=False).execute()
        repas = supabase.table("meals").select("*").order("created_at", desc=False).execute()
        return (boissons.data if boissons.data else []), (repas.data if repas.data else [])
    except Exception as e:
        st.error(f"⚠️ Erreur de lecture Cloud : {e}")
        return [], []

boissons_nuageuses, repas_nuage = charger_donnees_depuis_cloud()

# --- INTERFACE : 1. CONFIGURATION ÉQUIPE ---
st.title("🪳 Haggis et les cafards — Suivi d'absorption")
st.header("👥 1. Configuration de l'équipe")
onglet_Ajusteur, tab_Ajouter = st.tabs(["✏️ Ajuster les poids", "➕ Ajouter un invité"])

with onglet_Ajusteur:
    cols = st.columns(len(profils))
    for i, (nom, info) in enumerate(profils.items()):
        with cols[i]:
            st.subheader(nom)
            nouveau_poids = st.number_input(f"Poids (kg) - {nom}", min_value=40, max_value=150, value=info["poids"], key=f"poids_{nom}")
            st.session_state.profils[nom]["poids"] = nouveau_poids

with tab_Ajouter:
    col1, col2, col3 = st.columns(3)
    with col1:
        nouveau_nom = st.text_input("Nom de l'invité")
    with col2:
        nouveau_sexe = st.selectbox("Sexe", ["Homme", "Femme"])
    with col3:
        nouveau_poids_inv = st.number_input("Poids (kg)", min_value=40, max_value=150, value=70)
    
    if st.button("Ajouter à l'équipe"):
        if nouveau_nom and nouveau_nom not in st.session_state.profils:
            st.session_state.profils[nouveau_nom] = {"sexe": nouveau_sexe, "poids": nouveau_poids_inv}
            st.success(f"✔️ {nouveau_nom} a rejoint la table !")
            st.rerun()

st.write("---")

# --- INTERFACE : 2. DÉCLARATION DES ENTRÉES ---
st.header("🍹 2. Déclaration des consommations & repas")
choix_type = st.radio("Type d'entrée :", ["Un verre de l'amitié 🍺", "Un repas complet 🍽️"], horizontal=True)

moment_actuel = datetime.datetime.now().isoformat()

if "repas" in choix_type.lower():
    Qui = st.selectbox("Qui a mangé ?", list(profils.keys()))
    if st.button("Enregistrer le repas 💾"):
        try:
            supabase.table("meals").insert({"pseudo": Qui, "created_at": moment_actuel}).execute()
            envoyer_alerte_whatsapp(Qui, "", est_repas=True)
            st.success(f"🍽️ Repas enregistré pour {Qui}")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur d'écriture Repas : {e}")
else:
    c1, c2, c3 = st.columns(3)
    with c1:
        Qui = st.selectbox("Qui consomme ?", list(profils.keys()))
    with c2:
        Volume_ml = st.number_input("Volume du verre (ml)", min_value=10, max_value=1000, value=250, step=10)
    with c3:
        Degre_Alcool = st.number_input("Degré d'alcool (° ou %)", min_value=0.0, max_value=100.0, value=5.0, step=0.5)

    if st.button("Enregistrer le verre 💾"):
        try:
            label_boisson = f"{Volume_ml}ml @ {Degre_Alcool}%"
            # Assure-toi que 'type_boisson' correspond exactement au nom de ta colonne dans Supabase
            supabase.table("drinks").insert({
                "pseudo": Qui, 
                "type_boisson": label_boisson, 
                "volume": Volume_ml, 
                "created_at": moment_actuel
            }).execute()
            envoyer_alerte_whatsapp(Qui, label_boisson, est_repas=False)
            st.success(f"🍹 Verre enregistré pour {Qui} ({label_boisson})")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur d'écriture Boisson : {e}")

st.write("---")

# --- INTERFACE : 3. GRAPHIC & ALCOOLEMIE ---
st.header("📊 3. Évolution des courbes d'alcoolémie")

if boissons_nuageuses:
    df_verres = pd.DataFrame(boissons_nuageuses)
    df_verres['created_at'] = pd.to_datetime(df_verres['created_at'])
    
    df_repas = pd.DataFrame(repas_nuage) if repas_nuage else pd.DataFrame(columns=['pseudo', 'created_at'])
    if not df_repas.empty:
        df_repas['created_at'] = pd.to_datetime(df_repas['created_at'])
        
    debut_suivi = df_verres['created_at'].min()
    fin_suivi = datetime.datetime.now()
    axe_temps = pd.date_range(start=debut_suivi, end=fin_suivi, freq='5min')
    
    df_graphique = pd.DataFrame(index=axe_temps)
    
    for nom, info in profils.items():
        poids = info["poids"]
        coef_diffusion = 0.7 if info["sexe"] == "Homme" else 0.6
        taux_liste = []
        
        for t in axe_temps:
            verres_passes = df_verres[(df_verres['pseudo'] == nom) & (df_verres['created_at'] <= t)]
            repas_passes = df_repas[(df_repas['pseudo'] == nom) & (df_repas['created_at'] <= t)] if not df_repas.empty else pd.DataFrame()
            
            total_alcool_g = 0
            for _, row in verres_passes.iterrows():
                vol = row['volume']
                
                try:
                    string_degre = row['type_boisson'].split('@')[1].replace('%', '').strip()
                    degre = float(string_degre) / 100.0
                except Exception:
                    degre = 0.05
                    
                masse_alcool = vol * degre * 0.8
                
                a_mange = False
                if not repas_passes.empty:
                    for _, r_row in repas_passes.iterrows():
                        diff = (row['created_at'] - r_row['created_at']).total_seconds() / 3600.0
                        if 0 <= diff <= 2.0:
                            a_mange = True
                            break
                
                total_alcool_g += masse_alcool * 0.55 if a_mange else masse_alcool
            
            heures_ecoulees = (t - debut_suivi).total_seconds() / 3600.0
            taux_theorique = (total_alcool_g / (poids * coef_diffusion)) - (0.15 * heures_ecoulees)
            taux_liste.append(max(0.0, taux_theorique))
            
        df_graphique[nom] = taux_liste

    st.line_chart(df_graphique)
    
    st.subheader("📋 Historique des entrées")
    st.dataframe(df_verres[['pseudo', 'type_boisson', 'volume', 'created_at']].tail(10))
else:
    st.info("Aucune donnée disponible. Ajoutez une consommation pour générer les graphiques d'absorption.")
