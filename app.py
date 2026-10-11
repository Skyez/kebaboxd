import datetime
import json
import locale
import os
import random
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from supabase import Client, create_client

try:
  locale.setlocale(locale.LC_ALL, "fr_FR.UTF-8")
except Exception:
  pass

# Configuration de la page en mode "wide"
st.set_page_config(page_title="Kebaboxd", page_icon="🥙", layout="wide")


# --- INITIALISATION SUPABASE (AUTH & DATABASE) ---
@st.cache_resource
def init_supabase():
  try:
    url = st.secrets["SUPABASE_URL"].strip().rstrip("/")
    key = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)
  except Exception:
    return None


supabase = init_supabase()

if "user" not in st.session_state:
  st.session_state.user = None
if "profile" not in st.session_state:
  st.session_state.profile = None

if supabase and not st.session_state.user:
  try:
    session = supabase.auth.get_session()
    if session and session.user:
      st.session_state.user = session.user
      prof = (
          supabase.table("profiles")
          .select("*")
          .eq("id", session.user.id)
          .execute()
      )
      if prof.data:
        st.session_state.profile = prof.data[0]
  except Exception:
    pass


def login(email, password):
  try:
    res = supabase.auth.sign_in_with_password(
        {"email": email, "password": password}
    )
    st.session_state.user = res.user
    prof = (
        supabase.table("profiles").select("*").eq("id", res.user.id).execute()
    )
    if prof.data:
      st.session_state.profile = prof.data[0]
    st.success("Connexion réussie !")
    st.rerun()
  except Exception as err:
    st.error(f"Échec de la connexion : {err}")


def signup(email, password, username):
  try:
    res = supabase.auth.sign_up({"email": email, "password": password})
    if res.user:
      try:
        supabase.table("profiles").insert(
            {"id": res.user.id, "username": username}
        ).execute()
      except Exception:
        pass
      st.success(
          "Compte créé avec succès ! Tu peux maintenant te connecter."
      )
  except Exception as err:
    st.error(f"Erreur d'inscription : {err}")


def logout():
  if supabase:
    try:
      supabase.auth.sign_out()
    except Exception:
      pass
  st.session_state.user = None
  st.session_state.profile = None
  st.rerun()


# --- ÉCRAN DE CONNEXION SI SUPABASE CONFIGURÉ ET NON CONNECTÉ ---
if supabase and not st.session_state.user:
  st.markdown(
      """
        <style>
        html, body, [data-testid="stAppViewContainer"], .stApp {
            background-color: #14181c;
            color: #9ab;
        }
        [data-testid="stHeader"], .stAppHeader, [data-testid="stDecoration"], [data-testid="stToolbar"] { 
            display: none !important; 
            visibility: hidden !important; 
            height: 0px !important; 
        }
        [data-testid="stSidebar"] { display: none; }
        .stForm {
            background-color: #1c2228;
            padding: 25px;
            border-radius: 12px;
            border: 1px solid #2c3440;
        }
        [data-testid="stFormSubmitButton"] button {
            background-color: #00e054 !important;
            color: #14181c !important;
            font-weight: bold !important;
            font-size: 16px !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 24px !important;
            width: 100%;
        }
        </style>
    """,
      unsafe_allow_html=True,
  )

  st.markdown(
      "<h1 style='text-align: center; color: #00e054; margin-top: 50px;'>🥙"
      " Kebaboxd</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #9ab; margin-bottom:"
      " 30px;'>Bienvenue dans le monde sacré du Kebab.</p>",
      unsafe_allow_html=True,
  )

  _, col_auth, _ = st.columns([1, 2, 1])
  with col_auth:
    tab_login, tab_signup = st.tabs(["Connexion", "Créer un compte"])

    with tab_login:
      with st.form("form_login"):
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Se connecter"):
          login(email, password)

    with tab_signup:
      with st.form("form_signup"):
        new_username = st.text_input("Pseudo")
        new_email = st.text_input("Email")
        new_password = st.text_input(
            "Mot de passe (6 car. min)", type="password"
        )
        if st.form_submit_button("Créer mon compte"):
          if new_username and new_email and len(new_password) >= 6:
            signup(new_email, new_password, new_username)
          else:
            st.warning("Veuillez remplir tous les champs correctement.")
  st.stop()


