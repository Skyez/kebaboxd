import streamlit as st
import pandas as pd
import folium
from folium import Element
from streamlit_folium import st_folium
import datetime
import json
import os

# Configuration de la page en mode "wide"
st.set_page_config(page_title="Kebabboxd", page_icon="🥙", layout="wide")

# Gestion de la navigation via les paramètres URL
if "p" in st.query_params:
    p_val = st.query_params["p"]
    if p_val == "carte": st.session_state.nav_page = "🗺️ Carte"
    elif p_val == "ajouter": st.session_state.nav_page = "🥙 Ajouter"
    elif p_val == "diary": st.session_state.nav_page = "📖 Diary"
    elif p_val == "stats": st.session_state.nav_page = "📊 Stats"

if 'nav_page' not in st.session_state:
    st.session_state.nav_page = "🗺️ Carte"

current_page = st.session_state.nav_page

# --- PERSONNALISATION ESTHÉTIQUE & CSS CONDITIONNEL ---
if current_page == "🗺️ Carte":
    st.markdown("""
        <style>
        /* Bloquer le scroll uniquement sur la page carte */
        html, body, [data-testid="stAppViewContainer"], .stApp {
            overflow: hidden !important;
            height: 100vh !important;
            background-color: #14181c;
            color: #9ab;
        }
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0px !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
            max-height: 100vh !important;
            overflow: hidden !important;
        }
        div[data-testid="stVerticalBlock"] > div:first-child {
            margin-top: -1rem !important;
        }
        header { visibility: hidden; height: 0px !important; }
        [data-testid="stSidebar"] { display: none; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        /* Autoriser le scroll sur les pages textuelles */
        html, body, [data-testid="stAppViewContainer"], .stApp {
            background-color: #14181c;
            color: #9ab;
            overflow-x: hidden !important;
            overflow-y: auto !important;
        }
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 80px !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
        }
        div[data-testid="stVerticalBlock"] > div:first-child {
            margin-top: -1rem !important;
        }
        header { visibility: hidden; height: 0px !important; }
        [data-testid="stSidebar"] { display: none; }

        /* Style des formulaires */
        .stForm {
            background-color: #1c2228;
            padding: 25px;
            border-radius: 12px;
            border: 1px solid #2c3440;
        }

        /* Amélioration du bouton d'enregistrement (submit) */
        [data-testid="stFormSubmitButton"] button {
            background-color: #00e054 !important;
            color: #14181c !important;
            font-weight: bold !important;
            font-size: 16px !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 24px !important;
            transition: all 0.2s ease !important;
            width: 100%;
        }
        [data-testid="stFormSubmitButton"] button:hover {
            background-color: #00c048 !important;
            transform: scale(1.02);
        }
        </style>
    """, unsafe_allow_html=True)

# CSS commun pour la barre de navigation flottante et le titre
st.markdown("""
    <style>
    .fixed-nav-bar {
        position: fixed;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 999999;
        background-color: rgba(28, 34, 40, 0.92);
        backdrop-filter: blur(10px);
        padding: 6px 14px;
        border-radius: 40px;
        border: 1px solid #2c3440;
        display: flex;
        align-items: center;
        gap: 10px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.6);
    }
    .nav-btn {
        background-color: transparent !important;
        color: #fff !important;
        font-size: 20px !important;
        text-decoration: none !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        width: 42px;
        height: 42px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: background-color 0.2s ease, transform 0.1s ease;
    }
    .nav-btn:hover, .nav-btn:focus, .nav-btn:active {
        background-color: #00e054 !important;
        color: #14181c !important;
        text-decoration: none !important;
        transform: scale(1.05);
    }
    </style>
""", unsafe_allow_html=True)

DATA_FILE = "user_data.json"

def load_base_kebabs():
    try:
        df_csv = pd.read_csv('kebabs.csv')
        kebabs_list = []
        for _, row in df_csv.iterrows():
            try:
                # Nettoyage et découpage sécurisé des coordonnées GPS
                gps_str = str(row['gps']).strip()
                parts = gps_str.split(',')
                lat, lon = float(parts[0].strip()), float(parts[1].strip())
            except Exception:
                lat, lon = 49.4431, 1.0993  # Valeur de repli (Rouen) en cas de format invalide
            
            kebabs_list.append({
                'nom': str(row['name']).strip(), 
                'adresse': str(row['address']).strip(), 
                'lat': lat, 
                'lon': lon
            })
        return pd.DataFrame(kebabs_list)
    except Exception:
        return pd.DataFrame([{'nom': 'Atlas Royal Rouen', 'adresse': 'Rouen', 'lat': 49.4377, 'lon': 1.0836}])

