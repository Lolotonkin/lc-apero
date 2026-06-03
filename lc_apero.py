import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 1. Configuration de la page pour mobile et ordinateur
st.set_page_config(page_title="AlcooSuivi de Soirée", page_icon="🍻", layout="centered")

st.title("🍻 AlcooSuivi de Soirée")
st.subheader("Suivi multi-joueurs de l'alcoolémie en temps réel.")

# Initialisation de la mémoire de l'application
if "profiles" not in st.session_state:
    st.session_state.profiles = {}

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
    if pseudo_clean not in st.session_state.profiles:
        st.session_state.profiles[pseudo_clean] = {
            "sexe": sexe,
            "poids": poids,
            "drinks": [],
            "created_at": datetime.now()
        }
        st.success(f"Profil de {pseudo_clean} créé !")
    else:
        st.warning(f"Le profil {pseudo_clean} existe déjà.")

# --- SECTION 2 : ENREGISTRER UN VERRE ---
if st.session_state.profiles:
    st.header("🍹 2. Enregistrer un verre")
    
    # Sélection du joueur
    selected_profile = st.selectbox("Qui boit ?", list(st.session_state.profiles.keys()))
    
    # Sélection de la boisson
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

    # Bouton d'action instantané
    if st.button(f"🍹 Ajouter ce verre à {selected_profile} maintenant"):
        # Calcul de la masse d'alcool pur : Vol(ml) * (Degre/100) * 0.8 (densité de l'éthanol)
        alcool_g = volume * (degre / 100.0) * 0.8
        heure_actuelle = datetime.now()
        
        st.session_state.profiles[selected_profile]["drinks"].append({
            "time": heure_actuelle,
            "alcool_g": alcool_g,
            "label": type_boisson
        })
        st.success(f"Verre ajouté à {heure_actuelle.strftime('%H:%M:%S')} !")

else:
    st.info("Ajoutez au moins un profil ci-dessus pour commencer à enregistrer des verres.")

# --- SECTION 3 : ÉVOLUTION DE L'ALCOOLÉMIE ---
st.header("📈 3. Évolution de l'alcoolémie")

# Vérification si au moins un verre a été consommé dans toute la session
has_drinks = any(len(p["drinks"]) > 0 for p in st.session_state.profiles.values())

if not has_drinks:
    st.info("Sélectionnez un profil et ajoutez un verre pour voir la simulation graphique.")
else:
    # Récupération de tous les repères de temps pour caler le graphique
    all_times = []
    for p in st.session_state.profiles.values():
        all_times.append(p["created_at"])
        for d in p["drinks"]:
            all_times.append(d["time"])
    
    # Le graphique démarre au moment du tout premier événement de la soirée
    start_time = min(all_times)
    # Le graphique va jusqu'à maintenant + 4 heures pour anticiper la phase de dessalage
    end_time = datetime.now() + timedelta(hours=4)
    
    # Calcul du nombre total de minutes à simuler
    total_minutes = max(1, int((end_time - start_time).total_seconds() / 60))
    
    # Création des axes de temps parfaitement alignés
    timeline_minutes = np.arange(0, total_minutes + 1)
    timeline_hours = timeline_minutes / 60.0
    
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Taux d'élimination moyen par minute (0.15 g/L par heure)
    elimination_par_minute = 0.15 / 60.0
    
    # Calcul des courbes pour chaque profil
    for name, p in st.session_state.profiles.items():
        r = 0.7 if p["sexe"] == "Homme" else 0.6
        poids = p["poids"]
        
        # Pré-calcul des minutes exactes où les verres ont été pris par rapport au point zéro
        verres_minutes = []
        for d in p["drinks"]:
            minute_exacte = int((d["time"] - start_time).total_seconds() / 60)
            verres_minutes.append((minute_exacte, d["alcool_g"]))
            
        bac_series = []
        current_bac = 0.0
        
        # Simulation minute par minute
        for m in timeline_minutes:
            # 1. Ajout de l'alcool si un ou plusieurs verres ont été bus à cette minute exacte
            for min_verre, alcool_g in verres_minutes:
                if min_verre == m:
                    current_bac += alcool_g / (poids * r)
            
            # 2. Élimination naturelle du foie
            if current_bac > 0:
                current_bac -= elimination_par_minute
                if current_bac < 0:
                    current_bac = 0.0
            
            bac_series.append(current_bac)
            
        # Affichage de la ligne sur le graphique (longueurs toujours identiques)
        ax.plot(timeline_hours, bac_series, label=f"{name} (Max: {max(bac_series):.2f} g/L)", linewidth=2)

    # Paramétrage visuel du graphique
    ax.axhline(y=0.5, color='r', linestyle='--', label="Limite légale conduite (0.5 g/L)")
    ax.set_xlabel("Temps écoulé depuis le début (en heures)")
    ax.set_ylabel("Alcoolémie (g/L)")
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right")
    ax.grid(True, linestyle=':', alpha=0.6)
    
    st.pyplot(fig)
