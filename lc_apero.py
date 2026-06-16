import streamlit as st
from supabase import create_client, Client
import requests
import pandas as pd
import datetime
import qrcode
import io
import plotly.graph_objects as go
import numpy as np
import urllib.parse

# --- CONFIGURATION INITIALE & THÈME ---
st.set_page_config(page_title="Suivi de soirée V4.0 🍹", layout="wide", initial_sidebar_state="collapsed")

COULEURS_JOUEURS = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22', '#1abc9c', '#16a085', '#c0392b', '#8e44ad']

st.markdown("""
    <style>
    /* Réduction globale de la taille des polices pour un rendu plus discret */
    html, body, [class*="css"] { font-size: 14px !important; }
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.4rem !important; }
    h3 { font-size: 1.2rem !important; }
    h4 { font-size: 1.1rem !important; }
    h5 { font-size: 1.0rem !important; }
    
    /* Thème général sombre */
    .stApp, .stApp > header { background-color: #000000 !important; color: #FFFFFF !important; }
    h1, h2, h3, h4, h5, p, span, label, div[data-testid="stMarkdownContainer"] { color: #FFFFFF !important; }
    h1, h2 { color: #FF9800 !important; font-weight: bold !important; }
    
    /* Boutons de l'interface */
    div[data-testid="stButton"] > button, 
    div[data-testid="stFormSubmitButton"] > button { 
        background-color: #1A1A1A !important; 
        color: #FF9800 !important; 
        font-weight: bold !important; 
        border: 1px solid #FF9800 !important; 
        border-radius: 8px !important;
        font-size: 0.9rem !important;
    }
    div[data-testid="stButton"] > button:hover, 
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #333333 !important;
        border-color: #FFFFFF !important;
        color: #FFFFFF !important;
    }
    
    /* Champs de saisie */
    .stTextInput input, .stNumberInput input, div[data-baseweb="select"], div[data-baseweb="select"] > div { 
        background-color: #1A1A1A !important; 
        color: #FFFFFF !important; 
        border: 1px solid #FFFFFF !important; 
        border-radius: 8px !important;
    }
    
    /* Accordéons (Expanders) & Métriques */
    div[data-testid="stExpander"] { background-color: #1A1A1A !important; border: 1px solid #FF9800 !important; border-radius: 8px !important; margin-bottom: 6px; }
    div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary * { 
        color: #FF9800 !important; font-weight: bold !important; font-size: 1.0rem !important; 
    }
    div[data-testid="stMetricValue"] { color: #FF9800 !important; font-size: 1.4rem !important; }

    /* Historique Timeline */
    .timeline-row { border-left: 3px solid #FF9800; padding-left: 15px; margin-bottom: 5px; }
    .time-badge { color: #FF9800; font-weight: bold; font-size: 1.05em; }
    .pseudo-text { color: #FFFFFF; font-weight: bold; font-size: 1.0em; }
    .details-text { color: #CCCCCC; font-size: 0.85em; }
    </style>
    """, unsafe_allow_html=True)

# --- GESTION MULTI-LANGUE ---
if "lang" not in st.session_state:
    st.session_state.lang = "fr"

def _(fr_text, en_text):
    return fr_text if st.session_state.lang == "fr" else en_text

# --- CONNEXION CONFIGURATION SUPABASE ---
SUPABASE_URL = "https://rjexlotreipfjbgpfcnt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqZXhsb3RyZWlwZmpiZ3BmY250Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTt4MDUyOTkyNywiZXhwIjoyMDk2MTA1OTI3fQ.0vMnopwPCMQaOmzCPNcdc4HLqr1d1npoqL3xXNnxGQ8"

@st.cache_resource
def init_supabase():
    try: return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"🔑 Erreur Supabase : {e}")
        st.stop()

supabase = init_supabase()
URL_WEBHOOK_WHATSAPP = st.secrets.get("URL_WEBHOOK_WHATSAPP", "")

