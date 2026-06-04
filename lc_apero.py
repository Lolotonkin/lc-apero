import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client, Client
import requests

# 1. Configuration de la page
st.set_page_config(page_title="Haggis & les cafards", page_icon="🍻", layout="centered")

# --- DESIGN PERSONNALISÉ ---
st.markdown("""
    <style>
    .stApp { background-color: #12141c; color: #f1f5f9; }
    h1, h2, h3, h4 { color: #ff9f1c !important; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: 700; }
    div[data-testid="stForm"], .stAlert, div[data-testid="stExpander"] { background-color: #1e2230 !important; border: 1px solid #2d3446 !important; border-radius: 12px !important; padding: 20px; }
    label, .stWidgetLabel, div[data-testid="stWidgetLabel"] p { color: #f1f5f9 !important; font-weight: 600 !important; }
    .stTextInput input, .stNumberInput input, div[data-baseweb="select"] { color: #f1f5f9 !important; background-color: #12141c !important; }
    div[data-testid="stSelectbox"] div[aria-live="polite"] { color: #f1f5f9 !important; }
    button[data-baseweb="tab"] { color: #94a3b8 !important; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #ff9f1c !important; border-color: #ff9f1c !important; }
    div.stButton > button { background-color: #1e2230 !important; color: #ff9f1c !important; border: 2px solid #ff9f1c !important; border-radius: 8px !important; font-weight: bold !important; width: 100%; padding: 10px 20px; transition: all 0.2s ease-in-out; }
    div.stButton > button:hover { background-color: #ff9f1c !important; color: #12141c !important; border-color: #ff9f1c !important; }
    div[data-testid="stFormSubmitButton"] > button, button[data-testid="baseButton-primary"] { background-color: #ff9f1c !important; color: #12141c !important; border: 2px solid #ff9f1c !important; border-radius: 8px !important; font-weight: bold !important; width: 100%; padding: 10px 20px; }
    div[data-testid="stFormSubmitButton"] > button:hover, button[data-testid="baseButton-primary"]:hover { background-color: #e08a12 !important; border-color: #e08a12 !important; color: #12141c !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🍻 Haggis et les cafards 🪳")
st.subheader("Suivi permanent avec courbe d'absorption réelle (image_8.png) et alertes WhatsApp.")

# --- CONFIGURATION SÉCURITÉ & CLOUD ---
A_PROPOS_URL = "https://lc-apero-eqdne2pvte4wak5sawi8kf.streamlit.app"
PASSWORD_RAZ = "haggis2026"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    supabase = init_supabase()
except Exception:
    st.error("🔑 Configuration Supabase manquante dans les Secrets Streamlit.")
    st.stop()

WHATSAPP_WEBHOOK_URL = st.secrets.get("WHATSAPP_WEBHOOK_URL", "")

def send_whatsapp_alert(pseudo, boisson, is_meal=False):
    if not WHATSAPP_WEBHOOK_URL: return
    if is_meal:
        texte = f"🍽️ *AlcooSuivi* : {pseudo} vient de déclarer un repas ! L'absorption des prochains verres sera ralentie (Modèle image_8.png). 🥪"
    else:
        texte = f"🚨 *AlcooSuivi* : {pseudo} vient de s'enfiler un verre de type {boisson} ! La courbe grimpe ! 📈"
    try: requests.post(WHATSAPP_WEBHOOK_URL, json={"message": texte, "pseudo": pseudo})
    except Exception: pass

# --- CONFIGURATION ÉQUIPE ---
if "profiles" not in st.session_state:
    st.session_state.profiles = {
        "Lolo'": {"sexe": "Homme", "poids": 75},
        "Poum's": {"sexe": "Homme", "poids": 75},
        "Nico'": {"sexe": "Homme", "poids": 75},
        "Duj'": {"sexe": "Homme", "poids": 75}
    }
profiles = st.session_state.profiles

def load_data_from_cloud():
    drinks = supabase.table("drinks").select("*").order("created_at", desc=False).execute()
    meals = supabase.table("meals").select("*").order("created_at", desc=False).execute()
    return (drinks.data if drinks.data else []), (meals.data if meals.data else [])

cloud_drinks, cloud_meals = load_data_from_cloud()

# --- SECTION 1 : ÉQUIPE ---
st.header("👥 1. Configuration de l'équipe")
tab_Ajuster, tab_Ajouter = st.tabs(["✏️ Ajuster les poids", "➕ Ajouter un invité"])

with tab_Ajuster:
    target = st.selectbox("Qui veux-tu peser ?", list(profiles.keys()))
    with st.form(f"edit_{target}"):
        col_e1, col_e2 = st.columns(2)
        with col_e1: p_val = st.number_input("Poids (kg)", min_value=30, max_value=200, value=int(profiles[target]["poids"]))
        with col_e2: s_val = st.selectbox("Sexe", ["Homme", "Femme"], index=0 if profiles[target]["sexe"] == "Homme" else 1)
        if st.form_submit_button("💾 Valider"):
            profiles[target]["poids"] = p_val
            profiles[target]["sexe"] = s_val
            st.rerun()

with tab_Ajouter:
    with st.form("add_inv", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1: p_name = st.text_input("Prénom")
        with col2: s_name = st.selectbox("Sexe Invité", ["Homme", "Femme"])
        with col3: w_name = st.number_input("Poids Invité (kg)", min_value=30, max_value=200, value=75)
        if st.form_submit_button("➕ Ajouter"):
            if p_name and p_name.strip() not in profiles:
                profiles[p_name.strip()] = {"sexe": s_name, "poids": w_name}
                st.rerun()

# --- SECTION 2 : ACTION VERRES & REPAS ---
st.header("🍹 2. Enregistrer une activité")
selected_profile = st.selectbox("Qui fait quoi ?", list(profiles.keys()))

col_act1, col_act2 = st.columns(2)
with col_act1:
    st.markdown("#### Enregistrer un verre")
    type_boisson = st.selectbox("Type", ["Bière (25cl - 5%)", "Vin (12.5cl - 12%)", "Fort (4cl - 40%)", "Sur mesure"])
    if type_boisson == "Sur mesure":
        volume = st.number_input("Volume (ml)", min_value=1, value=250)
        degre = st.number_input("Degré (%)", min_value=0.0, max_value=100.0, value=5.0)
    else: volume, degre = (250, 5.0) if "Bière" in type_boisson else (125, 12.0) if "Vin" in type_boisson else (40, 40.0)
    
    if st.button(f"🍹 Enregistrer le verre"):
        alcool_g = volume * (degre / 100.0) * 0.8
        supabase.table("drinks").insert({"pseudo": selected_profile, "boisson": type_boisson, "alcool_g": alcool_g}).execute()
        send_whatsapp_alert(selected_profile, type_boisson, is_meal=False)
        st.success("Verre enregistré !")
        st.rerun()

with col_act2:
    st.markdown("#### Déclarer un repas")
    st.write("Modélise un repas (Actif pendant 2h) : étale la diffusion à 75min au lieu de 30min pour aplatir le pic.")
    if st.button(f"🍽️ Déclarer un repas (2h)"):
        supabase.table("meals").insert({"pseudo": selected_profile}).execute()
        send_whatsapp_alert(selected_profile, "", is_meal=True)
        st.success(f"Repas enregistré pour {selected_profile} !")
        st.rerun()

# --- TRAITEMENT TEMPOREL GLISSANT (H-2 à H+6) ---
now_local = datetime.now(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
start_window = now_local - timedelta(hours=2)
end_window = now_local + timedelta(hours=6)

total_minutes = int((end_window - start_window).total_seconds() / 60)
timeline_minutes = np.arange(0, total_minutes + 1)
timeline_dates = [start_window + timedelta(minutes=int(m)) for m in timeline_minutes]

# Parsing des verres et repas
parsed_drinks = []
for d in cloud_drinks:
    dt_local = datetime.fromisoformat(d["created_at"].replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
    parsed_drinks.append({"pseudo": d["pseudo"], "time": dt_local, "alcool_g": d["alcool_g"]})

parsed_meals = []
for m in cloud_meals:
    dt_local = datetime.fromisoformat(m["created_at"].replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
    parsed_meals.append({"pseudo": m["pseudo"], "time": dt_local})

elim_par_minute = 0.15 / 60.0
stats_bande = {}

fig, ax = plt.subplots(figsize=(10, 5), facecolor='#12141c')
ax.set_facecolor('#1e2230')

# --- MODÉLISATION DE L'ABSORPTION CONTINUE CORRIGÉE ---
for name, p in profiles.items():
    r_base = 0.7 if p["sexe"] == "Homme" else 0.6
    poids = p["poids"]
    
    user_meals = [m["time"] for m in parsed_meals if m["pseudo"] == name]
    verres_user = [d for d in parsed_drinks if d["pseudo"] == name]
    
    bac_series = []
    current_bac = 0.0
    max_reached = 0.0
    last_sober_time = None
    
    # Étape par étape, minute par minute sur la timeline globale
    for m in timeline_minutes:
        current_time = start_window + timedelta(minutes=int(m))
        
        # 1. Calcul de l'apport d'alcool arrivant dans le sang à CETTE minute précise
        apport_minute_g = 0.0
        for verre in verres_user:
            # Durée de diffusion selon l'état de digestion au moment où le verre a été bu
            bu_a_jeun = not any(0 <= (verre["time"] - mt).total_seconds() <= 7200 for mt in user_meals)
            duree_diffusion = 30 if bu_a_jeun else 75  # 30min à jeun vs 1h15 en mangeant (image_8.png)
            
            # Si le temps actuel est dans la fenêtre d'absorption de ce verre
            temps_ecoule_min = int((current_time - verre["time"]).total_seconds() / 60)
            if 0 <= temps_ecoule_min < duree_diffusion:
                # On injecte une fraction constante du verre à chaque minute
                apport_minute_g += verre["alcool_g"] / duree_diffusion
        
        # Convertir les grammes absorbés à cette minute en g/L de sang
        if apport_minute_g > 0:
            current_bac += apport_minute_g / (poids * r_base)
            
        # 2. Élimination par le foie à cette minute
        if current_bac > 0:
            current_bac -= elim_par_minute
            if current_bac < 0: current_bac = 0.0
            
        bac_series.append(current_bac)
        if current_bac > max_reached: max_reached = current_bac
        if current_bac == 0.0 and current_time <= now_local: last_sober_time = current_time

    idx_now = max(0, min(int((now_local - start_window).total_seconds() / 60), total_minutes))
    instant_bac = bac_series[idx_now]
    
    if instant_bac > 0: temps_a_jeun = "En cours de session"
    elif last_sober_time is not None:
        diff = now_local - last_sober_time
        heures, reste = divmod(diff.total_seconds(), 3600)
        minutes, _ = divmod(reste, 60)
        temps_a_jeun = f"{int(heures)}h {int(minutes)}min"
    else: temps_a_jeun = "Aucun verre"
        
    stats_bande[name] = {"Alcoolémie instantanée": f"{instant_bac:.2f} g/L", "Maximum atteint": f"{max_reached:.2f} g/L", "Temps max sans alcool": temps_a_jeun}
    if max(bac_series) > 0 or name == "Lolo'": ax.plot(timeline_dates, bac_series, label=name, linewidth=2.5)

# --- SECTION 3 : AFFICHAGE ---
st.header("📈 3. État de la bande")
st.subheader("📊 Tableau de bord instantané")
st.table(pd.DataFrame.from_dict(stats_bande, orient='index'))

st.subheader("📉 Évolution temporelle (Fenêtre glissante H-2 à H+6)")
ax.axhline(y=0.5, color='#ef4444', linestyle='--', label="Limite conduite", linewidth=2)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
ax.axvline(x=now_local, color='#94a3b8', linestyle=':', alpha=0.7, label="Maintenant")
fig.autofmt_xdate()
ax.set_ylabel("Alcoolémie (g/L)", color='#94a3b8')
ax.tick_params(colors='#94a3b8', which='both')
ax.set_ylim(bottom=0)
for spine in ax.spines.values(): spine.set_color('#2d3446')
legend = ax.legend(loc="upper right", facecolor='#12141c', edgecolor='#2d3446')
for text in legend.get_texts(): text.set_color('#f1f5f9')
ax.grid(True, linestyle=':', alpha=0.15, color='#94a3b8')
st.pyplot(fig)

# --- SECTION 4 & 5 ---
st.markdown("---")
st.header("📢 4. Partage")
st.code(A_PROPOS_URL, language="text")

st.markdown("---")
st.header("⚙️ 5. Zone de réinitialisation")
input_password = st.text_input("Saisir le code d'effacement pour déverrouiller la purge", type="password")

if input_password == PASSWORD_RAZ:
    st.warning("⚠️ Code correct. Le bouton ci-dessous effacera TOUT l'historique (Verres et Repas) du Cloud.")
    if st.button("🔥 Confirmer et purger la base Cloud définitivement"):
        supabase.table("drinks").delete().neq("pseudo", "").execute()
        supabase.table("meals").delete().neq("pseudo", "").execute()
        st.success("Toutes les données cloud ont été nettoyées !")
        st.rerun()
elif input_password:
    st.error("Code erroné.")