# --- FONCTIONS BASE DE DONNÉES SUPABASE ---
def load_base_kebabs():
  if supabase:
    try:
      res = supabase.table("kebabs").select("*").execute()
      if res.data:
        df = pd.DataFrame(res.data)
        if "name" in df.columns and "nom" not in df.columns:
          df["nom"] = df["name"]
        if "address" in df.columns and "adresse" not in df.columns:
          df["adresse"] = df["address"]
        return df
    except Exception:
      pass

  try:
    df_csv = pd.read_csv("kebabs.csv")
    kebabs_list = []
    for _, row in df_csv.iterrows():
      try:
        gps_str = str(row["gps"]).strip()
        parts = gps_str.split(",")
        lat, lon = float(parts[0].strip()), float(parts[1].strip())
      except Exception:
        lat, lon = 49.4431, 1.0993

      kebabs_list.append({
          "nom": str(row["name"]).strip(),
          "adresse": str(row["address"]).strip(),
          "lat": lat,
          "lon": lon,
      })
    return pd.DataFrame(kebabs_list)
  except Exception:
    return pd.DataFrame([{
        "nom": "Atlas Royal Rouen",
        "adresse": "Rouen",
        "lat": 49.4377,
        "lon": 1.0836,
    }])


def load_user_entries():
  if supabase and st.session_state.user:
    try:
      res = (
          supabase.table("entries")
          .select("*, kebabs(*)")
          .eq("user_id", st.session_state.user.id)
          .execute()
      )
      raw_data = res.data or []
      entries = []
      for item in raw_data:
        k_raw = item.get("kebabs")
        if isinstance(k_raw, list) and len(k_raw) > 0:
          k_data = k_raw[0]
        elif isinstance(k_raw, dict):
          k_data = k_raw
        else:
          k_data = {}

        nom_k = (
            k_data.get("name")
            or k_data.get("nom")
            or "Kebab"
        )
        adresse_k = k_data.get("address") or k_data.get("adresse") or ""

        entries.append({
            "id": item.get("id"),
            "kebab_id": item.get("kebab_id"),
            "nom_kebab": nom_k,
            "adresse": adresse_k,
            "date_visite": item.get("date_visite"),
            "note": item.get("note"),
            "prix": item.get("prix"),
            "commentaire": item.get("commentaire"),
            "simple_visite": item.get("simple_visite", False),
        })
      return entries
    except Exception:
      pass

  data_file = (
      f"user_data_{st.session_state.user.id}.json"
      if st.session_state.user
      else "user_data.json"
  )
  if os.path.exists(data_file):
    try:
      with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return []
  return []


def load_all_kebab_reviews(nom_kebab):
  """Charge l'ensemble des avis de tous les utilisateurs pour un kebab donné en passant par kebab_id."""
  if supabase:
    try:
      k_match = st.session_state.kebabs_df[
          st.session_state.kebabs_df["nom"] == nom_kebab
      ]
      if not k_match.empty and "id" in k_match.columns and pd.notna(k_match.iloc[0]["id"]):
        k_id = int(k_match.iloc[0]["id"])
        res = (
            supabase.table("entries")
            .select("*, profiles(username)")
            .eq("kebab_id", k_id)
            .eq("simple_visite", False)
            .execute()
        )
        raw = res.data or []
        reviews = []
        for r in raw:
          prof = r.get("profiles") or {}
          reviews.append({
              "username": prof.get("username") or "Anonyme",
              "date_visite": r.get("date_visite"),
              "note": r.get("note"),
              "prix": r.get("prix"),
              "commentaire": r.get("commentaire"),
          })
        return reviews
    except Exception:
      pass

  # Fallback local (extraire les entrées de session actuelles)
  local_reviews = []
  for e in st.session_state.entries:
    if e and e.get("nom_kebab") == nom_kebab and not e.get("simple_visite"):
      username = (
          st.session_state.profile.get("username", "Moi")
          if st.session_state.profile
          else "Moi"
      )
      local_reviews.append({
          "username": username,
          "date_visite": e.get("date_visite"),
          "note": e.get("note"),
          "prix": e.get("prix"),
          "commentaire": e.get("commentaire"),
      })
  return local_reviews


def save_user_entry(new_entry):
  if supabase and st.session_state.user:
    try:
      payload = {
          "user_id": st.session_state.user.id,
          "kebab_id": new_entry.get("kebab_id"),
          "date_visite": new_entry.get("date_visite"),
          "note": new_entry.get("note"),
          "prix": new_entry.get("prix"),
          "commentaire": new_entry.get("commentaire"),
          "simple_visite": new_entry.get("simple_visite", False),
      }
      supabase.table("entries").insert(payload).execute()
      return True
    except Exception as e:
      st.error(f"Erreur d'enregistrement en base : {e}")

  data_file = (
      f"user_data_{st.session_state.user.id}.json"
      if st.session_state.user
      else "user_data.json"
  )
  entries = []
  if os.path.exists(data_file):
    try:
      with open(data_file, "r", encoding="utf-8") as f:
        entries = json.load(f)
    except Exception:
      entries = []
  entries.append(new_entry)
  with open(data_file, "w", encoding="utf-8") as f:
    json.dump(entries, f, ensure_ascii=False, indent=4)
  return True


