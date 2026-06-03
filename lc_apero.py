import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# 1. Configuration de la page pour mobile et ordinateur
st.set_page_config(page_title="AlcooSuivi de Soirée", page_icon="🍻", layout="centered")

st.title("🍻 AlcooSuivi de Soirée")
st.subheader("Suivi multi-joueurs de l'alcoolémie en temps réel.")

# --- CONFIGURATION DE TON LIEN ---
A_PROPOS_URL = "https://lc-apero.streamlit.app"

# --- MÉMOIRE GLOBALE ET PARTAGÉE ---
@st.cache_resource
def get_shared_db():
    return {"profiles": {}}

shared_db = get_shared_db()
profiles = shared_db["profiles"]

# --- SECTION 1 : GESTION DES PROFILS ---
st.header("👥 1. Gestion des profils")

with st.form("profile_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        pseudo = st.text_input("Prénom / Pseudo")
    with col2:
        sexe = st.selectbox("Sexe", ["Homme", "Femme"])
    with col3:
        poids = st.number_input("Poids (kg)", min_value=30, max_value=200, value=70)
    
    submit_profile = st.form_submit_button("Créer le profil")

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
        st.success(f"Profil de {pseudo_clean} créé !")
        st.rerun()
    else:
        st.warning(f"Le profil {pseudo_clean} existe déjà.")

# --- SECTION 2 : ENREGISTRER UN VERRE ---
if profiles:
    st.header("🍹 2. Enregistrer un verre")
    
    selected_profile = st.selectbox("Qui boit ?", list(profiles.keys()))
    
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
        st.success(f"Verre ajouté à {heure_actuelle.strftime('%H:%M:%S')} !")
        st.rerun()

else:
    st.info("Ajoutez au moins un profil ci-dessus pour commencer à enregistrer des verres.")

# --- SECTION 3 : ÉVOLUTION DE L'ALCOOLÉMIE ---
st.header("📈 3. Évolution de l'alcoolémie")

has_drinks = any(len(p["drinks"]) > 0 for p in profiles.values())

if not has_drinks:
    st.info("Sélectionnez un profil et ajoutez un verre pour voir la simulation graphique.")
else:
    all_times = []
    for p in profiles.values():
        all_times.append(p["created_at"])
        for d in p["drinks"]:
            all_times.append(d["time"])
    
    start_time = min(all_times)
    end_time = datetime.now(ZoneInfo("Europe/Paris")).replace(tzinfo=None) + timedelta(hours=4)
    
    total_minutes = max(1, int((end_time - start_time).total_seconds() / 60))
    timeline_minutes = np.arange(0, total_minutes + 1)
    
    timeline_dates = [start_time + timedelta(minutes=int(m)) for m in timeline_minutes]
    
    fig, ax = plt.subplots(figsize=(10, 5))
    elimination_par_minute = 0.15 / 60.0
    
    for name, p in profiles.items():
        r = 0.7 if p["sexe"] == "Homme" else 0.6
        poids = p["poids"]
        
        verres_minutes = [(int((d["time"] - start_time).total_seconds() / 60), d["alcool_g"]) for d in p["drinks"]]
            
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
            
        ax.plot(timeline_dates, bac_series, label=f"{name} (Max: {max(bac_series):.2f} g/L)", linewidth=2)

    ax.axhline(y=0.5, color='r', linestyle='--', label="Limite légale conduite (0.5 g/L)")
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    fig.autofmt_xdate()
    
    ax.set_xlabel("Heure réelle (Paris)")
    ax.set_ylabel("Alcoolémie (g/L)")
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right")
    ax.grid(True, linestyle=':', alpha=0.6)
    
    st.pyplot(fig)

# --- SECTION 4 : QR CODE D'INVITATION ---
st.markdown("---")
st.header("📢 4. Inviter des potes à la soirée")
st.write("Fais flasher ce QR Code à tes amis pour qu'ils rejoignent l'application sur leur téléphone !")

qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={A_PROPOS_URL}"

col_qr1, col_qr2, col_qr3 = st.columns([1, 2, 1])
with col_qr2:
    st.image(qr_api_url, caption="Scanne-moi pour rejoindre la session !", use_container_width=False)

# --- SECTION 5 : RAZ DE LA SOIRÉE (AVEC CONFIRMATION) ---
st.markdown("---")

# Initialisation du système de sécurité si absent
if "confirm_raz" not in st.session_state:
    st.session_state.confirm_raz = False

if not st.session_state.confirm_raz:
    # Premier bouton d'alerte
    if st.button("🗑️ Réinitialiser la soirée (Effacer tous les profils)"):
        st.session_state.confirm_raz = True
        st.rerun()
else:
    # Bloc de confirmation de sécurité
    st.error("⚠️ **Es-tu sûr de vouloir tout effacer ?** Cette action supprimera définitivement tous les profils et tous les verres.")
    col_oui, col_non = st.columns(2)
    with col_oui:
        if st.button("🔥 Oui, tout effacer", type="primary"):
            profiles.clear()
            st.session_state.confirm_raz = False
            st.success("La soirée a été remise à zéro !")
            st.rerun()
    with col_non:
        if st.button("❌ Non, annuler"):
            st.session_state.confirm_raz = False
            st.rerun()