# Chargement direct (sans cache strict pour prendre en compte les modifs de kebabs.csv immédiatement)
st.session_state.kebabs_df = load_base_kebabs()

if 'entries' not in st.session_state:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                for i, item in enumerate(loaded):
                    if item and not item.get('id'):
                        item['id'] = f"generated_id_{i}_{datetime.datetime.now().timestamp()}"
                st.session_state.entries = loaded
        except:
            st.session_state.entries = []
    else:
        st.session_state.entries = []

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.entries, f, ensure_ascii=False, indent=4)

# --- TITRE FLOTTANT GLOBAL ---
st.markdown('''
    <div style="position: fixed; 
        top: 25px; right: 15px; z-index: 100000; 
        background-color: rgba(20, 24, 28, 0.9); 
        padding: 10px 20px; 
        border-radius: 10px; 
        border: 1px solid #2c3440;
        color: #ffffff; 
        font-family: -apple-system, sans-serif;
        font-size: 20px;
        font-weight: bold;
        box-shadow: 0 4px 10px rgba(0,0,0,0.4);">
        🥙 Kebaboxd
    </div>
''', unsafe_allow_html=True)

# --- PAGE 1 : CARTE ---
if current_page == "🗺️ Carte":
    visités_noms = set(e.get('nom_kebab') for e in st.session_state.entries if e and e.get('nom_kebab'))
    
    mapbox_token = ""
    try:
        mapbox_token = st.secrets.get("MAPBOX_API_KEY", "clé_par_défaut")
    except Exception:
        mapbox_token = "clé_par_défaut"

    m = folium.Map(
        location=[49.4431, 1.0993],
        zoom_start=13,
        tiles=None
    )

    folium.TileLayer(
        tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={mapbox_token}",
        attr='&copy; OpenStreetMap &copy; CARTO',
        subdomains="abcd",
        name="CARTO Dark Matter",
        max_zoom=20
    ).add_to(m)
    
    for _, row in st.session_state.kebabs_df.iterrows():
        nom = row['nom']
        est_visite = nom in visités_noms
        color = 'green' if est_visite else 'red'
        
        popup_text = f"<b>{nom}</b><br>{'Déjà visité' if est_visite else 'À tester'}"
        
        folium.Marker(
            [row['lat'], row['lon']],
            popup=popup_text,
            tooltip=nom,
            icon=folium.Icon(color=color, icon="cutlery", prefix="fa")
        ).add_to(m)
        
    st_folium(m, width=None, height=850, use_container_width=True)

