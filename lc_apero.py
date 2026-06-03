import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Configuration de la page pour mobile
st.set_page_config(page_title="AlcooSuivi", page_icon="🍻", layout="centered")

st.title("🍻 AlcooSuivi de Soirée")
st.write("Suivi multi-joueurs de l'alcoolémie en temps réel.")

# Initialisation du dictionnaire des utilisateurs dans la session
if "users" not in st.session_state:
    st.session_state.users = {}

# --- SECTION 1 : GESTION DES PROFILS ---
st.header("👥 1. Gestion des profils")
with st.form("Ajouter un profil"):
    name = st.text_input("Prénom / Pseudo").strip()
    sex = st.selectbox("Sexe", ["Homme", "Femme"])
    weight = st.number_input("Poids (kg)", min_value=30, max_value=200, value=70)
    submit_user = st.form_submit_button("Créer le profil")
    
    if submit_user and name:
        if name not in st.session_state.users:
            st.session_state.users[name] = {
                "sex": sex,
                "weight": weight,
                "drinks": []  # Liste de dicts : {'minute': int, 'grams': float}
            }
            st.success(f"Profil de {name} ajouté !")
        else:
            st.warning("Ce pseudo existe déjà.")

# Affichage des profils actifs
if st.session_state.users:
    st.write(f"Profils actifs : {', '.join(st.session_state.users.keys())}")
else:
    st.info("Ajoutez au moins un profil pour commencer.")

# --- SECTION 2 : AJOUTER UN VERRE ---
st.header("🍹 2. Enregistrer un verre")
if st.session_state.users:
    with st.form("Ajouter un verre"):
        current_user = st.selectbox("Qui boit ?", list(st.session_state.users.keys()))
        vol = st.number_input("Volume du verre (mL)", min_value=10, max_value=1000, value=250, step=10)
        degree = st.number_input("Degré d'alcool (%)", min_value=0.0, max_value=100.0, value=5.0, step=0.5)
        time_min = st.number_input("Temps écoulé depuis le début de la soirée (minutes)", min_value=0, value=0, step=15)
        submit_drink = st.form_submit_button("Santé ! 🥂")
        
        if submit_drink:
            # Calcul des grammes d'alcool pur
            grams_alcohol = vol * (degree / 100.0) * 0.8
            st.session_state.users[current_user]["drinks"].append({
                "minute": time_min,
                "grams": grams_alcohol
            })
            st.success(f"Verre enregistré pour {current_user} à T+{time_min} min.")

# --- SECTION 3 : CALCULS ET GRAPHISME ---
st.header("📈 3. Évolution de l'alcoolémie")

SIMULATION_DURATION_HOURS = 10
total_minutes = SIMULATION_DURATION_HOURS * 60
timeline = np.arange(0, total_minutes, 5) # Calcul toutes les 5 minutes

def compute_bac_timeline(user_data, total_mins):
    r = 0.7 if user_data["sex"] == "Homme" else 0.6
    weight = user_data["weight"]
    elimination_per_minute = 0.15 / 60  # Décroissance de 0.15 g/L par heure
    
    bac_profile = np.zeros(total_mins)
    
    # On regroupe l'alcool apporté par minute
    drinks_per_minute = {}
    for d in user_data["drinks"]:
        m = d["minute"]
        drinks_per_minute[m] = drinks_per_minute.get(m, 0.0) + d["grams"]
        
    current_bac = 0.0
    for m in range(total_mins):
        # Absorption instantanée simplifiée (modèle de Widmark brut)
        if m in drinks_per_minute:
            current_bac += drinks_per_minute[m] / (weight * r)
            
        # Élimination par le foie
        if current_bac > 0:
            current_bac -= elimination_per_minute
            if current_bac < 0:
                current_bac = 0.0
                
        bac_profile[m] = current_bac
    return bac_profile

if st.session_state.users:
    fig, ax = plt.subplots(figsize=(8, 4))
    has_data = False
    
    for name, data in st.session_state.users.items():
        if data["drinks"]:
            has_data = True
            bac_series = compute_bac_timeline(data, total_minutes)
            # Conversion de la timeline en heures pour le graphique
            ax.plot(timeline / 60.0, bac_series, label=name, linewidth=2)
            
            # Affichage du taux max actuel ou instantané
            current_max = max(bac_series)
            st.write(f"**{name}** : Taux maximum théorique atteint : `{current_max:.2f} g/L`")
            
    if has_data:
        ax.axhline(y=0.5, color='r', linestyle='--', label='Limite légale (0.5 g/L)')
        ax.set_xlabel("Temps (Heures depuis le début)")
        ax.set_ylabel("Alcoolémie (g/L)")
        ax.set_title("Évolution du taux d'alcoolémie")
        ax.set_ylim(bottom=0)
        ax.legend()
        ax.grid(True, linestyle=':', alpha=0.6)
        st.pyplot(fig)
    else:
        st.info("Aucun verre n'a encore été enregistré.")
else:
    st.info("Créez des profils pour afficher le graphique.")

# Bouton de réinitialisation
if st.button("🔄 Réinitialiser la soirée"):
    st.session_state.users = {}
    st.rerun()
