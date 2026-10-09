import os
from pathlib import Path

DOSSIER_PROJET = Path(__file__).resolve().parent


def _charger_fichier_env() -> None:
    chemin = DOSSIER_PROJET / ".env"

    if not chemin.is_file():
        return

    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()

        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue

        nom, valeur = ligne.split("=", 1)
        os.environ.setdefault(nom.strip(), valeur.strip().strip('"').strip("'"))


_charger_fichier_env()

# --- Services externes -------------------------------------------------------------------------------------------
URL_BASE_DE_DONNEES = os.getenv("DATABASE_URL", "")
CLE_API_GOOGLE = os.getenv("GOOGLE_API_KEY", "")
IDENTIFIANT_MOTEUR_GOOGLE = os.getenv("GOOGLE_CX", "")
# Recherche web : les fournisseurs sont essayés dans cet ordre, le premier qui répond est utilisé.
ORDRE_FOURNISSEURS_RECHERCHE = [nom.strip() for nom in os.getenv("FOURNISSEURS_RECHERCHE", "searxng,duckduckgo,wikipedia,brave,google").split(",") if nom.strip()]
URL_SEARXNG = os.getenv("SEARXNG_URL", "http://localhost:8080").rstrip("/")
CLE_API_BRAVE = os.getenv("BRAVE_API_KEY", "")
URL_OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")

# --- Agent IA : LangChain orchestre exclusivement le modèle local Ollama -----------------------------------------
# Compatibilité historique neutralisée : une ancienne clé OpenRouter ne peut jamais être utilisée.
AGENT_API_URL = AGENT_API_CLE = AGENT_API_MODELE = ""
AGENT_API_ACTIVE = False
AGENT_LOCAL_ACTIF = os.getenv("AGENT_LOCAL", "on").lower() != "off"
MODELE_REDACTION = os.getenv("MODELE", "qwen3:4b")
DELAI_PANNE_FOURNISSEUR_EN_SECONDES = 60                      # un fournisseur en panne est ignoré pendant ce temps
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))
TOP_P = float(os.getenv("TOP_P", "0.9"))

# --- Vecteurs (RAG) : nomic-embed-text = 768 dimensions (et non 1024 comme bge-m3) ------------------------------
MODELE_VECTEURS = os.getenv("MODELE_EMBEDDING", "nomic-embed-text")
DIMENSION_VECTEUR = int(os.getenv("DIMENSION_VECTEUR", "768"))   # doit correspondre à vector(768) dans schema_rag.sql
DUREE_MODELE_EN_MEMOIRE = "30m"               # keep_alive d'Ollama
URL_NOMINATIM = "https://nominatim.openstreetmap.org/search"
IDENTIFIANT_APPLICATION = os.getenv("USER_AGENT", "connecteo-madagascar-geo/1.0")
PORT_API = int(os.getenv("PORT", "8000"))

# --- Dossiers et fichiers ----------------------------------------------------------------------------------------
DOSSIER_DONNEES = Path(os.getenv("DOSSIER_DONNEES", DOSSIER_PROJET / "donnees"))
DOSSIER_LIEUX_JSON = DOSSIER_DONNEES / "lieux"
DOSSIER_PRODUITS_JSON = DOSSIER_DONNEES / "produits"
DOSSIER_COMPLEMENTAIRES_JSON = DOSSIER_DONNEES / "complementaires"
DOSSIER_RESULTATS = DOSSIER_DONNEES / "resultats"
DOSSIER_CSV_PROPRES = DOSSIER_DONNEES / "csv_propres"
CHEMIN_EXCEL = DOSSIER_PROJET.parent / "Carte Infra_Opér_Début 2024_VFin.xlsx"
PAGE_WEB_DEMONSTRATION = DOSSIER_PROJET / "chat_demo.html"

