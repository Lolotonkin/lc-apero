import streamlit as st
from supabase import create_client, Client
import requests
import pandas as pd
import datetime

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Haggis et les cafards 🪳", layout="wide")

# Connexion sécurisée directe (Hardcoded pour éviter les bugs de l'éditeur Streamlit)
SUPABASE_URL = "https://rjexlotreipfjbgpfcnt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqZXhsb3RyZWlwZmpiZ3BmY250Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MDUyOTkyNywiZXhwIjoyMDk2MTA1OTI3fQ.0vMnopwPCMQaOmzCPNcdc4HLqr1d1npoqL3xXNnxGQ8"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"🔑 Erreur d'initialisation Supabase : {e}")
    st.stop()

URL_WEBHOOK_WHATSAPP = st.secrets.get("URL_WEBHOOK_WHATSAPP", "")

# --- ENVOI DES ALERTES WHATSAPP ---
def envoyer_alerte_whatsapp(pseudo, boisson, est_repas=False):
    if not URL_WEBHOOK_WHATSAPP:
        return
    if est_repas:
        texte = f"🍽️ *AlcooSuivi* : {pseudo} vient de déclarer un repas ! L'absorption des prochains verres sera ralentie (Modèle image_8.png). 🥪"
    else:
        texte = f"🍹 *AlcooSuivi* : {pseudo} vient de s'enfiler un verre de type {boisson} ! La courbe grimpe ! 📈"
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
        # Requêtes sur les vraies tables Supabase (drinks et meals)
        boissons = supabase.table("drinks").select("*").order("created_at", desc=False).execute()
        repas = supabase.table("meals").select("*").order("created_at", desc=False).execute()
        return (boissons.data if boissons.data else []), (repas.data if repas.data else [])
    except Exception as e:
        st.error(f"⚠️ Erreur de lecture Cloud : {e}")
        return [], []

boissons_nuageuses, repas_nuage = charger_donnees_depuis_cloud()

# --- INTERFACE : 1. CONFIGURATION ÉQUIPE ---
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
c1, c2, c3 = st.columns(3)
with c1:
    Qui = st.selectbox("Qui consomme ?", list(profils.keys()))
with c2:
    Type_Boisson = st.selectbox("Type de boisson", ["Bière Léger (4%)", "Bière Forte (8%)", "Vin / Champagne (12%)", "Apéritif / Fort (40%)", "Repas complet 🍽️"])
with c3:
    Volume_ml = st.number_input("Volume (ml)", min_value=10, max_value=1000, value=250, step=10)

if st.button("Enregistrer la sélection"):
    moment_actuel = datetime.datetime.now().isoformat()
    
    if "Repas" in Type_Boisson:
        # Enregistrement dans la table 'meals'
        try:
            supabase.table("meals").insert({"pseudo": Qui, "created_at": moment_actuel}).execute()
            envoyer_alerte_whatsapp(Qui, Type_Boisson, est_repas=True)
            st.success(f"🍽️ Repas enregistré pour {Qui}")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur d'écriture Repas : {e}")
    else:
        # Enregistrement dans la table 'drinks'
        try:
            supabase.table("drinks").insert({
                "pseudo": Qui, 
                "type_boisson": Type_Boisson, 
                "volume": Volume_ml, 
                "created_at": moment_actuel
            }).execute()
            envoyer_alerte_whatsapp(Qui, Type_Boisson, est_repas=False)
            st.success(f"🍹 {Type_Boisson} ({Volume_ml}ml) enregistré pour {Qui}")
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
        
    # Génération de la ligne temporelle du graphique (du premier verre jusqu'à maintenant)
    debut_suivi = df_verres['created_at'].min()
    fin_suivi = datetime.datetime.now()
    axe_temps = pd.date_range(start=debut_suivi, end=fin_suivi, freq='5min')
    
    df_graphique = pd.DataFrame(index=axe_temps)
    
    # Calcul Widmark itératif par personne
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
                degre = 0.04 if "4%" in row['type_boisson'] else (0.08 if "8%" in row['type_boisson'] else (0.12 if "12%" in row['type_boisson'] else 0.40))
                masse_alcool = vol * degre * 0.8
                
                # Effet du repas : si un repas a eu lieu dans les 2 heures précédant le verre
                a_mange = False
                if not repas_passes.empty:
                    for _, r_row in repas_passes.iterrows():
                        diff = (row['created_at'] - r_row['created_at']).total_seconds() / 3600.0
                        if 0 <= diff <= 2.0:
                            a_mange = True
                            break
                
                total_alcool_g += masse_alcool * 0.55 if a_mange else masse_alcool
            
            heures_ecoulees = (t - debut_suivi).total_seconds() / 3600.0
            # Élimination naturelle : 0.15g/l par heure
            taux_theorique = (total_alcool_g / (poids * coef_diffusion)) - (0.15 * heures_ecoulees)
            taux_liste.append(max(0.0, taux_theorique))
            
        df_graphique[nom] = taux_liste

    st.line_chart(df_graphique)
    
    st.subheader("📋 Historique des derniers verres enregistrés")
    st.dataframe(df_verres[['pseudo', 'type_boisson', 'volume', 'created_at']].tail(10))
else:
    st.info("Aucune donnée disponible. Ajoutez une consommation pour générer les graphiques d'absorption.")