@st.cache_data(ttl=2)
def obtenir_toutes_les_tables():
    try:
        rep = supabase.table("profils").select("groupe").execute()
        if rep.data:
            return sorted(list(set([p['groupe'] for p in rep.data if p.get('groupe')])))
        return ["Haggis et les cafards"]
    except:
        return ["Haggis et les cafards"]

# --- INITIALISATION DE NAVIGATION ---
if "current_view" not in st.session_state: st.session_state.current_view = "bar"
if "groupe_selectionne" not in st.session_state: st.session_state.groupe_selectionne = ""

# Intercepter une table partagée via le QR Code (paramètre URL)
query_params = st.query_params
if "table" in query_params and st.session_state.groupe_selectionne == "":
    st.session_state.groupe_selectionne = query_params["table"]
    st.session_state.current_view = "table"

tables_existantes = obtenir_toutes_les_tables()
if "Haggis et les cafards" not in tables_existantes: tables_existantes.insert(0, "Haggis et les cafards")

# ==========================================
# BANDEAU SUPÉRIEUR (TITRE & DRAPEAUX)
# ==========================================
col_titre, col_fr, col_en = st.columns([8, 1, 1])
with col_titre:
    st.title(_("🍹 Suivi de soirée - V4.0", "🍹 Party Tracker - V4.0"))
with col_fr:
    if st.button("🇫🇷", use_container_width=True): 
        st.session_state.lang = "fr"
        st.rerun()
with col_en:
    if st.button("🇬🇧", use_container_width=True): 
        st.session_state.lang = "en"
        st.rerun()

# ==========================================
# VUE 1 : LA SALLE DU BAR (SELECTION TABLE)
# ==========================================
if st.session_state.current_view == "bar":
    st.markdown(_("### 🍻 Choisissez votre table", "### 🍻 Choose your table"))
    
    cols = st.columns(3)
    for idx, table_name in enumerate(tables_existantes):
        with cols[idx % 3]:
            if st.button(f"🪑 {table_name}", use_container_width=True, key=f"btn_table_{table_name}"):
                st.session_state.groupe_selectionne = table_name
                st.session_state.current_view = "table"
                st.query_params["table"] = table_name
                st.rerun()
                
    st.markdown("---")
    st.markdown(_("#### ➕ Ou créez une nouvelle table", "#### ➕ Or open a new table"))
    col_nom, col_btn = st.columns([3, 1])
    with col_nom:
        nom_nouvelle_table = st.text_input(_("Nom de la table :", "Table name :"), label_visibility="collapsed", placeholder="Ex: Sopemea")
    with col_btn:
        if st.button(_("Créer la table 🚀", "Create table 🚀"), use_container_width=True):
            if nom_nouvelle_table.strip():
                st.session_state.groupe_selectionne = nom_nouvelle_table.strip()
                st.session_state.current_view = "table"
                st.query_params["table"] = nom_nouvelle_table.strip()
                st.rerun()