# --- Fonctionnement ----------------------------------------------------------------------------------------------
INTERVALLE_REINDEXATION_EN_SECONDES = 600     # 10 minutes
DUREE_CACHE_RESULTATS_EN_SECONDES = 600       # 10 minutes
NOMBRE_FRAGMENTS_RECUPERES = 30
NOMBRE_LIEUX_MAX = 30
NOMBRE_LIEUX_POUR_LE_RESUME = 5
NOMBRE_PAGES_WEB_LUES = 4
CARACTERES_MAX_PAR_PAGE = 6000

# --- Seuils de recherche -----------------------------------------------------------------------------------------
SEUIL_SIMILARITE_NOM_LIEU = 0.5               
SEUIL_SIMILARITE_FRAGMENT = 0.45              
SEUIL_COUVERTURE_MOTS_CLES = 0.5              
BONUS_MOT_CLE_COMMUN = 0.2

# --- Classement des lieux ----------------------------------------------------------------------------------------
NOTE_MOYENNE_DE_REFERENCE = 3.5
NOMBRE_AVIS_DE_REFERENCE = 10
POIDS_CLASSEMENT = {"pertinence": 0.45, "note": 0.15, "confiance": 0.15, "origine": 0.10, "precision": 0.15}
POIDS_ORIGINE = {"referentiel": 1.0, "osm": 0.9, "base_connaissances": 0.8, "google": 0.5}
POIDS_PRECISION = {"precis": 1.0, "centroide": 0.6, "repli_hierarchique": 0.2, "absent": 0.0}
CONFIANCE_DONNEES_PRODUITS = 0.7

# --- Madagascar : emprise géographique (pour détecter les coordonnées fausses) ------------------------------------
LATITUDE_MIN, LATITUDE_MAX = -26.0, -11.5
LONGITUDE_MIN, LONGITUDE_MAX = 42.5, 51.0

# --- Opérateurs mobiles (fichier Excel). Lettre = celle des colonnes 2GT2023, COUVT... ---------------------------
# À VÉRIFIER avec la feuille Desserte_des_Communes : seule E = GULFSAT est mentionnée dans le LISEZMOI.
OPERATEURS_PAR_LETTRE = {"T": "TELMA", "O": "ORANGE", "A": "AIRTEL", "B": "BLUELINE", "E": "GULFSAT"}
OPERATEURS_VALIDES = set(OPERATEURS_PAR_LETTRE.values())

# --- Synonymes : un mot cherché trouve aussi tous les mots de son groupe -----------------------------------------
GROUPES_DE_SYNONYMES = [
    ["CACAO", "CACAOYER", "CACAOYERE", "CHOCOLAT", "KAKAO"],
    ["VANILLE", "VANILLIER", "VANILLA"],
    ["CANNE A SUCRE", "CANNE", "SUCRE", "SAKARY"],
    ["RIZ", "RIZIERE", "VARY"],
    ["CAFE", "CAFEIER", "KAFE"],
    ["GIROFLE", "GIROFLIER", "CLOU DE GIROFLE"],
    ["POIVRE", "POIVRIER"],
    ["LITCHI", "LYCHEE", "LETCHI"],
    ["HOPITAL", "CLINIQUE", "CSB", "CENTRE DE SANTE", "DISPENSAIRE"],
    ["MARCHE", "MARKET", "TOKO"],
    ["ECOLE", "LYCEE", "COLLEGE", "UNIVERSITE"],
]

# --- Fenêtre de précision (requête floue) et urgence -------------------------------------------------------------
QUESTION_REQUETE_FLOUE = "Que cherchez-vous exactement ?"
QUESTION_AUCUN_RESULTAT = "Je n'ai rien trouvé. Pouvez-vous préciser votre recherche ?"
MESSAGE_URGENCE = "En cas d'urgence, contactez immédiatement les secours."
# Numéros fournis par l'équipe : À VÉRIFIER auprès d'une source officielle (un avertissement est ajouté tant que
# NUMEROS_D_URGENCE_VERIFIES vaut False).
NUMEROS_D_URGENCE: list[dict] = [
    {"service": "Police", "numero": "117"},
    {"service": "Pompiers", "numero": "118"},
    {"service": "Ambulance", "numero": "124"},
]
NUMEROS_D_URGENCE_VERIFIES = False
# Mots qui déclenchent directement l'affichage des numéros d'urgence (comparaison mot entier, sans accents)
URGENCE_MOTS = {"urgence", "urgent", "sos", "secours", "emergency", "vonjeo", "vonjy", "maika", "maharary", "loza"}