def delete_user_entry(entry_id):
  if supabase and st.session_state.user:
    try:
      supabase.table("entries").delete().eq("id", entry_id).execute()
      return True
    except Exception as e:
      st.error(f"Erreur de suppression en base : {e}")

  data_file = (
      f"user_data_{st.session_state.user.id}.json"
      if st.session_state.user
      else "user_data.json"
  )
  if os.path.exists(data_file):
    try:
      with open(data_file, "r", encoding="utf-8") as f:
        entries = json.load(f)
      entries = [e for e in entries if e and e.get("id") != entry_id]
      with open(data_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=4)
    except Exception:
      pass
  return True


# Chargement des données globales et de l'utilisateur
st.session_state.kebabs_df = load_base_kebabs()
st.session_state.entries = load_user_entries()

# Messages de confirmation aléatoires
SIMPLES_VISITES_MESSAGES = [
    "✅ **{kebab}** validé ! Salade, tomate, oignon, chef !",
    "📍 **{kebab}** tamponné sur ton passeport Kebab ! Le Chef salue ton passage !",
    "🌯 **{kebab}** enregistré en coup de vent ! Rapide et efficace comme un kebab à 3h du matin !",
    "🎯 **{kebab}** coché dans ta liste ! Un de plus au compteur du Maître Kebabier !"
]

BIBLE_MESSAGES = [
    "🥙 **{kebab}** ajouté à La Bible avec succès ! Un régal pour l'âme et pour le ventre !",
    "📜 **{kebab}** gravé dans les annales sacrées ! Que la sauce blanche et le pain chaud te bénissent !",
    "👑 Entrée enregistrée pour **{kebab}** ! Le Maître Kebabier t'accorde sa bénédiction !",
    "🔥 **{kebab}** immortalisé ! Ton avis entre directement au panthéon du kebab !",
    "✨ Magnifique revue pour **{kebab}** ! Que tes frites soient toujours croustillantes et ta sauce généreuse !"
]

# Gestion de la navigation via les paramètres URL
if "p" in st.query_params:
  p_val = st.query_params["p"]
  if "last_p" not in st.session_state or st.session_state.last_p != p_val:
    if p_val == "carte":
      st.session_state.nav_page = "🗺️ Carte"
    elif p_val == "ajouter":
      st.session_state.nav_page = "🥙 Ajouter"
    elif p_val == "diary":
      st.session_state.nav_page = "📖 Diary"
    elif p_val == "stats":
      st.session_state.nav_page = "📊 Stats"
    st.session_state.last_p = p_val

if "nav_page" not in st.session_state:
  st.session_state.nav_page = "🗺️ Carte"

if "selected_kebab_nom" not in st.session_state:
  st.session_state.selected_kebab_nom = None

current_page = st.session_state.nav_page

