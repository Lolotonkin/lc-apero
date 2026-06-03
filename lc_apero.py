import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# 1. Configuration de la page pour mobile et ordinateur
st.set_page_config(page_title="Haggis & les cafards", page_icon="🍻", layout="centered")

# --- DESIGN PERSONNALISÉ (MODE SOMBRE / PUB) ---
st.markdown("""
    <style>
    /* Fond général de l'application */
    .stApp {
        background-color: #12141c;
        color: #f1f5f9;
    }
    /* Titres stylisés couleur ambre/bière */
    h1, h2, h3, h4 {
        color: #ff9f1c !important;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 700;
    }
    /* Blocs de formulaires, onglets et sections */
    div[data-testid="stForm"], .stAlert, div[data-testid="stExpander"] {
        background-color: #1e2230 !important;
        border: 1px solid #2d3446 !important;
        border-radius: 12px !important;
        padding: 20px;
    }
    /* Style pour les onglets */
    button[data-baseweb="tab"] {
        color: #94a3b8 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ff9f1c !important;
        border-color: #ff9f1c !important;
    }
    /* Inputs text et selectbox */
    .stTextInput json, .stSelectbox, .stNumberInput {
        color: #f1f5f9;
    }
    /* Boutons */
    .stButton>button {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🍻 Haggis et les cafards (et les amis) 🪳")
st.subheader("AlcooSuivi officiel de la bande en temps réel.")

# --- CONFIGURATION DE TON LIEN ---
A_PROPOS_URL = "https://lc-apero.streamlit.app"

# --- MÉMOIRE GLOBALE ET PARTAGÉE (AVEC LES 4 PROFILS PAR DÉFAUT) ---
@st.cache_resource
def get_shared_db():
    heure_paris_naiv = datetime.now(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
    # Pré-population automatique avec un poids par défaut de 75kg à ajuster
    default_profiles = {
        "Lolo'": {"sexe": "Homme", "poids": 75, "drinks": [], "created_at": heure_paris_naiv},
        "Poum's": {"sexe": "Homme", "poids": 75, "drinks": [], "created_at": heure_paris_naiv},
        "Nico'": {"sexe": "Homme", "poids": 75, "drinks": [], "created_at": heure_paris_naiv},
        "Duj'": {"sexe": "Homme", "poids": 75, "drinks": [], "created_at": heure_paris_naiv}
    }
    return {"profiles": default_profiles}

shared_db = get_shared_db()
profiles = shared_db["profiles"]

# --- SECTION 1 : GESTION DES PROFILS (AVEC ONGLETS) ---
st.header("👥 1. Configuration de l'équipe")

tab_Ajuster, tab_Ajouter = st.tabs(["✏️ Ajuster les poids (La Bande)", "➕ Ajouter un invité"])

with tab_Ajuster:
    if profiles:
        target_profile = st.selectbox("Qui veux-tu peser ?", list(profiles.keys()))
        
        with st.form(f"edit_form_{target_profile}"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                poids_actuel = int(profiles[target_profile]["poids"])
                new_poids = st.number_input(f"Vrai poids de {target_profile} (kg)", min_value=30, max_value=200, value=poids_actuel)
            with col_e2:
                sexe_actuel = profiles[target_profile]["sexe"]
                sexe_idx = 0 if sexe_actuel == "Homme" else 1
                new_sexe = st.selectbox(f"Sexe de {target_profile}", ["Homme", "Femme"], index=sexe_idx)
            
            if st.form_submit_button(f"💾 Valider le poids de {target_profile}"):
                profiles[target_profile]["poids"] = new_poids
                profiles[target_profile]["sexe"] = new_sexe
                st.success(f"Poids mis à jour : {target_profile} fait maintenant {new_poids} kg !")
                st.rerun()

with tab_Ajouter:
    with st.form("profile_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            pseudo = st.text_input("Prénom / Pseudo de l'invité")
        with col2:
            sexe = st.selectbox("Sexe", ["Homme", "Femme"])
        with col3:
            poids = st.number_input("Poids (kg)", min_value=30, max_value=200, value=75)
        
        submit_profile = st.form_submit_button("➕ Ajouter à la table")

    if submit_profile and pseudo:
        pseudo_clean = pseudo.strip()
        if pseudo_clean not in profiles:
            heure_paris_naiv = datetime.now(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
            profiles[pseudo_clean] = {
                "sexe": sexe,
                "poids": poids,
                "drinks": [],
                "created_at": heure_paris_naiv
            }
            st.success(f"Bienvenue à la soirée, {pseudo_clean} !")
            st.rerun()
        else:
            st.warning(f"Le profil {pseudo_clean} est déjà de la partie.")

# --- SECTION 2 : ENREGISTRER UN VERRE ---
if profiles:
    st.header("🍹 2. Enregistrer un verre")
    
    selected_profile = st.selectbox("Qui trinque ?", list(profiles.keys()))
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        type_boisson = st.selectbox(
            "Type de boisson", 
            ["Bière (25cl - 5%)", "Vin (12.5cl - 12%)", "Fort (4cl - 40%)", "Sur mesure"]
        )
    
    with col_b2:
        if type_boisson == "Sur mesure":
            volume = st.number_input("Volume (ml)", min_value=1, value=250)
            degre = st.number_input("Degré (%)", min_value=0.0, max_value=100.0, value=5.0)
        else:
            if "Bière" in type_boisson:
                volume, degre = 250, 5.0
            elif "Vin" in type_boisson:
                volume, degre = 125, 12.0
            else:
                volume, degre = 40, 40.0

    if st.button(f"🍹 Ajouter ce verre à {selected_profile} maintenant"):
        alcool_g = volume * (degre / 100.0) * 0.8
        heure_actuelle = datetime.now(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
        
        profiles[selected_profile]["drinks"].append({
            "time": heure_actuelle,
            "alcool_g": alcool_g,
            "label": type_boisson
        })
        st.success(f"Santé {selected_profile} ! Verre enregistré à {heure_actuelle.strftime('%H:%M:%S')}.")
        st.rerun()

# --- SECTION 3 : ÉVOLUTION DE L'ALCOOLÉMIE ---
st.header("📈 3. État de la bande (Évolution graphique)")

has_drinks = any(len(p["drinks"]) > 0 for p in profiles.values())

if not has_drinks:
    st.info("Aucun verre enregistré pour le moment. Servez le premier coup pour lancer le graphique !")
else:
    all_times = []
    for p in profiles.values():
        t_created = p["created_at"].replace(tzinfo=None) if p["created_at"].tzinfo is not None else p["created_at"]
        all_times.append(t_created)
        for d in p["drinks"]:
            t_drink = d["time"].replace(tzinfo=None) if d["time"].tzinfo is not None else d["time"]
            all_times.append(t_drink)
    
    start_time = min(all_times)
    end_time = datetime.now(ZoneInfo("Europe/Paris")).replace(tzinfo=None) + timedelta(hours=4)
    
    total_minutes = max(1, int((end_time - start_time).total_seconds() / 60))
    timeline_minutes = np.arange(0, total_minutes + 1)
    
    timeline_dates = [start_time + timedelta(minutes=int(m)) for m in timeline_minutes]
    
    fig, ax = plt.subplots(figsize=(10, 5), facecolor='#12141c')
    ax.set_facecolor('#1e2230')
    elimination_par_minute = 0.15 / 60.0
    
    for name, p in profiles.items():
        r = 0.7 if p["sexe"] == "Homme" else 0.6
        poids = p["poids"]
        
        verres_minutes = []
        for d in p["drinks"]:
            t_drink = d["time"].replace(tzinfo=None) if d["time"].tzinfo is not None else d["time"]
            min_verre = int((t_drink - start_time).total_seconds() / 60)
            verres_minutes.append((min_verre, d["alcool_g"]))
            
        bac_series = []
        current_bac = 0.0
        
        for m in timeline_minutes:
            for min_verre, alcool_g in verres_minutes:
                if min_verre == m:
                    current_bac += alcool_g / (poids * r)
            
            if current_bac > 0:
                current_bac -= elimination_par_minute
                if current_bac < 0:
                    current_bac = 0.0
            
            bac_series.append(current_bac)
        
        if max(bac_series) > 0 or name == "Lolo'":
            ax.plot(timeline_dates, bac_series, label=f"{name} ({poids}kg - Max: {max(bac_series):.2f} g/L)", linewidth=2.5)

    ax.axhline(y=0.5, color='#ef4444', linestyle='--', label="Limite conduite (0.5 g/L)", linewidth=2)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    fig.autofmt_xdate()
    
    ax.set_xlabel("Heure réelle", color='#94a3b8')
    ax.set_ylabel("Alcoolémie (g/L)", color='#94a3b8')
    ax.tick_params(colors='#94a3b8', which='both')
    ax.set_ylim(bottom=0)
    
    for spine in ax.spines.values():
        spine.set_color('#2d3446')
        
    legend = ax.legend(loc="upper right", facecolor='#12141c', edgecolor='#2d3446')
    for text in legend.get_texts():
        text.set_color('#f1f5f9')
        
    ax.grid(True, linestyle=':', alpha=0.15, color='#94a3b8')
    
    st.pyplot(fig)

# --- SECTION 4 : QR CODE D'INVITATION ---
st.markdown("---")
st.header("📢 4. Inviter des cafards à la table")
st.write("Fais flasher ce QR Code pour qu'ils ajoutent leurs verres directement depuis leur téléphone ! ")

qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={A_PROPOS_URL}"

col_qr1, col_qr2, col_qr3 = st.columns([1, 2, 1])
with col_qr2:
    st.image(qr_api_url, caption="Scanne pour rejoindre Haggis et les cafards !", use_container_width=False)

# --- SECTION 5 : RAZ DE LA SOIRÉE (AVEC CONFIRMATION) ---
st.markdown("---")

if "confirm_raz" not in st.session_state:
    st.session_state.confirm_raz = False

if not st.session_state.confirm_raz:
    if st.button("🗑️ Réinitialiser la soirée (Vider les verres)"):
        st.session_state.confirm_raz = True
        st.rerun()
else:
    st.error("⚠️ **Es-tu sûr de vouloir tout effacer ?** Tous les verres seront supprimés, mais l'équipe de base (Lolo', Poum's, Nico', Duj') restera prête pour le prochain round.")
    col_oui, col_non = st.columns(2)
    with col_oui:
        if st.button("🔥 Oui, nettoyer la table", type="primary"):
            profiles.clear()
            heure_paris_naiv = datetime.now(ZoneInfo("Europe/Paris")).replace(tzinfo=None)
            for name, info in {
                "Lolo'": {"sexe": "Homme", "poids": 75, "drinks": [], "created_at": heure_paris_naiv},
                "Poum's": {"sexe": "Homme", "poids": 75, "drinks": [], "created_at": heure_paris_naiv},
                "Nico'": {"sexe": "Homme", "poids": 75, "drinks": [], "created_at": heure_paris_naiv},
                "Duj'": {"sexe": "Homme", "poids": 75, "drinks": [], "created_at": heure_paris_naiv}
            }.items():
                profiles[name] = info
            st.session_state.confirm_raz = False
            st.success("C'est propre ! Prêts pour une nouvelle session.")
            st.rerun()
    with col_non:
        if st.button("❌ Non, annuler"):
            st.session_state.confirm_raz = False
            st.rerun()
