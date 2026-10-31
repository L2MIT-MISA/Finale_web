import os
from pathlib import Path

DOSSIER_PROJET = Path(__file__).resolve().parent


def _charger_fichier_env() -> None:
    chemin = DOSSIER_PROJET / ".env"

    if os.getenv("CONNECTEO_SANS_FICHIER_ENV") == "1" or not chemin.is_file():
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
DELAI_DE_CONNEXION_EN_SECONDES = float(os.getenv("DELAI_CONNEXION", "8"))
TAILLE_DU_POOL = int(os.getenv("TAILLE_POOL", "4"))
CLE_API_GOOGLE = os.getenv("GOOGLE_API_KEY", "")
IDENTIFIANT_MOTEUR_GOOGLE = os.getenv("GOOGLE_CX", "")
# Recherche web : les fournisseurs sont essayés dans cet ordre, le premier qui répond est utilisé.
ORDRE_FOURNISSEURS_RECHERCHE = [nom.strip() for nom in os.getenv("FOURNISSEURS_RECHERCHE", "tavily,searxng,duckduckgo,wikipedia,brave,google").split(",") if nom.strip()]
# Tavily : API de recherche pour agents, 1 000 recherches gratuites par mois sans carte (documentation du 30/10/2026),
# résultats et images en 1 à 2 s. Sans clé, il est ignoré.
CLE_API_TAVILY = os.getenv("TAVILY_API_CLE", "")
URL_SEARXNG = os.getenv("SEARXNG_URL", "http://localhost:8080").rstrip("/")
CLE_API_BRAVE = os.getenv("BRAVE_API_KEY", "")
# --- Agent IA : LangChain, uniquement par API (Gemini, puis Groq en secours) ---------------------------------------
# AGENT_FOURNISSEUR = off | gemini | groq. Sans cette variable : gemini si AGENT_API_CLE est renseignée, sinon off.
# La clé de l'IA est AGENT_API_CLE : jamais GOOGLE_API_KEY, réservée à Google Custom Search.
# Mesurés le 30/10/2026 avec les clés du projet : gemini-2.5-flash est fermé aux nouveaux comptes (404),
# gemini-3.7/3.8-flash étaient surchargés (503, 504, > 30 s) ; gemini-3.6-flash répondait en 5 à 7 s, Groq en 1 s.
# L'offre gratuite Gemini limite gemini-3.6-flash à 20 requêtes par jour (message 429 de Google) : plusieurs modèles,
# séparés par des virgules, forment une chaîne (chaque modèle a son propre quota), essayée dans l'ordre.
# Cerebras : offre gratuite gpt-oss-120b et qwen-3.8-27b (5 req/min, 1 M tokens/jour, page « rate limits » du
# 30/10/2026). OpenRouter : seul nemotron-3.5-super-vl:free a réussi réponse, JSON et agent le 30/10/2026 (gemma-4 :free
# saturé, 429) ; la liste gratuite change souvent. Mistral : mistral-small-latest et mistral-medium-latest existent
# (liste des modèles du compte), mais un compte non activé reçoit « x-ratelimit-limit-req-minute = 0 » (429).
MODELES_PAR_DEFAUT = {"gemini": "gemini-3.6-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite",
                      "groq": "openai/gpt-oss-120b,qwen/qwen3.8-27b",
                      "cerebras": "gpt-oss-120b,qwen-3.8-27b",
                      "openrouter": "nvidia/nemotron-3.5-super-vl:free",
                      "mistral": "mistral-small-latest,mistral-medium-latest"}