# Pour les pages de texte, on utilise une colonne centrale
else:
    st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
    
    _, center_col, _ = st.columns([0.15, 0.7, 0.15])
    
    with center_col:
        # --- PAGE 2 : AJOUTER ---
        if current_page == "🥙 Ajouter":
            st.markdown('<h2 style="margin-bottom: 25px;">🥙 Ajouter un repas miraculeux</h2>', unsafe_allow_html=True)
            
            choix_kebab = st.selectbox(
                "", 
                st.session_state.kebabs_df['nom'].tolist(),
                index=None,
                placeholder="Tapez le nom d'un lieu de culte..."
            )
            
            if choix_kebab:
                kebab_info = st.session_state.kebabs_df[st.session_state.kebabs_df['nom'] == choix_kebab].iloc[0]
                
                try:
                    mapbox_token = st.secrets.get("MAPBOX_API_KEY", "clé_par_défaut")
                except Exception:
                    mapbox_token = "clé_par_défaut"

                m_mini = folium.Map(location=[kebab_info['lat'], kebab_info['lon']], zoom_start=15, tiles=None)
                folium.TileLayer(
                    tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={mapbox_token}",
                    attr='&copy; CARTO',
                    subdomains="abcd",
                    max_zoom=20
                ).add_to(m_mini)
                
                folium.Marker(
                    [kebab_info['lat'], kebab_info['lon']],
                    tooltip=choix_kebab,
                    icon=folium.Icon(color="green", icon="cutlery", prefix="fa")
                ).add_to(m_mini)
                
                st.markdown("<div style='border-radius: 12px; overflow: hidden; margin-bottom: 20px; border: 1px solid #2c3440;'>", unsafe_allow_html=True)
                st_folium(m_mini, width=None, height=200, use_container_width=True, key=f"minimap_{choix_kebab}")
                st.markdown("</div>", unsafe_allow_html=True)
                
                with st.form("form_add"):
                    simple_visite = st.checkbox("Ne pas ajouter au calendrier ? (Marquer simplement comme visité)")
                    
                    if not simple_visite:
                        date_visite = st.date_input("Date de visite", value=datetime.date.today())
                        note = st.slider("Note (/5) ⭐", 0.0, 5.0, 4.0, 0.5)
                        prix = st.number_input("Prix (€) (Optionnel)", min_value=0.0, max_value=50.0, value=0.0, step=0.5)
                        commentaire = st.text_area("Avis (Optionnel)")
                    else:
                        date_visite = None
                        note = None
                        prix = 0.0
                        commentaire = ""
                    
                    if st.form_submit_button("Enregistrer la visite 🥙"):
                        new_entry = {
                            'id': str(datetime.datetime.now().timestamp()),
                            'nom_kebab': choix_kebab,
                            'date_visite': str(date_visite) if date_visite else None,
                            'note': note,
                            'prix': prix if prix > 0 else None,
                            'commentaire': commentaire if commentaire else None,
                            'simple_visite': simple_visite
                        }
                        st.session_state.entries.append(new_entry)
                        save_data()
                        if simple_visite:
                            st.success(f"{choix_kebab} marqué comme visité !")
                        else:
                            st.success("Visite ajoutée au calendrier !")

        # --- PAGE 3 : DIARY ---
        elif current_page == "📖 Diary":
            st.markdown('<h2 style="margin-bottom: 45px;">📖 La Bible</h2>', unsafe_allow_html=True)
            
            diary_entries = [e for e in st.session_state.entries if e and not e.get('simple_visite')]
            
            if not diary_entries:
                st.info("Magne toi. Ton Maître Kebabier t'attends.")
            else:
                def sort_key(x):
                    d = x.get('date_visite') if x else None
                    if not d:
                        return '1900-01-01'
                    return str(d)

                entries_sorted = sorted(diary_entries, key=sort_key, reverse=True)
                
                for index, entry in enumerate(entries_sorted):
                    entry_id = entry.get('id', f"fallback_{index}")
                    nom_k = entry.get('nom_kebab')
                    note_val = entry.get('note')
                    prix_val = entry.get('prix')
                    
                    k_match = st.session_state.kebabs_df[st.session_state.kebabs_df['nom'] == nom_k]
                    adresse = k_match.iloc[0]['adresse'] if not k_match.empty else ""
                    
                    with st.container():
                        c1, c2, c3 = st.columns([1.5, 3.5, 1])
                        with c1:
                            st.markdown(f"### 📅 {entry.get('date_visite', 'N/A')}")
                            if note_val is not None:
                                st.markdown(f"⭐ **{note_val}** / 5")
                            else:
                                st.markdown("⭐ *Pas de note*")
                            if prix_val:
                                st.caption(f"💶 {prix_val} €")
                        with c2:
                            st.markdown(f"#### 🥙 {nom_k}")
                            st.caption(f"📍 {adresse}")
                            if entry.get('commentaire'):
                                st.markdown(f"> *{entry['commentaire']}*")
                        with c3:
                            if st.button("🗑️", key=f"del_diary_{entry_id}_{index}"):
                                st.session_state.entries = [e for e in st.session_state.entries if e and e.get('id') != entry_id] # syntax check
                                save_data()
                                st.rerun()
                        st.divider()

        # --- PAGE 4 : STATS ---
        elif current_page == "📊 Stats":
            st.markdown('<h2 style="margin-bottom: 40px;">📊 Tes Statistiques</h2>', unsafe_allow_html=True)
            
            if not st.session_state.entries:
                st.info("Tu n'es pas allé voir ton Maître Kebabier depuis longtemps...")
            else:
                total_visites = len(st.session_state.entries)
                
                # Calcul Pokédex (visités uniques / total dans le CSV)
                visités_uniques_set = set(e.get('nom_kebab') for e in st.session_state.entries if e.get('nom_kebab'))
                kebabs_uniques = len(visités_uniques_set)
                total_kebabs_dispos = len(st.session_state.kebabs_df)
                pokedex_str = f"{kebabs_uniques} / {total_kebabs_dispos}"

                noms_visites = [e.get('nom_kebab') for e in st.session_state.entries if e.get('nom_kebab')]
                kebab_prefere = max(set(noms_visites), key=noms_visites.count) if noms_visites else "N/A"
                nb_fois_prefere = noms_visites.count(kebab_prefere) if kebab_prefere != "N/A" else 0
                
                notes = [e.get('note') for e in st.session_state.entries if e.get('note') is not None]
                moyenne_notes = round(sum(notes) / len(notes), 2) if notes else 0.0
                
                prix_list = [e.get('prix') for e in st.session_state.entries if e.get('prix') and e.get('prix') > 0]
                prix_moyen = round(sum(prix_list) / len(prix_list), 2) if prix_list else 0.0

                valid_dates = []
                for e in st.session_state.entries:
                    if e.get('date_visite'):
                        try:
                            parsed_date = datetime.datetime.strptime(e['date_visite'], '%Y-%m-%d').date()
                            valid_dates.append(parsed_date)
                        except:
                            pass
                
                avg_per_week, avg_per_month, kd_ratio = 0.0, 0.0, 0.0
                current_streak, max_streak = 0, 0

                if valid_dates:
                    first_date = min(valid_dates)
                    last_date = datetime.date.today()
                    days_passed = (last_date - first_date).days
                    
                    weeks_passed = max(1, days_passed / 7.0)
                    months_passed = max(1, days_passed / 30.44)
                    
                    avg_per_week = round(len(valid_dates) / weeks_passed, 1)
                    avg_per_month = round(len(valid_dates) / months_passed, 1)
                    kd_ratio = round(len(valid_dates) / max(1, days_passed), 2)
                    
                    def get_monday(d):
                        iso = d.isocalendar()
                        return datetime.date.fromisocalendar(iso.year, iso.week, 1)
                        
                    mondays = sorted(list(set([get_monday(d) for d in valid_dates])))
                    
                    if mondays:
                        max_streak = 1
                        c_streak = 1
                        for i in range(1, len(mondays)):
                            if (mondays[i] - mondays[i-1]).days == 7:
                                c_streak += 1
                            else:
                                c_streak = 1
                            max_streak = max(max_streak, c_streak)
                            
                        this_week_monday = get_monday(datetime.date.today())
                        if (this_week_monday - mondays[-1]).days <= 7:
                            current_streak = 1
                            for i in range(len(mondays)-2, -1, -1):
                                if (mondays[i+1] - mondays[i]).days == 7:
                                    current_streak += 1
                                else:
                                    break

                # Affichage des métriques
                st.markdown("### 🏆 Général")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total de visites", total_visites)
                    st.metric("Pokédex", pokedex_str)  # Remplacement effectué ici
                with col2:
                    st.metric("Note moyenne globale", f"{moyenne_notes} / 5")
                    st.metric("Aumône moyenne", f"{prix_moyen} €" if prix_moyen > 0 else "N/A")
                with col3:
                    st.metric("Safe place", kebab_prefere, f"{nb_fois_prefere} visites" if nb_fois_prefere > 0 else None, delta_color="off")
                
                st.divider()
                st.markdown("### 📈 Rythme & Winstreaks")
                col4, col5, col6, col7 = st.columns(4)
                with col4:
                    st.metric("Moyenne / Semaine", f"{avg_per_week} Kebabs/Sem", f"soit un K/D de {kd_ratio}", delta_color="off")
                with col5:
                    st.metric("Moyenne / Mois", f"{avg_per_month} Kebabs/Mois")
                with col6:
                    st.metric("Winstreak Actuelle 🔥", f"{current_streak} sem.")
                with col7:
                    st.metric("Meilleure Winstreak 👑", f"{max_streak} sem.")

                # Section Graphiques
                if valid_dates:
                    st.divider()
                    st.markdown("### 📊 Tendances")
                    
                    df_stats = pd.DataFrame(valid_dates, columns=['date'])
                    df_stats['date'] = pd.to_datetime(df_stats['date'])
                    
                    jour_labels = ['L', 'M', 'M ', 'J', 'V', 'S', 'D']
                    df_stats['Jour_Num'] = df_stats['date'].dt.dayofweek
                    jour_counts_series = df_stats['Jour_Num'].value_counts()
                    
                    df_jour = pd.DataFrame({
                        'Jour': jour_labels,
                        'Visites': [jour_counts_series.get(i, 0) for i in range(7)]
                    })
                    df_jour['Jour'] = pd.Categorical(df_jour['Jour'], categories=jour_labels, ordered=True)
                    
                    df_stats['Mois'] = df_stats['date'].dt.to_period('M').astype(str)
                    mois_counts = df_stats['Mois'].value_counts().sort_index()
                    
                    c_chart1, c_chart2 = st.columns(2)
                    with c_chart1:
                        st.markdown("**Fréquentation par jour**")
                        st.bar_chart(df_jour, x='Jour', y='Visites', height=250, color="#00e054")
                    with c_chart2:
                        st.markdown("**Évolution mensuelle**")
                        st.line_chart(mois_counts, height=250, color="#00e054")

# --- BARRE DE NAVIGATION FLOTTANTE UNIVERSELLE ---
st.markdown('''
    <div class="fixed-nav-bar">
        <a href="?p=carte" target="_self" class="nav-btn" title="Carte">🗺️</a>
        <a href="?p=ajouter" target="_self" class="nav-btn" title="Ajouter">🥙</a>
        <a href="?p=diary" target="_self" class="nav-btn" title="Diary">📖</a>
        <a href="?p=stats" target="_self" class="nav-btn" title="Stats">📊</a>
    </div>
''', unsafe_allow_html=True)