OPTIONS_DE_CLARIFICATION = [
    {"id": "lieu", "libelle": "Un lieu", "termes_de_recherche": [],
     "question_suivante": "Quel lieu cherchez-vous ? (ville, commune, site...)"},
    {"id": "ressource", "libelle": "Une ressource ou un produit", "termes_de_recherche": [],
     "question_suivante": "Quelle ressource ou quel produit cherchez-vous ? (cacao, vanille, riz...)"},
    {"id": "sante", "libelle": "Un service de santé", "termes_de_recherche": ["santé", "hôpital", "centre de santé"],
     "question_suivante": "Dans quelle ville ou commune cherchez-vous un service de santé ?"},
    {"id": "urgence", "libelle": "Une urgence", "style": "danger", "urgence": True,
     "termes_de_recherche": [], "question_suivante": ""},
]

# --- Assistant conversationnel (route /chat) ---------------------------------------------------------------------
CHAT_MESSAGES_MAX_EN_MEMOIRE = 8              # contexte court : plus rapide avec qwen3:4b
CHAT_DUREE_SESSION_EN_SECONDES = 7200
CHAT_SESSIONS_MAX = 500
CHAT_ATTENTE_MAX_EN_SECONDES = float(os.getenv("CHAT_ATTENTE_MAX", "1.2"))
CHAT_DUREE_MAX_EN_SECONDES = float(os.getenv("CHAT_DUREE_MAX", "25"))
# Temps maximal accordé à l'IA à chaque étape (attente du modèle local comprise). Au-delà, l'assistant répond sans IA
# (règles et texte de secours) au lieu de faire attendre l'utilisateur plusieurs minutes.
CHAT_DELAI_COMPREHENSION_EN_SECONDES = float(os.getenv("CHAT_DELAI_COMPREHENSION", "5"))
CHAT_DELAI_REDACTION_EN_SECONDES = float(os.getenv("CHAT_DELAI_REDACTION", "10"))
CHAT_TAILLE_MAX_MESSAGE = 2000
CHAT_LIEUX_MAX = 6                            # lieux détaillés dans la réponse du chat (le reste reste dans la liste)
LIMITE_REQUETES_PAR_MINUTE = int(os.getenv("LIMITE_REQUETES_PAR_MINUTE", "40"))   # par adresse IP (protège le quota IA)

# --- Images d'aperçu ---------------------------------------------------------------------------------------------
IMAGES_ACTIVES = os.getenv("IMAGES", "on").lower() != "off"
IMAGES_NOMBRE_LIEUX = int(os.getenv("IMAGES_NOMBRE_LIEUX", "8"))
IMAGES_DELAI_TOTAL_EN_SECONDES = float(os.getenv("IMAGES_DELAI_TOTAL", "5"))
IMAGES_DUREE_CACHE_EN_SECONDES = 86400
IMAGES_DELAI_REQUETE_EN_SECONDES = 4

# --- Établissements précis (restaurants, hôtels, agences...) : OpenStreetMap, sans clé ---------------------------
POI_ACTIF = os.getenv("POI_OSM", "on").lower() != "off"
URLS_OVERPASS = [url.strip() for url in os.getenv(
    "OVERPASS_URLS", "https://overpass-api.de/api/interpreter,https://overpass.kumi.systems/api/interpreter").split(",") if url.strip()]
POI_RAYON_MAX_EN_METRES = 15000
POI_RAYON_PAR_DEFAUT_EN_METRES = 6000
POI_NOMBRE_MAX = 12
POI_DELAI_EN_SECONDES = 5                     # attente maximale des sources d'établissements