URLS_COMPATIBLES_OPENAI = {"cerebras": "https://api.cerebras.ai/v1", "openrouter": "https://openrouter.ai/api/v1"}
AGENT_API_CLE = os.getenv("AGENT_API_CLE", "")
AGENT_FOURNISSEUR = (os.getenv("AGENT_FOURNISSEUR") or ("gemini" if AGENT_API_CLE else "off")).strip().lower()
MODELE_REDACTION = os.getenv("MODELE") or MODELES_PAR_DEFAUT.get(AGENT_FOURNISSEUR, "")
# Fournisseur de secours, essayé quand le principal est en panne, limité (429) ou hors quota.
AGENT_SECOURS_FOURNISSEUR = os.getenv("AGENT_SECOURS_FOURNISSEUR", "off").strip().lower()
AGENT_SECOURS_CLE = os.getenv("AGENT_SECOURS_CLE", "")
AGENT_SECOURS_MODELE = os.getenv("AGENT_SECOURS_MODELE") or MODELES_PAR_DEFAUT.get(AGENT_SECOURS_FOURNISSEUR, "")
# Chaîne complète, essayée dans l'ordre : AGENT_CHAINE=gemini,groq,cerebras,openrouter. Chaque fournisseur a sa clé
# <NOM>_API_CLE et, si besoin, ses modèles <NOM>_MODELES (virgules). Sans AGENT_CHAINE : principal puis secours.
AGENT_CHAINE = [nom.strip().lower() for nom in os.getenv("AGENT_CHAINE", "").split(",") if nom.strip()]
CLES_API = {nom: os.getenv(f"{nom.upper()}_API_CLE", "") for nom in MODELES_PAR_DEFAUT}
MODELES_API = {nom: os.getenv(f"{nom.upper()}_MODELES", "") for nom in MODELES_PAR_DEFAUT}
# Plafonds par fournisseur (protègent le quota gratuit). Au-delà : fournisseur suivant, puis repli sans IA.
AGENT_APPELS_PAR_MINUTE = int(os.getenv("AGENT_APPELS_PAR_MINUTE", "10"))
AGENT_APPELS_PAR_JOUR = int(os.getenv("AGENT_APPELS_PAR_JOUR", "200"))
AGENT_APPELS_SIMULTANES = int(os.getenv("AGENT_APPELS_SIMULTANES", "4"))
DELAI_PANNE_FOURNISSEUR_EN_SECONDES = 60                      # un fournisseur limité (429) est ignoré pendant ce temps
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))
TOP_P = float(os.getenv("TOP_P", "0.9"))

# --- Vecteurs (RAG) : 768 dimensions, comme vector(768) dans schema_rag.sql ------------------------------------
# VECTEURS_FOURNISSEUR = off | gemini. Off par défaut : rien n'est envoyé ni indexé sans décision explicite.
# Changer de modèle de vecteurs impose de réindexer : les vecteurs ne sont pas comparables d'un modèle à l'autre.
VECTEURS_FOURNISSEUR = os.getenv("VECTEURS_FOURNISSEUR", "off").strip().lower()
MODELE_VECTEURS = os.getenv("MODELE_EMBEDDING", "gemini-embedding-001")
DIMENSION_VECTEUR = int(os.getenv("DIMENSION_VECTEUR", "768"))   # doit correspondre à vector(768) dans schema_rag.sql
DELAI_VECTEUR_REQUETE_EN_SECONDES = float(os.getenv("VECTEURS_DELAI_REQUETE", "4"))
VECTEURS_APPELS_PAR_MINUTE = int(os.getenv("VECTEURS_APPELS_PAR_MINUTE", "60"))
VECTEURS_APPELS_PAR_JOUR = int(os.getenv("VECTEURS_APPELS_PAR_JOUR", "1000"))
# Indexation automatique (démarrage, toutes les 10 minutes, lieux appris du web) : off par défaut (consomme le quota)
INDEXATION_AUTO = os.getenv("INDEXATION_AUTO", "off").lower() != "off"
URL_NOMINATIM = "https://nominatim.openstreetmap.org/search"
# Wikimedia (Wikipédia, Commons) refuse (403) un client sans contact dans son User-Agent ; Nominatim l'exige aussi.
IDENTIFIANT_APPLICATION = os.getenv("USER_AGENT", "connecteo-madagascar-geo/1.0 (https://connecteo.duckdns.org)")
HOTE_API = os.getenv("HOTE_API", "127.0.0.1")
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
CHAT_MESSAGES_MAX_EN_MEMOIRE = 8              # derniers messages envoyés à l'IA avec le nouveau message
CHAT_DUREE_SESSION_EN_SECONDES = 7200
CHAT_SESSIONS_MAX = 500
CHAT_ATTENTE_MAX_EN_SECONDES = float(os.getenv("CHAT_ATTENTE_MAX", "1.2"))
CHAT_DUREE_MAX_EN_SECONDES = float(os.getenv("CHAT_DUREE_MAX", "55"))
# Temps maximal accordé à l'IA à chaque étape. Au-delà, l'assistant répond sans IA (règles et texte de secours).
# Mesuré le 30/10/2026 : une même requête Groq varie de 1 à 6 s selon le réseau ; 15 s ne laissaient pas assez au secours
CHAT_DELAI_COMPREHENSION_EN_SECONDES = float(os.getenv("CHAT_DELAI_COMPREHENSION", "10"))
CHAT_DELAI_REDACTION_EN_SECONDES = float(os.getenv("CHAT_DELAI_REDACTION", "20"))
CHAT_DELAI_LIBRE_EN_SECONDES = float(os.getenv("CHAT_DELAI_LIBRE", "30"))
CHAT_TOKENS_REDACTION = int(os.getenv("CHAT_TOKENS_REDACTION", "700"))
CHAT_TOKENS_LIBRE = int(os.getenv("CHAT_TOKENS_LIBRE", "1500"))
CHAT_CARACTERES_MAX_HISTORIQUE = 6000         # historique envoyé au fournisseur (les tours les plus anciens sont coupés)
# Questions de connaissance (« Connais-tu X ? ») : recherche web préalable, comme un moteur de recherche
CHAT_RECHERCHE_WEB_PREALABLE = os.getenv("CHAT_RECHERCHE_WEB", "on").lower() != "off"
CHAT_DELAI_RECHERCHE_WEB_EN_SECONDES = float(os.getenv("CHAT_DELAI_RECHERCHE_WEB", "10"))
CHAT_RESULTATS_WEB = 6
CHAT_TAILLE_MAX_MESSAGE = 2000
CHAT_LIEUX_MAX = 6                            # lieux détaillés dans la réponse du chat (le reste reste dans la liste)
LIMITE_REQUETES_PAR_MINUTE = int(os.getenv("LIMITE_REQUETES_PAR_MINUTE", "40"))   # par adresse IP (protège le quota IA)