# --- CSS COMMUN ET PERMANENT INJECTÉ DÈS LE DÉBUT ---
st.markdown(
    """
    <style>
    /* CSS Nav bar et Top Header */
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

    .top-header-badge {
        position: fixed !important; 
        top: 20px !important; 
        right: 95px !important; 
        z-index: 999990 !important; 
        background-color: rgba(20, 24, 28, 0.92) !important; 
        padding: 0px 16px !important; 
        height: 42px !important;
        display: flex !important;
        align-items: center !important;
        border-radius: 10px !important; 
        border: 1px solid #2c3440 !important;
        color: #ffffff !important; 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-size: 18px !important;
        font-weight: bold !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.4) !important;
        backdrop-filter: blur(10px) !important;
        white-space: nowrap !important;
    }

    div[data-testid="stPopover"] {
        position: fixed !important;
        top: 20px !important;
        right: 20px !important;
        z-index: 999991 !important;
        width: 65px !important;
        height: 42px !important;
    }
    div[data-testid="stPopover"] > button {
        background-color: rgba(20, 24, 28, 0.92) !important;
        border: 1px solid #2c3440 !important;
        border-radius: 10px !important;
        color: #ffffff !important;
        font-size: 18px !important;
        font-weight: bold !important;
        width: 65px !important;
        height: 42px !important;
        min-width: 65px !important;
        min-height: 42px !important;
        max-width: 65px !important;
        max-height: 42px !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.4) !important;
        backdrop-filter: blur(10px) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stPopover"] > button:hover {
        border-color: #00e054 !important;
        color: #00e054 !important;
        transform: scale(1.03);
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- PERSONNALISATION ESTHÉTIQUE SPÉCIFIQUE ---
if current_page == "🗺️ Carte" and not st.session_state.selected_kebab_nom:
  st.markdown(
      """
        <style>
        [data-testid="stHeader"], 
        .stAppHeader, 
        [data-testid="stDecoration"], 
        [data-testid="stToolbar"],
        [data-testid="stHeader"] * { 
            display: none !important; 
            visibility: hidden !important; 
            height: 0px !important; 
            min-height: 0px !important;
            max-height: 0px !important;
            background: transparent !important;
            opacity: 0 !important;
            pointer-events: none !important;
            z-index: -9999 !important;
        }

        [data-testid="stSidebar"] { display: none !important; }

        html, body, [data-testid="stAppViewContainer"], .stApp, .main, [data-testid="stMain"], [data-testid="stMainBlockContainer"] {
            overflow: hidden !important;
            height: 100vh !important;
            width: 100vw !important;
            background-color: #14181c !important;
            color: #9ab;
            margin: 0 !important;
            padding: 0 !important;
            top: 0 !important;
        }
        
        .block-container, [data-testid="block-container"], [data-testid="stMainBlockContainer"] {
            padding: 0rem !important;
            margin: 0rem !important;
            max-width: 100% !important;
            height: 100vh !important;
            max-height: 100vh !important;
            overflow: hidden !important;
            top: 0 !important;
        }

        div[data-testid="stElementContainer"]:has(iframe),
        div[data-testid="stIframe"],
        div[data-testid="stIFrame"] > iframe,
        iframe {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            border: none !important;
            display: block !important;
            z-index: 10 !important;
        }
        </style>
    """,
      unsafe_allow_html=True,
  )
else:
  st.markdown(
      """
        <style>
        html, body, [data-testid="stAppViewContainer"], .stApp {
            background-color: #14181c;
            color: #9ab;
            overflow-x: hidden !important;
            overflow-y: auto !important;
        }
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 90px !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        [data-testid="stHeader"], .stAppHeader { 
            display: none !important; 
            visibility: hidden !important; 
            height: 0px !important; 
        }
        [data-testid="stSidebar"] { display: none; }

        .stForm {
            background-color: #1c2228;
            padding: 25px;
            border-radius: 12px;
            border: 1px solid #2c3440;
        }

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
    """,
      unsafe_allow_html=True,
  )

# --- INJECTION DES ÉLÉMENTS SUR-ÉLEVÉS FLOTTANTS AVANT LA CARTE (ÉVITE LE FLICKER) ---
st.markdown(
    """
    <div class="top-header-badge">
        🥙 Kebaboxd
    </div>
    <div class="fixed-nav-bar">
        <a href="?p=carte" target="_self" class="nav-btn" title="Carte">🗺️</a>
        <a href="?p=ajouter" target="_self" class="nav-btn" title="Ajouter">🥙</a>
        <a href="?p=diary" target="_self" class="nav-btn" title="Diary">📖</a>
        <a href="?p=stats" target="_self" class="nav-btn" title="Stats">📊</a>
    </div>
""",
    unsafe_allow_html=True,
)

username_val = (
    st.session_state.profile.get("username", "Mon Compte")
    if st.session_state.profile
    else "Mon Compte"
)
with st.popover("👤", help="Mon Compte"):
  st.markdown(f"### 👤 {username_val}")
  if st.session_state.user and st.session_state.user.email:
    st.caption(f"📧 {st.session_state.user.email}")
  st.divider()
  if st.button("Se déconnecter 🚪", use_container_width=True):
    logout()

# --- PAGE SPÉCIFIQUE / FICHE DÉTAILLÉE DU KEBAB SÉLECTIONNÉ ---
if current_page == "🗺️ Carte" and st.session_state.selected_kebab_nom:
  nom_kebab_sel = st.session_state.selected_kebab_nom

  kebab_matches = st.session_state.kebabs_df[
      st.session_state.kebabs_df["nom"] == nom_kebab_sel
  ]
  k_data = kebab_matches.iloc[0] if not kebab_matches.empty else None

  mes_visites = [
      e
      for e in st.session_state.entries
      if e and e.get("nom_kebab") == nom_kebab_sel
  ]
  visites_effectuees = [e for e in mes_visites if not e.get("simple_visite")]
  est_deja_visite = len(mes_visites) > 0

  mes_notes = [
      e.get("note") for e in visites_effectuees if e.get("note") is not None
  ]
  ma_note_moyenne = (
      round(sum(mes_notes) / len(mes_notes), 2) if mes_notes else "N/A"
  )
  nb_mes_visites = len(visites_effectuees)

  all_reviews = load_all_kebab_reviews(nom_kebab_sel)

  all_reviews_sorted = sorted(
      all_reviews,
      key=lambda x: str(x.get("date_visite") or "1900-01-01"),
      reverse=True,
  )

  all_notes = [
      r.get("note") for r in all_reviews_sorted if r.get("note") is not None
  ]
  global_avg_note = (
      round(sum(all_notes) / len(all_notes), 2) if all_notes else "N/A"
  )

  _, col_k, _ = st.columns([0.15, 0.7, 0.15])
  with col_k:
    if st.button("⬅️ Retour à la carte"):
      st.session_state.selected_kebab_nom = None
      st.rerun()

    if est_deja_visite:
      badge_html = (
          "<span style='font-size: 0.45em; vertical-align: middle;"
          " background-color: rgba(0, 224, 84, 0.15); color: #00e054; padding:"
          " 4px 12px; border-radius: 20px; border: 1px solid #00e054;"
          " margin-left: 10px; display: inline-block;'>✅ Visité</span>"
      )
    else:
      badge_html = (
          "<span style='font-size: 0.45em; vertical-align: middle;"
          " background-color: rgba(255, 165, 0, 0.15); color: #ffa500; padding:"
          " 4px 12px; border-radius: 20px; border: 1px solid #ffa500;"
          " margin-left: 10px; display: inline-block;'>📍 À tester</span>"
      )

    st.markdown(
        "<h1 style='display: flex; align-items: center; flex-wrap: wrap; gap:"
        f" 8px;'>🥙 {nom_kebab_sel} {badge_html}</h1>",
        unsafe_allow_html=True,
    )

    if k_data is not None and pd.notna(k_data.get("adresse")):
      st.caption(f"📍 {k_data['adresse']}")

    st.markdown("<br>", unsafe_allow_html=True)

    m1, m2 = st.columns(2)
    with m1:
      st.metric(
          "Ma note", 
          f"{ma_note_moyenne} / 5 ⭐" if ma_note_moyenne != "N/A" else "N/A",
          f"parmi {nb_mes_visites} visite{'s' if nb_mes_visites > 1 else ''}"
      )
    with m2:
      st.metric(
          "Note moyenne globale",
          f"{global_avg_note} / 5 ⭐" if global_avg_note != "N/A" else "N/A",
          f"parmi {len(all_reviews_sorted)} avis"
      )

    if (
        k_data is not None
        and pd.notna(k_data.get("lat"))
        and pd.notna(k_data.get("lon"))
    ):
      try:
        mapbox_token = st.secrets.get("MAPBOX_API_KEY", "clé_par_défaut")
      except Exception:
        mapbox_token = "clé_par_défaut"

      m_fiche = folium.Map(
          location=[k_data["lat"], k_data["lon"]],
          zoom_start=16,
          tiles=None,
      )
      folium.TileLayer(
          tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={mapbox_token}",
          attr="&copy; CARTO",
          subdomains="abcd",
          max_zoom=20,
      ).add_to(m_fiche)

      folium.Marker(
          [k_data["lat"], k_data["lon"]],
          tooltip=nom_kebab_sel,
          icon=folium.Icon(
              color="green" if est_deja_visite else "red",
              icon="cutlery",
              prefix="fa",
          ),
      ).add_to(m_fiche)

      st.markdown(
          "<div style='border-radius: 12px; overflow: hidden; margin-bottom:"
          " 25px; border: 1px solid #2c3440;'>",
          unsafe_allow_html=True,
      )
      st_folium(
          m_fiche,
          width=None,
          height=220,
          use_container_width=True,
          key=f"fiche_map_{nom_kebab_sel}",
      )
      st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        "### 🗣️ Avis de la communauté"
    )
    if not all_reviews_sorted:
      st.info("Aucun avis enregistré par la communauté pour ce kebab.")
    else:
      for v in all_reviews_sorted:
        with st.container():
          c_user, c_date, c_details = st.columns([1.2, 1.2, 2.6])
          with c_user:
            st.markdown(f"👤 **{v.get('username', 'Anonyme')}**")
          with c_date:
            st.markdown(f"📅 **{v.get('date_visite', 'N/A')}**")
            if v.get("note") is not None:
              st.markdown(f"⭐ **{v['note']}** / 5")
            if v.get("prix"):
              st.caption(f"💶 {v['prix']} €")
          with c_details:
            if v.get("commentaire"):
              st.markdown(f"> *{v['commentaire']}*")
            else:
              st.caption("*Pas de commentaire*")
          st.divider()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(
        f"➕ Ajouter mon avis / visite pour {nom_kebab_sel}",
        use_container_width=True,
    ):
      st.session_state.kebab_select_box = nom_kebab_sel
      st.session_state.selected_kebab_nom = None
      st.session_state.nav_page = "🥙 Ajouter"
      st.query_params["p"] = "ajouter"
      st.session_state.last_p = "ajouter"
      st.rerun()

# --- PAGE 1 : CARTE ---
elif current_page == "🗺️ Carte":
  visités_noms = set(
      e.get("nom_kebab")
      for e in st.session_state.entries
      if e and e.get("nom_kebab")
  )

  mapbox_token = ""
  try:
    mapbox_token = st.secrets.get("MAPBOX_API_KEY", "clé_par_défaut")
  except Exception:
    mapbox_token = "clé_par_défaut"

  m = folium.Map(location=[49.4431, 1.0993], zoom_start=13, tiles=None)

  folium.TileLayer(
      tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={mapbox_token}",
      attr="&copy; OpenStreetMap &copy; CARTO",
      subdomains="abcd",
      name="CARTO Dark Matter",
      max_zoom=20,
  ).add_to(m)

  for _, row in st.session_state.kebabs_df.iterrows():
    nom = row["nom"]
    est_visite = nom in visités_noms
    color = "green" if est_visite else "red"

    folium.Marker(
        [row["lat"], row["lon"]],
        tooltip=nom,
        icon=folium.Icon(color=color, icon="cutlery", prefix="fa"),
    ).add_to(m)

  map_data = st_folium(
      m,
      width=None,
      height=1000,
      use_container_width=True,
      returned_objects=["last_object_clicked"],
  )

  if map_data and map_data.get("last_object_clicked"):
    clicked_lat = map_data["last_object_clicked"]["lat"]
    clicked_lng = map_data["last_object_clicked"]["lng"]

    tolerance = 0.0001
    matched = st.session_state.kebabs_df[
        (st.session_state.kebabs_df["lat"].sub(clicked_lat).abs() < tolerance)
        & (st.session_state.kebabs_df["lon"].sub(clicked_lng).abs() < tolerance)
    ]
    if not matched.empty:
      st.session_state.selected_kebab_nom = matched.iloc[0]["nom"]
      st.rerun()

else:
  st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)

  _, center_col, _ = st.columns([0.15, 0.7, 0.15])

  with center_col:
    if "flash_message" in st.session_state and st.session_state.flash_message:
      st.success(st.session_state.flash_message)
      st.session_state.flash_message = None

    if current_page == "🥙 Ajouter":
      st.markdown(
          '<h2 style="margin-bottom: 25px;">🥙 Ajouter un repas'
          ' miraculeux</h2>',
          unsafe_allow_html=True,
      )

      kebabs_list = st.session_state.kebabs_df["nom"].tolist()

      if (
          "kebab_select_box" not in st.session_state
          or st.session_state.kebab_select_box not in kebabs_list
      ):
        st.session_state.kebab_select_box = kebabs_list[0] if kebabs_list else None

      choix_kebab = st.selectbox(
          "",
          kebabs_list,
          key="kebab_select_box",
          placeholder="Tapez le nom d'un lieu de culte...",
      )

      if choix_kebab:
        kebab_info = st.session_state.kebabs_df[
            st.session_state.kebabs_df["nom"] == choix_kebab
        ].iloc[0]

        nb_simples_visites = len([
            e
            for e in st.session_state.entries
            if e
            and e.get("nom_kebab") == choix_kebab
            and e.get("simple_visite", False)
        ])

        try:
          mapbox_token = st.secrets.get("MAPBOX_API_KEY", "clé_par_défaut")
        except Exception:
          mapbox_token = "clé_par_défaut"

        m_mini = folium.Map(
            location=[kebab_info["lat"], kebab_info["lon"]],
            zoom_start=15,
            tiles=None,
        )
        folium.TileLayer(
            tiles=f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={mapbox_token}",
            attr="&copy; CARTO",
            subdomains="abcd",
            max_zoom=20,
        ).add_to(m_mini)

        folium.Marker(
            [kebab_info["lat"], kebab_info["lon"]],
            tooltip=choix_kebab,
            icon=folium.Icon(color="green", icon="cutlery", prefix="fa"),
        ).add_to(m_mini)

        st.markdown(
            "<div style='border-radius: 12px; overflow: hidden;"
            " margin-bottom: 20px; border: 1px solid #2c3440;'>",
            unsafe_allow_html=True,
        )
        st_folium(
            m_mini,
            width=None,
            height=200,
            use_container_width=True,
            key=f"minimap_{choix_kebab}",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        with st.form("form_add"):
          disabled_simple = nb_simples_visites >= 1
          
          simple_visite = st.checkbox(
              "Ne pas ajouter au calendrier ? (Marquer simplement comme"
              " visité)",
              disabled=disabled_simple,
              help=(
                  "Tu as déjà marqué ce kebab comme visité."
                  if disabled_simple
                  else None
              )
          )

          if disabled_simple:
            st.info(
                "💡 **Limite atteinte (1/1)** : Tu as déjà marqué ce kebab 1 fois en 'simple visite'. Pour enregistrer tes passages suivants, il faut remplir ton journal avec la date et ton avis !"
            )

          if not simple_visite:
            date_visite = st.date_input(
                "Date de visite",
                value=datetime.date.today(),
                min_value=datetime.date(2000, 1, 1),
                max_value=datetime.date.today(),
                format="DD/MM/YYYY",
            )
            note = st.slider("Note (/5) ⭐", 0.0, 5.0, 4.0, 0.5)
            prix = st.number_input(
                "Prix (€) (Optionnel)",
                min_value=0.0,
                max_value=50.0,
                value=0.0,
                step=0.5,
            )
            commentaire = st.text_area("Avis (Optionnel)")
          else:
            date_visite = None
            note = None
            prix = 0.0
            commentaire = ""

          if st.form_submit_button("Enregistrer la visite 🥙"):
            if simple_visite and nb_simples_visites >= 1:
              st.error(
                  "Impossible : Limite de 1 simple visite atteinte pour ce kebab ! Décoche l'option pour ajouter une vraie entrée au journal."
              )
            else:
              k_id = (
                  int(kebab_info["id"])
                  if "id" in kebab_info and pd.notna(kebab_info["id"])
                  else None
              )
              new_entry = {
                  "id": str(datetime.datetime.now().timestamp()),
                  "kebab_id": k_id,
                  "nom_kebab": choix_kebab,
                  "date_visite": str(date_visite) if date_visite else None,
                  "note": note,
                  "prix": prix if prix > 0 else None,
                  "commentaire": commentaire if commentaire else None,
                  "simple_visite": simple_visite,
              }
              save_user_entry(new_entry)
              st.session_state.entries = load_user_entries()

              if simple_visite:
                msg_template = random.choice(SIMPLES_VISITES_MESSAGES)
                st.session_state.flash_message = msg_template.format(kebab=choix_kebab)
              else:
                msg_template = random.choice(BIBLE_MESSAGES)
                st.session_state.flash_message = msg_template.format(kebab=choix_kebab)
              st.rerun()

    elif current_page == "📖 Diary":
      st.markdown(
          '<h2 style="margin-bottom: 45px;">📖 La Bible</h2>',
          unsafe_allow_html=True,
      )

      diary_entries = [
          e for e in st.session_state.entries if e and not e.get("simple_visite")
      ]

      if not diary_entries:
        st.info("Magne toi. Ton Maître Kebabier t'attends.")
      else:

        def sort_key(x):
          d = x.get("date_visite") if x else None
          if not d:
            return "1900-01-01"
          return str(d)

        entries_sorted = sorted(
            diary_entries, key=sort_key, reverse=True
        )

        for index, entry in enumerate(entries_sorted):
          entry_id = entry.get("id", f"fallback_{index}")
          nom_k = entry.get("nom_kebab")
          note_val = entry.get("note")
          prix_val = entry.get("prix")

          adresse = entry.get("adresse") or ""
          if not adresse:
            k_match = st.session_state.kebabs_df[
                st.session_state.kebabs_df["nom"] == nom_k
            ]
            adresse = (
                k_match.iloc[0]["adresse"] if not k_match.empty else ""
            )

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
              if adresse:
                st.caption(f"📍 {adresse}")
              if entry.get("commentaire"):
                st.markdown(f"> *{entry['commentaire']}*")
            with c3:
              if st.button("🗑️", key=f"del_diary_{entry_id}_{index}"):
                delete_user_entry(entry_id)
                st.session_state.entries = load_user_entries()
                st.rerun()
            st.divider()

    elif current_page == "📊 Stats":
      st.markdown(
          '<h2 style="margin-bottom: 40px;">📊 Tes Statistiques</h2>',
          unsafe_allow_html=True,
      )

      if not st.session_state.entries:
        st.info("Tu n'es pas allé voir ton Maître Kebabier depuis longtemps...")
      else:
        total_visites = len([
            e
            for e in st.session_state.entries
            if e and e.get("date_visite") is not None
        ])

        visités_uniques_set = set(
            e.get("nom_kebab")
            for e in st.session_state.entries
            if e.get("nom_kebab")
        )
        kebabs_uniques = len(visités_uniques_set)
        total_kebabs_dispos = len(st.session_state.kebabs_df)
        pokedex_str = f"{kebabs_uniques} / {total_kebabs_dispos}"

        noms_visites = [
            e.get("nom_kebab")
            for e in st.session_state.entries
            if e.get("nom_kebab")
        ]
        kebab_prefere = (
            max(set(noms_visites), key=noms_visites.count)
            if noms_visites
            else "N/A"
        )
        nb_fois_prefere = (
            noms_visites.count(kebab_prefere) if kebab_prefere != "N/A" else 0
        )

        notes = [
            e.get("note")
            for e in st.session_state.entries
            if e.get("note") is not None
        ]
        moyenne_notes = round(sum(notes) / len(notes), 2) if notes else 0.0

        prix_list = [
            e.get("prix")
            for e in st.session_state.entries
            if e.get("prix") and e.get("prix") > 0
        ]
        prix_moyen = (
            round(sum(prix_list) / len(prix_list), 2) if prix_list else 0.0
        )

        valid_dates = []
        for e in st.session_state.entries:
          if e.get("date_visite"):
            try:
              parsed_date = datetime.datetime.strptime(
                  e["date_visite"], "%Y-%m-%d"
              ).date()
              valid_dates.append(parsed_date)
            except Exception:
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
              if (mondays[i] - mondays[i - 1]).days == 7:
                c_streak += 1
              else:
                c_streak = 1
              max_streak = max(max_streak, c_streak)

            this_week_monday = get_monday(datetime.date.today())
            if (this_week_monday - mondays[-1]).days <= 7:
              current_streak = 1
              for i in range(len(mondays) - 2, -1, -1):
                if (mondays[i + 1] - mondays[i]).days == 7:
                  current_streak += 1
                else:
                  break

        st.markdown("### 🏆 Général")
        col1, col2, col3 = st.columns(3)
        with col1:
          st.metric(
              "Total de visites",
              total_visites,
              (
                  f"depuis le {first_date.strftime('%d %B %Y')}"
                  if valid_dates
                  else None
              ),
              delta_color="off",
          )
          st.metric("Pokédex", pokedex_str)
        with col2:
          st.metric("Note moyenne globale", f"{moyenne_notes} / 5")
          st.metric(
              "Aumône moyenne",
              f"{prix_moyen} €" if prix_moyen > 0 else "N/A",
          )
        with col3:
          st.metric(
              "Safe place",
              kebab_prefere,
              f"{nb_fois_prefere} visites" if nb_fois_prefere > 0 else None,
              delta_color="off",
          )

        st.divider()
        st.markdown("### 📈 Rythme & Winstreaks")
        col4, col5, col6, col7 = st.columns(4)
        with col4:
          st.metric(
              "Moyenne / Semaine",
              f"{avg_per_week} Kebabs",
              f"soit un K/D de {kd_ratio}",
              delta_color="off",
          )
        with col5:
          st.metric("Moyenne / Mois", f"{avg_per_month} Kebabs")
        with col6:
          st.metric("Winstreak Actuelle 🔥", f"{current_streak} sem.")
        with col7:
          st.metric("Meilleure Winstreak 👑", f"{max_streak} sem.")

        if valid_dates:
          st.divider()
          st.markdown("### 📊 Tendances")

          df_stats = pd.DataFrame(valid_dates, columns=["date"])
          df_stats["date"] = pd.to_datetime(df_stats["date"])

          jour_labels = ["L", "M", "M ", "J", "V", "S", "D"]
          df_stats["Jour_Num"] = df_stats["date"].dt.dayofweek
          jour_counts_series = df_stats["Jour_Num"].value_counts()

          df_jour = pd.DataFrame({
              "Jour": jour_labels,
              "Visites": [jour_counts_series.get(i, 0) for i in range(7)],
          })
          df_jour["Jour"] = pd.Categorical(
              df_jour["Jour"], categories=jour_labels, ordered=True
          )

          df_stats["Mois"] = df_stats["date"].dt.to_period("M").astype(str)
          mois_counts = df_stats["Mois"].value_counts().sort_index()

          c_chart1, c_chart2 = st.columns(2)
          with c_chart1:
            st.markdown("**Fréquentation par jour**")
            st.bar_chart(
                df_jour, x="Jour", y="Visites", height=250, color="#00e054"
            )
          with c_chart2:
            st.markdown("**Évolution mensuelle**")
            st.line_chart(mois_counts, height=250, color="#00e054")