# ==========================================
# VUE 2 : AUTOUR DE LA TABLE (LES 9 RUBRIQUES)
# ==========================================
else:
    groupe_actif = st.session_state.groupe_selectionne
    
    col_back, col_name, _ = st.columns([2, 6, 2])
    with col_back:
        if st.button(_("🔙 Retour au bar", "🔙 Back to the bar"), use_container_width=True):
            st.session_state.current_view = "bar"
            st.query_params.clear()
            st.rerun()
    with col_name:
        st.markdown(f"<h4 style='text-align: center; color: white;'>Table : <span style='color: #FF9800;'>{groupe_actif}</span></h4>", unsafe_allow_html=True)

    # --- CHARGEMENT DES BASES DE DONNÉES ---
    @st.cache_data(ttl=2)
    def charger_profils(groupe):
        try:
            rep = supabase.table("profils").select("*").eq("groupe", groupe).execute()
            return {p['pseudo']: {"sexe": p['sexe'], "poids": p['poids'], "id": p['id']} for p in rep.data} if rep.data else {}
        except: return {}

    profils = charger_profils(groupe_actif)

    if not profils and groupe_actif == "Haggis et les cafards":
        defauts = [
            {"pseudo": "Lolo", "sexe": "Homme", "poids": 75, "groupe": groupe_actif},
            {"pseudo": "Poums", "sexe": "Homme", "poids": 75, "groupe": groupe_actif},
            {"pseudo": "Nico", "sexe": "Homme", "poids": 75, "groupe": groupe_actif},
            {"pseudo": "Duj", "sexe": "Homme", "poids": 75, "groupe": groupe_actif}
        ]
        supabase.table("profils").insert(defauts).execute()
        st.cache_data.clear()
        profils = charger_profils(groupe_actif)

    @st.cache_data(ttl=2)
    def charger_donnees(groupe):
        try:
            boissons = supabase.table("drinks").select("*").eq("groupe", groupe).order("created_at", desc=False).execute()
            repas = supabase.table("meals").select("*").eq("groupe", groupe).order("created_at", desc=False).execute()
            return (boissons.data or []), (repas.data or [])
        except: return [], []

    boissons_nuageuses, repas_nuage = charger_donnees(groupe_actif)

    # --- CALCULS PHYSIOLOGIQUES INTÉGRAUX ---
    maintenant = pd.Timestamp.now(tz='Europe/Paris')
    maintenant_arrondi = maintenant.floor('5min')
    debut_calcul = maintenant_arrondi - pd.Timedelta(hours=24)
    fin_calcul = maintenant_arrondi + pd.Timedelta(hours=12)
    axe_temps = pd.date_range(start=debut_calcul, end=fin_calcul, freq='5min', tz='Europe/Paris')
    PENTE_ELIMINATION_5MIN = 0.15 * (5 / 60)

    def clean_tz(series):
        dt = pd.to_datetime(series, errors='coerce', format='mixed', utc=True)
        return dt.dt.tz_convert('Europe/Paris')

    df_verres = pd.DataFrame(boissons_nuageuses) if boissons_nuageuses else pd.DataFrame(columns=['id', 'pseudo', 'boisson', 'alcool_g', 'created_at', 'groupe'])
    if not df_verres.empty: df_verres['created_at'] = clean_tz(df_verres['created_at'])

    df_repas = pd.DataFrame(repas_nuage) if repas_nuage else pd.DataFrame(columns=['id', 'pseudo', 'created_at', 'groupe', 'type'])
    if not df_repas.empty: df_repas['created_at'] = clean_tz(df_repas['created_at'])

    df_graphique = pd.DataFrame(index=axe_temps)
    idx_maintenant = df_graphique.index.get_indexer([maintenant_arrondi], method='nearest')[0]

    stats_joueurs = {}

    for nom, info in profils.items():
        poids = info["poids"]
        coef_diffusion = 0.7 if info["sexe"] == "Homme" else 0.6
        taux_liste = []
        
        verres_perso = df_verres[df_verres['pseudo'] == nom] if not df_verres.empty else pd.DataFrame()
        repas_perso = df_repas[df_repas['pseudo'] == nom] if not df_repas.empty else pd.DataFrame()

        t_start_sim = debut_calcul
        if not verres_perso.empty:
            premier_verre = verres_perso['created_at'].min().floor('5min')
            if premier_verre < t_start_sim: t_start_sim = premier_verre
                
        axe_complet = pd.date_range(start=t_start_sim, end=fin_calcul, freq='5min', tz='Europe/Paris')
        apports_globaux = pd.Series(0.0, index=axe_complet)
        
        if not verres_perso.empty:
            for _, verre in verres_perso.iterrows():
                t_drink = verre['created_at']
                a_mange, a_grignote = False, False
                
                if not repas_perso.empty:
                    repas_complets = repas_perso[repas_perso['type'] == 'Repas']
                    grignotages = repas_perso[repas_perso['type'] == 'Grignotage']
                    if not repas_complets.empty:
                        a_mange = not repas_complets[(repas_complets['created_at'] >= t_drink - pd.Timedelta(hours=3)) & (repas_complets['created_at'] <= t_drink + pd.Timedelta(hours=1))].empty
                    if not grignotages.empty:
                        a_grignote = not grignotages[(grignotages['created_at'] >= t_drink - pd.Timedelta(hours=1.5)) & (grignotages['created_at'] <= t_drink + pd.Timedelta(hours=0.5))].empty
                    
                t_pic, bio_factor = (1.0, 0.8) if a_mange else ((0.75, 0.9) if a_grignote else (0.5, 1.0))
                c_max_theo = (verre['alcool_g'] / (poids * coef_diffusion)) * bio_factor
                
                t_start_search = t_drink.floor('5min')
                for steps in range(0, int(t_pic * 12) + 2):
                    t = t_start_search + pd.Timedelta(minutes=5 * steps)
                    if t in apports_globaux.index:
                        diff_heures_debut = (t - pd.Timedelta(minutes=5) - t_drink).total_seconds() / 3600.0
                        diff_heures_fin = (t - t_drink).total_seconds() / 3600.0
                        if diff_heures_fin > 0 and diff_heures_debut < t_pic:
                            apport_5min = c_max_theo * ((min(t_pic, diff_heures_fin) - max(0.0, diff_heures_debut)) / t_pic)
                            apports_globaux.loc[t] += max(0.0, apport_5min)

        taux_courant = 0.0
        taux_dict = {}
        for t in axe_complet:
            apport_5min = apports_globaux.loc[t]
            taux_courant += apport_5min
            if apport_5min == 0 and taux_courant > 0: taux_courant -= PENTE_ELIMINATION_5MIN
            taux_courant = max(0.0, taux_courant)
            taux_dict[t] = taux_courant
            
        for t in axe_temps: taux_liste.append(taux_dict.get(t, 0.0))
        df_graphique[nom] = taux_liste
        max_historique = max(taux_dict.values()) if taux_dict else 0.0
        stats_joueurs[nom] = {"max_ever": max_historique, "total_verres": len(verres_perso)}

    record_absolu_groupe = max([s['max_ever'] for s in stats_joueurs.values()]) if stats_joueurs else 0.0

    def attribuer_badge(taux):
        if taux >= 2.0: return "🧟‍♂️"
        elif taux >= 1.5: return "🏴‍☠️"
        elif taux >= 1.0: return "🥳"
        elif taux >= 0.5: return "🍺"
        elif taux > 0.01: return "👼"
        else: return "🚰"

    # --- AFFICHAGE INTERACTIF DE LA TABLE RONDE (PLOTLY) ---
    if profils:
        fig_table = go.Figure()
        fig_table.add_shape(type="circle", x0=-0.8, y0=-0.8, x1=0.8, y1=0.8, fillcolor="#1A1A1A", line_color="#FF9800", line_width=3)
        fig_table.add_annotation(x=0, y=0, text=groupe_actif, showarrow=False, font=dict(color="#FF9800", size=13, family="Arial"))
        
        angles = np.linspace(0, 2*np.pi, len(profils), endpoint=False)
        for idx, (nom, angle) in enumerate(zip(profils.keys(), angles)):
            cx, cy = 1.15 * np.cos(angle), 1.15 * np.sin(angle)
            tx, ty = 1.65 * np.cos(angle), 1.65 * np.sin(angle)
            
            taux_actuel = df_graphique[nom].iloc[idx_maintenant] if nom in df_graphique.columns else 0.0
            badge = attribuer_badge(taux_actuel)
            couronne = "👑" if (stats_joueurs[nom]['max_ever'] == record_absolu_groupe and record_absolu_groupe > 0.01) else ""
            
            fig_table.add_shape(type="circle", x0=cx-0.18, y0=cy-0.18, x1=cx+0.18, y1=cy+0.18, fillcolor=COULEURS_JOUEURS[idx % len(COULEURS_JOUEURS)], line_color="#FFFFFF", line_width=1.5)
            fig_table.add_annotation(x=tx, y=ty, text=f"{couronne}{nom} {badge}", showarrow=False, font=dict(color="#FFFFFF", size=11, family="Arial"))

        fig_table.update_layout(
            xaxis=dict(visible=False, range=[-2.1, 2.1], fixedrange=True), 
            yaxis=dict(visible=False, range=[-2.1, 2.1], fixedrange=True), 
            width=320, height=320, margin=dict(l=0, r=0, t=10, b=10), 
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", 
            showlegend=False, dragmode=False
        )
        st.plotly_chart(fig_table, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True})

    # ==========================================
    # LES 9 RUBRIQUES DE L'APPLICATION
    # ==========================================

    # --- 1. DÉCLARER UNE CONSOMMATION ---
    with st.expander(_("🍹 1. Déclarer une consommation", "🍹 1. Log a drink"), expanded=False):
        if profils:
            choix_type = st.radio(_("Type d'entrée :", "Entry type :"), [_("Un verre de l'amitié 🍺", "A friendly drink 🍺"), _("Un repas complet 🍽️", "A full meal 🍽️"), _("Grignotage (Apéro) 🥨", "Snacks 🥨")], horizontal=True)
            oubli = st.checkbox(_("🕰️ Enregistrement rétroactif (modifier l'heure)", "🕰️ Backdated entry (change time)"))
            maintenant_local = pd.Timestamp.now(tz='Europe/Paris')
            
            if oubli:
                heure_perso = st.time_input(_("Heure de la consommation :", "Time :"), value=maintenant_local.time())
                dt_combine = datetime.datetime.combine(maintenant_local.date(), heure_perso)
                moment_actuel = pd.Timestamp(dt_combine).tz_localize('Europe/Paris').isoformat()
            else:
                moment_actuel = maintenant_local.isoformat()

            if "verre" in choix_type.lower() or "drink" in choix_type.lower():
                c1, c2, c3 = st.columns(3)
                with c1: Qui = st.selectbox(_("Qui consomme ?", "Who is drinking?"), list(profils.keys()), key="select_qui_drink")
                with c2: Volume_cl = st.number_input(_("Volume (cl)", "Volume (cl)"), 1, 200, 25)
                with c3: Degre_Alcool = st.number_input(_("Degré (%)", "BAC (%)"), 0.5, 90.0, 5.0, 0.5)
                if st.button(_("Enregistrer le verre 💾", "Save drink 💾")):
                    alcool_g = float((Volume_cl * 10) * (Degre_Alcool / 100) * 0.8)
                    supabase.table("drinks").insert({"pseudo": Qui, "boisson": f"{Volume_cl}cl @ {Degre_Alcool}%", "alcool_g": alcool_g, "created_at": moment_actuel, "groupe": groupe_actif}).execute()
                    st.cache_data.clear()
                    st.rerun()
            else:
                type_repas = "Repas" if "repas" in choix_type.lower() or "meal" in choix_type.lower() else "Grignotage"
                Qui = st.selectbox(_("Qui a mangé ?", "Who ate?"), list(profils.keys()), key="select_qui_eat")
                if st.button(_("Enregistrer le repas 💾", "Save meal 💾")):
                    supabase.table("meals").insert({"pseudo": Qui, "created_at": moment_actuel, "groupe": groupe_actif, "type": type_repas}).execute()
                    st.cache_data.clear()
                    st.rerun()

    # --- 2. TABLEAU DE BORD INSTANTANÉ ---
    with st.expander(_("📍 2. Tableau de bord instantané", "📍 2. Instant Dashboard"), expanded=False):
        if profils:
            cols_dashboard = st.columns(len(profils))
            texte_whatsapp = f"🍹 *Point Suivi de Soirée — Table {groupe_actif}* 🍻\n\n"
            for i, nom in enumerate(profils.keys()):
                taux_actuel = df_graphique[nom].iloc[idx_maintenant] if nom in df_graphique.columns else 0.0
                donnees_futures = df_graphique[nom].loc[maintenant_arrondi:] if nom in df_graphique.columns else pd.Series()
                taux_max_futur = donnees_futures.max() if not donnees_futures.empty else 0.0
                
                retour_zero = donnees_futures[donnees_futures <= 0.01].index[0].strftime("%H:%M") if not donnees_futures[donnees_futures <= 0.01].empty else "Demain"
                heure_conduite = donnees_futures.loc[donnees_futures.idxmax():][donnees_futures < 0.5].index[0].strftime("%H:%M") if not donnees_futures.loc[donnees_futures.idxmax():][donnees_futures < 0.5].empty else "Trop tard 🛑"
                if taux_max_futur < 0.5: heure_conduite = "Maintenant ✅"

                with cols_dashboard[i % len(cols_dashboard)]:
                    st.markdown(f"**{nom} {attribuer_badge(taux_actuel)}**")
                    st.metric(label="Actuel", value=f"{taux_actuel:.2f} g/L")
                    st.markdown(f"<span style='font-size:0.85em;'>🔮 Max: {taux_max_futur:.2f}g/L<br>🚗 Conduite: {heure_conduite}<br>💧 Sobre: {retour_zero}</span>", unsafe_allow_html=True)
                texte_whatsapp += f"• {nom} : {taux_actuel:.2f} g/L (Max prévu: {taux_max_futur:.2f} g/L)\n"
            
            st.link_button(_("📲 Partager le bilan sur WhatsApp", "📲 Share on WhatsApp"), f"https://api.whatsapp.com/send?text={urllib.parse.quote(texte_whatsapp)}")

    # --- 3. COURBES (ÉVOLUTION) ---
    with st.expander(_("📊 3. Courbes (Évolution)", "📊 3. Curves (Evolution)"), expanded=False):
        if not df_verres.empty and profils:
            fig = go.Figure()
            for i, nom in enumerate(profils.keys()):
                if nom in df_graphique.columns:
                    fig.add_trace(go.Scatter(x=df_graphique.index, y=df_graphique[nom], mode='lines', name=nom, line=dict(width=2.5, color=COULEURS_JOUEURS[i % len(COULEURS_JOUEURS)])))
            fig.add_vline(x=maintenant_arrondi, line_width=1.5, line_dash="dash", line_color="orange")
            fig.add_hline(y=0.5, line_width=1, line_dash="dot", line_color="red")
            fig.update_layout(template="plotly_dark", height=250, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- 4. HISTORIQUE DE LA TABLE ---
    with st.expander(_("📋 4. Historique de la table", "📋 4. Table History"), expanded=False):
        if not df_verres.empty or not df_repas.empty:
            df_verres_rec = df_verres.copy() if not df_verres.empty else pd.DataFrame(columns=['id', 'pseudo', 'created_at', 'boisson'])
            df_verres_rec['type_ev'], df_verres_rec['icon'] = 'drink', '🍹'
            df_verres_rec['desc'] = df_verres_rec['boisson']
            
            df_repas_rec = df_repas.copy() if not df_repas.empty else pd.DataFrame(columns=['id', 'pseudo', 'created_at', 'type'])
            df_repas_rec['type_ev'], df_repas_rec['icon'] = 'meal', df_repas_rec['type'].apply(lambda x: '🥨' if x == 'Grignotage' else '🍽️')
            df_repas_rec['desc'] = df_repas_rec['type']

            df_tl = pd.concat([df_verres_rec[['id', 'pseudo', 'created_at', 'icon', 'desc', 'type_ev']], df_repas_rec[['id', 'pseudo', 'created_at', 'icon', 'desc', 'type_ev']]]).sort_values(by='created_at', ascending=False)
            for _, r in df_tl.iterrows():
                c_time, c_text, c_del = st.columns([1.5, 5, 1])
                c_time.markdown(f"<span class='time-badge'>{r['created_at'].strftime('%H:%M')}</span>", unsafe_allow_html=True)
                c_text.markdown(f"**{r['pseudo']}** {r['icon']} {r['desc']}")
                if c_del.button("❌", key=f"del_{r['type_ev']}_{r['id']}"):
                    supabase.table("drinks" if r['type_ev']=='drink' else "meals").delete().eq("id", r['id']).execute()
                    st.cache_data.clear()
                    st.rerun()

    # --- 5. PALMARÈS & RECORSMEN ---
    with st.expander(_("🏆 5. Palmarès & Sommets de la soirée", "🏆 5. Table Records"), expanded=False):
        if stats_joueurs:
            st.markdown(_("##### 🚀 Plus hauts taux atteints ce soir :", "##### 🚀 Highest levels hit tonight :"))
            for nom, stat in stats_joueurs.items():
                couronne = "👑" if (stat['max_ever'] == record_absolu_groupe and record_absolu_groupe > 0.01) else "📊"
                st.write(f"{couronne} **{nom}** : {stat['max_ever']:.2f} g/L — Total : {stat['total_verres']} verre(s)")

    # --- 6. PARTAGER LA TABLE (QR CODE SYNCHRONISÉ) ---
    with st.expander(_("📲 6. Inviter des amis (QR Code)", "📲 6. Invite Friends (QR Code)"), expanded=False):
        url_brute = f"https://partytracker.streamlit.app/?table={urllib.parse.quote(groupe_actif)}"
        st.write(_("Faites scanner ce code pour ajouter un convive directement à cette table :", "Scan this QR code to join this table directly:"))
        
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(url_brute)
        qr.make(fit=True)
        img_buf = io.BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(img_buf, format="PNG")
        st.image(img_buf.getvalue(), width=140)
        st.caption(f"Lien : {url_brute}")

    # --- 7. GÉRER LES CHAISES (ÉQUIPE) ---
    with st.expander(_("⚙️ 7. Gérer les chaises (Équipe)", "⚙️ 7. Manage Seats (Team)"), expanded=False):
        t_poids, t_add, t_del = st.tabs([_("✏️ Poids", "✏️ Weights"), _("➕ Ajouter", "➕ Add"), _("🗑️ Retirer", "🗑️ Remove")])
        with t_poids:
            with st.form("f_poids"):
                nv_poids = {}
                for nom, info in profils.items():
                    nv_poids[nom] = st.number_input(f"{nom} (kg)", 40, 150, info["poids"])
                if st.form_submit_button(_("Enregistrer", "Save")):
                    for nom in profils.keys():
                        supabase.table("profils").update({"poids": nv_poids[nom]}).eq("id", profils[nom]["id"]).execute()
                    st.cache_data.clear()
                    st.rerun()
        with t_add:
            c_n, c_s, c_p = st.columns(3)
            n_n = c_n.text_input("Nom")
            n_s = c_s.selectbox("Sexe", ["Homme", "Femme"])
            n_p = c_p.number_input("Poids", 40, 150, 70)
            if st.button(_("Placer sur une chaise", "Seat user")):
                if n_n and n_n not in profils:
                    supabase.table("profils").insert({"pseudo": n_n, "sexe": n_s, "poids": n_p, "groupe": groupe_actif}).execute()
                    st.cache_data.clear()
                    st.rerun()
        with t_del:
            qui_del = st.selectbox(_("Qui doit partir ?", "Who leaves?"), list(profils.keys()))
            if st.button(_("Retirer la chaise ❌", "Remove seat ❌")):
                supabase.table("profils").delete().eq("id", profils[qui_del]["id"]).execute()
                st.cache_data.clear()
                st.rerun()

    # --- 8. ZONE DE DANGER & REINITIALISATION (RAZ) ---
    with st.expander(_("🚨 8. Zone de Danger & RAZ Table", "🚨 8. Danger Zone & Reset"), expanded=False):
        st.write(_("⚠️ Attention : La remise à zéro supprimera définitivement l'historique de cette table.", "⚠️ Danger: This will wipe all data for this current table."))
        if st.button(_("💥 Remise À Zéro (RAZ) de la Table", "💥 Hard Reset (RAZ) Table")):
            supabase.table("drinks").delete().eq("groupe", groupe_actif).execute()
            supabase.table("meals").delete().eq("groupe", groupe_actif).execute()
            st.cache_data.clear()
            st.success(_("Table réinitialisée !", "Table cleared!"))
            st.rerun()

    # --- BOUTON DE RAFRAÎCHISSEMENT GENERAL ---
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(_("🔄 Mettre à jour les données de la table", "🔄 Refresh data"), use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # --- 9. FAQ & LÉGENDE INTEGRALE ---
    with st.expander(_("❓ 9. FAQ & Avertissements Importants", "❓ 9. FAQ & Important Warnings"), expanded=True):
        st.warning(_("⚠️ **AVERTISSEMENT LÉGAL** : Outil de simulation théorique basé sur la formule mathématique de Widmark étendue. Il ne remplace en aucun cas un éthylotest réel. Ne prenez jamais le volant après avoir consommé de l'alcool.", "⚠️ **LEGAL WARNING**: Theoretical simulation based on the extended Widmark formula. Does not replace a physical breathalyzer. Never drive after drinking alcohol."))
        
        st.markdown(_("""
        ### 📊 Signification complète des statuts & émojis
        * 🧟‍♂️ **Zombie** : Taux très critique (>= 2.0 g/L). Risques physiologiques majeurs, repos obligatoire.
        * 🏴‍☠️ **Pirate** : Taux élevé (>= 1.5 g/L). Ivresse prononcée.
        * 🥳 **Fêtard** : État d'ivresse classique (>= 1.0 g/L).
        * 🍺 **Joyeux** : Seuil légal de conduite dépassé ou approché (>= 0.5 g/L).
        * 👼 **Innocent** : Alcool en cours d'assimilation ou de descente (> 0.01 g/L).
        * 🚰 **À jeun** : Parfaitement sobre (0.0 g/L).
        * 👑 **Couronne** : Attribuée automatiquement au recordman (plus haut taux atteint) de la table active.

        ### 🧮 Comment fonctionne le calcul ?
        L'application modélise la courbe d'alcoolémie de manière dynamique :
        1. **La diffusion (Montée)** : L'alcool n'atteint pas son maximum immédiatement. Le pic de concentration est atteint en **30 minutes** à jeun, **45 minutes** avec grignotage (Apéro), et **60 minutes** après un repas complet. Le repas réduit également la biodisponibilité globale de l'alcool de 20%.
        2. **L'élimination (Descente)** : Le corps élimine de manière linéaire à un rythme moyen de **0,15 g/L par heure** (ramené à des pas de calcul précis de 5 minutes).
        """, """
        ### 📊 Symbols & Status Legend
        * 🧟‍♂️ **Zombie** : Critical BAC (>= 2.0 g/L). High physiological risk, sleep required.
        * 🏴‍☠️ **Pirate** : High BAC (>= 1.5 g/L). High level of drunkenness.
        * 🥳 **Partier** : Classic drunk state (>= 1.0 g/L).
        * 🍺 **Happy** : Legal driving limit reached or exceeded (>= 0.5 g/L).
        * 👼 **Innocent** : Alcohol currently processing (> 0.01 g/L).
        * 🚰 **Sober** : Completely clean (0.0 g/L).
        * 👑 **Crown** : Automatically awarded to the highest record holder of the live table.

        ### 🧮 How does the engine compute?
        The application updates a real-time metabolic trace:
        1. **Absorption (Ramp-up)**: Peak concentration is reached in **30 mins** on an empty stomach, **45 mins** with snacks, and **60 mins** after a full meal. Meals also lower total bioavailability by 20%.
        2. **Elimination (Cool-down)**: The liver processes alcohol linearly at an average rate of **0.15 g/L per hour**.
        """))