# --- Images d'aperçu ---------------------------------------------------------------------------------------------
IMAGES_ACTIVES = os.getenv("IMAGES", "on").lower() != "off"
IMAGES_NOMBRE_LIEUX = int(os.getenv("IMAGES_NOMBRE_LIEUX", "8"))
IMAGES_DELAI_TOTAL_EN_SECONDES = float(os.getenv("IMAGES_DELAI_TOTAL", "5"))
IMAGES_DUREE_CACHE_EN_SECONDES = 86400
IMAGES_DELAI_REQUETE_EN_SECONDES = 4
IMAGES_PAR_LIEU = int(os.getenv("IMAGES_PAR_LIEU", "4"))
IMAGES_COMMONS = os.getenv("IMAGES_COMMONS", "on").lower() != "off"      # Wikimedia Commons autour des coordonnées
IMAGES_MAPILLARY_JETON = os.getenv("MAPILLARY_JETON", "")                # vues de rue, jeton gratuit (facultatif)
# Google Places Photos (facultatif, compte de facturation requis) : jamais mis en cache (conditions de Google)
IMAGES_GOOGLE_PLACES_CLE = os.getenv("GOOGLE_PLACES_CLE", "")
IMAGES_GOOGLE_PLACES_PAR_RECHERCHE = int(os.getenv("GOOGLE_PLACES_PAR_RECHERCHE", "3"))

# --- Établissements précis (restaurants, hôtels, agences...) : OpenStreetMap, sans clé ---------------------------
POI_ACTIF = os.getenv("POI_OSM", "on").lower() != "off"
URLS_OVERPASS = [url.strip() for url in os.getenv(
    "OVERPASS_URLS", "https://overpass-api.de/api/interpreter,https://overpass.kumi.systems/api/interpreter").split(",") if url.strip()]
POI_RAYON_MAX_EN_METRES = 15000
POI_RAYON_PAR_DEFAUT_EN_METRES = 6000
POI_NOMBRE_MAX = 12
POI_DELAI_EN_SECONDES = int(os.getenv("POI_DELAI", "8"))   # attente maximale des sources d'établissements (4,3 s mesurées seules)
