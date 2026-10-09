"""Assistant conversationnel : une vraie discussion, avec mémoire, au-dessus du moteur de recherche.

Le site (web) et l'application (mobile) envoient la même chose : POST /chat {message, session_id, requete_id}.
Chaque tour suit ces étapes :
  1. urgence ?              -> numéros d'urgence tout de suite, sans IA ;
  2. compréhension          -> règles rapides, puis l'agent LangChain + qwen3:4b quand c'est ambigu ;
  3. action                 -> discuter, demander une précision, chercher (établissements OpenStreetMap, base RAG, web),
                               ou montrer la carte (seulement si l'utilisateur le demande) ;
  4. images d'aperçu        -> ajoutées aux lieux ;
  5. réponse rédigée        -> l'IA rédige un message poli et précis à partir des seuls résultats trouvés.
Le résultat est écrit dans donnees/resultats/<id>.json : /chat l'attend au plus CHAT_ATTENTE_MAX_EN_SECONDES, puis le client
relit GET /resultats/<id> tant que `statut` vaut « en_cours ».
"""
from __future__ import annotations

import logging
import re
import secrets
import threading
import time
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass, field

import agent_ia
import config
import poi_osm
import recherche
import recherche_images
import resultat_json
from modeles import AnalyseTour, ReponseChat
from outils import extraire_mots_utiles, normaliser_nom, retirer_accents, trouver_groupe_synonymes
from prompts import construire_messages_analyse, construire_messages_chat

journal = logging.getLogger("conversation")

NIVEAUX_ADMINISTRATIFS = {"province", "region", "district", "commune", "fokontany"}
DELAI_RECHERCHE_COMPLETE_EN_SECONDES = 8       # au-delà, réponse partielle immédiate ; le travail continue en arrière-plan
DELAI_COMPLEMENT_WEB_EN_SECONDES = 3           # des établissements existent déjà : ne jamais bloquer sur le web
MOTS_MAX_PHRASE_SIMPLE = 6                     # au-delà, la phrase est confiée à l'IA pour être comprise
MOTS_DE_POLITESSE = {
    "bonjour", "bonsoir", "salut", "hello", "hi", "hey", "coucou", "salama", "manao", "ahoana", "merci", "mersi",
    "misaotra", "ok", "okay", "daccord", "super", "parfait", "cool", "oui", "non", "svp", "stp", "sil", "vous", "te",
    "plait", "tompoko", "au", "revoir", "bye", "a", "bientot", "bravo", "genial", "excellent", "nickel", "d", "accord",
    "tres", "bien", "beaucoup", "encore", "ca", "va", "comment", "allez", "vas", "tu", "et", "toi", "je", "suis",
    "content", "heureux", "ravi", "de",
}
MOTS_DE_REMERCIEMENT = {"merci", "mersi", "misaotra", "bravo", "genial", "excellent", "parfait", "super", "nickel", "cool"}
MOTS_DE_CARTE = {"carte", "map", "maps", "itineraire", "itineraires"}
MOTS_DE_PERSONNE = {"personne", "quelqu", "quelquun", "homme", "femme", "biographie"}
MOTS_DE_FIN_DE_LIEU = {"svp", "stp", "please", "merci", "pour", "qui", "que", "avec", "sil", "plait", "s", "il", "vous",
                       "et", "ou", "mais", "donc", "car", "ni", "or"}
MOTIF_LIEU = re.compile(
    r"\b(?:a|au|aux|dans|sur|vers|pres de|autour de|en|proche de|pres d|du cote de|cote de|proximite de|alentours de)\s+"
    r"(?:(?:la|le|l)\s+)?(?:(?:ville|commune|region|quartier|village|district)\s+)?(?:(?:de|du|des|d)\s*['\s]\s*)?"
    r"([a-z][a-z' \-]{1,40})")
SUGGESTIONS_PAR_DEFAUT = ["Un restaurant à Antananarivo", "Un hôtel à Nosy Be", "Où cultive-t-on la vanille ?"]
MESSAGE_PRESENTATION = ("Je suis l'assistant Connectéo. Je peux répondre à vos questions et vous aider à réfléchir, "
                        "rédiger, expliquer ou rechercher des informations. Pour Madagascar, je peux aussi trouver "
                        "des lieux, services et ressources vérifiables, avec carte et images quand elles existent. "
                        "Que puis-je faire pour vous ?")


# --- Sessions -------------------------------------------------------------------------------------------------------
@dataclass
class Session:
    id: str
    historique: list[dict] = field(default_factory=list)       # {"role": "user" | "assistant", "text": str}
    lieux: list[dict] = field(default_factory=list)            # derniers lieux proposés
    contexte: dict = field(default_factory=dict)               # ex. {"categorie": "restaurant", "lieu": "Antananarivo"}
    requetes: OrderedDict = field(default_factory=OrderedDict)  # requete_id -> id_resultat (évite les doublons)
    maj: float = field(default_factory=time.monotonic)
    verrou_tour: threading.Lock = field(default_factory=threading.Lock)


_sessions: OrderedDict[str, Session] = OrderedDict()
_verrou_sessions = threading.Lock()
_evenements: dict[str, threading.Event] = {}


def _purger_les_sessions(maintenant: float):
    for identifiant in [i for i, s in _sessions.items() if maintenant - s.maj > config.CHAT_DUREE_SESSION_EN_SECONDES]:
        _sessions.pop(identifiant, None)

    while len(_sessions) > config.CHAT_SESSIONS_MAX:
        _sessions.popitem(last=False)


def obtenir_session(identifiant: str | None) -> Session:
    identifiant = identifiant if identifiant and re.fullmatch(r"[A-Za-z0-9_-]{8,64}", identifiant) else None

    with _verrou_sessions:
        maintenant = time.monotonic()
        _purger_les_sessions(maintenant)
        session = _sessions.get(identifiant) if identifiant else None

        if session is None:
            session = Session(id=identifiant or "s-" + secrets.token_hex(8))
            _sessions[session.id] = session

        session.maj = maintenant
        _sessions.move_to_end(session.id)

        return session


def lire_historique(identifiant: str) -> list[dict] | None:
    with _verrou_sessions:
        session = _sessions.get(identifiant)

    return None if session is None else list(session.historique)


def oublier_la_session(identifiant: str) -> bool:
    with _verrou_sessions:
        return _sessions.pop(identifiant, None) is not None


# --- Compréhension du message --------------------------------------------------------------------------------------
def nettoyer_message(texte: str) -> str:
    texte = unicodedata.normalize("NFC", str(texte or "")).replace("’", "'")
    texte = re.sub(r"[\x00-\x1f\x7f]", " ", texte)

    return re.sub(r"\s+", " ", texte).strip()[:config.CHAT_TAILLE_MAX_MESSAGE]


def _mots(texte: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", retirer_accents(texte).lower().replace("'", " "))


def detecter_urgence(message: str) -> bool:
    return bool(set(_mots(message)) & {retirer_accents(mot).lower() for mot in config.URGENCE_MOTS})


def est_une_formule_de_politesse(message: str) -> bool:
    mots = _mots(message)

    return bool(mots) and all(mot in MOTS_DE_POLITESSE for mot in mots) and len(mots) <= 8


def extraire_le_lieu(message: str) -> str | None:
    """Le lieu cité après « à », « dans », « sur »... (« restaurant dans la ville d'Antananarivo » -> Antananarivo)."""
    message = unicodedata.normalize("NFC", message).replace("’", "'")
    sans_accents = retirer_accents(message).lower()
    resultat = None

    # Les marqueurs les plus précis passent avant « près de ». Sinon une phrase comme
    # « près de la plage ... du côté de Nosy Be » est capturée depuis « plage » et masque la vraie localité.
    marqueur_precis = re.search(
        r"\b(?:du cote de|cote de|aux alentours de|dans la ville de|dans la commune de)\s+([a-z][a-z' \-]{1,40})",
        sans_accents,
    )
    if marqueur_precis:
        debut, fin = marqueur_precis.span(1)
        mots = message[debut:fin].strip(" -'").split()
        while mots and retirer_accents(mots[-1]).lower().strip("'") in MOTS_DE_FIN_DE_LIEU:
            mots.pop()
        candidat = " ".join(mots).strip(" -'")
        if candidat and not poi_osm.detecter_categorie(candidat):
            return candidat.title() if candidat.islower() else candidat

    for correspondance in MOTIF_LIEU.finditer(sans_accents):
        debut, fin = correspondance.span(1)
        mots = message[debut:fin].strip(" -'").split()

        while mots and retirer_accents(mots[-1]).lower().strip("'") in MOTS_DE_FIN_DE_LIEU:
            mots.pop()

        candidat = " ".join(mots).strip(" -'")

        if candidat and not poi_osm.detecter_categorie(candidat):
            resultat = candidat

    return resultat.title() if resultat and resultat.islower() else resultat


def _analyser_par_regles(message: str, session: Session) -> tuple[AnalyseTour, bool]:
    """Retourne (analyse, sure). `sure` = inutile de demander à l'IA."""
    mots = set(_mots(message))
    categorie = poi_osm.detecter_categorie(message)
    attente = session.contexte.get("en_attente")

    if est_une_formule_de_politesse(message):
        return AnalyseTour(action="discuter"), True

    # Une personne n'est jamais un lieu. Cette règle passe avant toute similarité géographique
    # afin que « Andry Rasoanaivo » ne remonte pas une commune comme « Andohamandry ».
    personne_explicite = bool(mots & MOTS_DE_PERSONNE)
    question_personne = bool(re.search(
        r"\b(?:connais(?:\s+tu|sez\s+vous)?|qui\s+est|qui\s+etait|parle\s+moi\s+de)\b",
        retirer_accents(message).lower().replace("'", " "),
    ))
    if personne_explicite or (question_personne and not categorie):
        return AnalyseTour(action="discuter"), True

    if mots & MOTS_DE_CARTE or ({"voir", "montre", "montrez", "afficher"} & mots and {"lieux", "resultats", "liste"} & mots):
        return AnalyseTour(action="carte"), True

    # Demande géographique explicite sans catégorie : « des lieux à Isalo »,
    # « endroits à visiter à Morondava ». Elle ne doit pas tomber dans une
    # clarification générique ni dépendre de la disponibilité du modèle.
    if not categorie and mots & {"lieu", "lieux", "endroit", "endroits", "visiter", "decouvrir", "touristique", "touristiques"}:
        lieu = extraire_le_lieu(message)
        if lieu:
            return AnalyseTour(action="chercher", type_recherche="etablissement", categorie="site touristique",
                               lieu=lieu, requete=f"sites touristiques à visiter {lieu}"), True

    if categorie:
        lieu = extraire_le_lieu(message)

        if not lieu and session.contexte.get("lieu") and len(mots) <= 8:
            lieu = session.contexte["lieu"]                      # « et un hôtel ? » : on garde la ville précédente

        libelle = poi_osm.libelle_de_la_categorie(categorie).lower()

        if lieu:
            return AnalyseTour(action="chercher", type_recherche="etablissement", categorie=categorie, lieu=lieu,
                               requete=f"{libelle} {lieu}"), True

        # Sans ville : pour une phrase courte (« j'ai faim », « je cherche une pharmacie »), l'IA n'apprendrait rien de
        # plus et coûterait de longues secondes : on demande la ville tout de suite. Seule une longue phrase, où la
        # ville peut être formulée autrement, est confiée à l'IA.
        return AnalyseTour(action="preciser", type_recherche="etablissement", categorie=categorie,
                           question=_question_de_ville(categorie)), len(mots) <= MOTS_MAX_PHRASE_SIMPLE

    if attente and len(mots) <= 5:                              # réponse à « Dans quelle ville ? »
        lieu = extraire_le_lieu(message) or message
        libelle = poi_osm.libelle_de_la_categorie(attente["categorie"]).lower()

        return AnalyseTour(action="chercher", type_recherche="etablissement", categorie=attente["categorie"], lieu=lieu,
                           requete=f"{libelle} {lieu}"), True

    analyse = _analyse_de_secours(message, session)
    # Un produit connu (cacao, vanille, riz...) : recherche par thème directe, l'IA n'apporterait rien
    # Les demandes non géographiques sont directement confiées à l'agent généraliste :
    # un second appel de classification ferait attendre l'utilisateur sans améliorer la réponse.
    sure = (analyse.action == "discuter"
            or (analyse.type_recherche == "theme" and len(mots) <= MOTS_MAX_PHRASE_SIMPLE + 2))

    return analyse, sure


def _analyse_de_secours(message: str, session: Session) -> AnalyseTour:
    """Quand l'IA n'est pas disponible : on ne fait aucune supposition hasardeuse."""
    mots_utiles = extraire_mots_utiles(message)

    if not mots_utiles:
        return AnalyseTour(action="discuter")

    est_un_produit = any(len(trouver_groupe_synonymes(mot)) > 1 for mot in mots_utiles)

    if est_un_produit:
        return AnalyseTour(action="chercher", type_recherche="theme", requete=message)

    # Un nom propre court seul est très probablement un lieu (« Antananarivo », « Nosy Be »).
    # L'analyse IA peut toujours corriger cette hypothèse lorsqu'elle est disponible.
    if len(mots_utiles) <= 3 and message[:1].isupper():
        return AnalyseTour(action="chercher", type_recherche="lieu", lieu=message.strip(), requete=message)

    if session.historique:                                      # suite de conversation que les règles ne comprennent pas
        return AnalyseTour(action="discuter")

    return AnalyseTour(action="discuter")


def _question_de_ville(categorie: str) -> str:
    libelle = poi_osm.libelle_de_la_categorie(categorie).lower()

    return f"Dans quelle ville ou quel quartier cherchez-vous {_article_indefini(libelle)} ?"


def _article_indefini(libelle: str) -> str:
    feminins = ("pharmacie", "agence", "banque", "école", "plage", "boulangerie", "station", "poste", "police")

    return f"une {libelle}" if libelle.startswith(feminins) else f"un {libelle}"


def analyser(message: str, session: Session, historique: list[dict], meta: dict) -> AnalyseTour:
    analyse, sure = _analyser_par_regles(message, session)

    if sure:
        meta["comprehension"] = "regles"
        return analyse

    lieux_precedents = [lieu["nom"] for lieu in session.lieux[:6]]
    resultat = agent_ia.demander_json_detaille(construire_messages_analyse(historique[-8:], message, lieux_precedents),
                                               AnalyseTour, max_tokens=120, temperature=0.1,
                                               delai_max=config.CHAT_DELAI_COMPREHENSION_EN_SECONDES)

    if resultat is None:
        meta["comprehension"] = "regles"
        return analyse

    analyse_ia, reponse = resultat
    meta["comprehension"], meta["fournisseur_ia"] = "ia", reponse.fournisseur

    if analyse_ia.action == "chercher" and not (analyse_ia.requete or "").strip():
        analyse_ia.requete = message

    return analyse_ia


# --- Recherche ---------------------------------------------------------------------------------------------------------
def _attendre_la_recherche(requete: str, avertissements: list[str], delai: float) -> dict:
    # Le chat rédige lui-même sa réponse : le résumé IA de la recherche serait un second appel au modèle, inutile
    resultat = recherche.lancer_recherche(requete, avec_resume_ia=False)
    limite = time.monotonic() + delai

    # Les résultats provisoires sont déjà vérifiés et cartographiables. Ne pas bloquer l'interface pendant les
    # enrichissements de fond (web, rédaction, indexation).
    if resultat.get("lieux"):
        avertissements += resultat.get("avertissements") or []
        return resultat

    while resultat["statut"] == "en_cours" and time.monotonic() < limite:
        time.sleep(0.4)
        resultat = resultat_json.lire_resultat(resultat["id_resultat"]) or resultat

    if resultat["statut"] == "en_cours":
        avertissements.append("La recherche complète n'a pas fini : résultats partiels.")

    avertissements += resultat.get("avertissements") or []

    return resultat


def _est_un_lieu_administratif(lieu: dict) -> bool:
    return lieu.get("niveau") in NIVEAUX_ADMINISTRATIFS and lieu.get("origine") in ("referentiel", "base_connaissances")


def _decrire_la_localite(lieu: dict) -> str | None:
    """Pour un lieu sans adresse : « commune, district X, région Y », qui distingue « Antananarivo I » de « II »."""
    parties = []

    if lieu.get("niveau") in NIVEAUX_ADMINISTRATIFS:
        parties.append(lieu["niveau"].capitalize())

    if lieu.get("district"):
        parties.append(f"district {lieu['district']}")

    if lieu.get("region"):
        parties.append(f"région {lieu['region']}")

    return ", ".join(parties) or None


def rechercher(analyse: AnalyseTour, message: str, avertissements: list[str], meta: dict) -> tuple[list[dict], dict]:
    """Retourne (lieux au format de sortie, informations : requête, catégorie, lieu, source)."""
    categorie = (poi_osm.detecter_categorie(analyse.categorie) or poi_osm.detecter_categorie(analyse.requete)
                 or (poi_osm.detecter_categorie(message) if analyse.type_recherche == "etablissement" else None))
    est_un_etablissement = categorie is not None and analyse.type_recherche != "theme"
    infos = {"requete": (analyse.requete or message).strip(), "categorie": categorie, "lieu": analyse.lieu,
             "intention": "lieu" if analyse.type_recherche in ("etablissement", "lieu") else "theme"}
    lieux: list[dict] = []

    if est_un_etablissement and config.POI_ACTIF and analyse.lieu:
        debut = time.monotonic()

        try:
            etablissements, _ = poi_osm.chercher_etablissements(categorie, analyse.lieu)
            lieux = [lieu.vers_dictionnaire_sortie() for lieu in etablissements]
        except poi_osm.PoiIndisponible as erreur:
            avertissements.append(f"OpenStreetMap : {erreur}")

        meta.setdefault("etapes_ms", {})["etablissements"] = int((time.monotonic() - debut) * 1000)
        infos["source"] = "osm"

    if est_un_etablissement and len(lieux) >= 3:
        return lieux, infos

    # Pas (assez) d'établissements précis : base de connaissances + web, sans les zones administratives
    debut = time.monotonic()
    delai = DELAI_COMPLEMENT_WEB_EN_SECONDES if lieux else DELAI_RECHERCHE_COMPLETE_EN_SECONDES
    resultat = _attendre_la_recherche(infos["requete"], avertissements, delai)
    meta.setdefault("etapes_ms", {})["recherche"] = int((time.monotonic() - debut) * 1000)
    trouves = [] if resultat["statut"] in ("clarification_necessaire", "erreur") else resultat.get("lieux", [])

    if est_un_etablissement:
        trouves = [lieu for lieu in trouves if not _est_un_lieu_administratif(lieu)]

    vus = {normaliser_nom(lieu["nom"]) for lieu in lieux}
    lieux += [lieu for lieu in trouves if normaliser_nom(lieu["nom"]) not in vus]
    infos["source"] = infos.get("source") or (resultat.get("reponse") or {}).get("source_principale")
    infos["sources"] = resultat.get("sources") or []
    infos["intention"] = (resultat.get("requete") or {}).get("intention") or infos["intention"]

    for lieu in lieux:
        if not lieu.get("adresse"):
            lieu["adresse"] = _decrire_la_localite(lieu)

    return lieux[:config.NOMBRE_LIEUX_MAX], infos


# --- Rédaction de la réponse ----------------------------------------------------------------------------------------------
def _decrire_un_lieu_pour_le_modele(numero: int, lieu: dict) -> str:
    morceaux = [f"[{numero}] {lieu['nom']}"]

    if lieu.get("categorie"):
        morceaux.append(f"catégorie : {lieu['categorie']}")

    localisation = lieu.get("adresse") or ", ".join(p for p in (lieu.get("district"), lieu.get("region")) if p)

    if localisation:
        morceaux.append(f"adresse : {localisation}")

    for cle, etiquette in (("telephone", "téléphone"), ("horaires", "horaires")):
        if lieu.get(cle):
            morceaux.append(f"{etiquette} : {lieu[cle]}")

    note = lieu.get("note_google")

    if note:
        morceaux.append(f"note Google {note['note']}/5" + (f" ({note['nombre_avis']} avis)" if note.get("nombre_avis") else ""))

    if lieu.get("description") and lieu["description"] != lieu.get("categorie"):
        morceaux.append(f"description : {lieu['description'][:160]}")

    return " ; ".join(morceaux)


def construire_le_bloc_de_resultats(infos: dict | None, lieux: list[dict], avertissements: list[str],
                                    note: str = "") -> str:
    if infos is None:
        return "AUCUNE RECHERCHE EFFECTUÉE (simple discussion) : ne cite aucun lieu précis. " + note

    cherche = " — ".join(partie for partie in (infos.get("categorie") or infos["requete"], infos.get("lieu")) if partie)

    if not lieux:
        return f"RECHERCHE EFFECTUÉE : « {cherche} ». Aucun lieu trouvé."

    lignes = [f"RECHERCHE EFFECTUÉE : « {cherche} ». {len(lieux)} lieu(x) trouvé(s), du plus pertinent au moins pertinent :"]
    lignes += [_decrire_un_lieu_pour_le_modele(numero, lieu) for numero, lieu in enumerate(lieux[:config.CHAT_LIEUX_MAX], start=1)]

    if any("partiel" in avertissement for avertissement in avertissements):
        lignes.append("Les résultats sont partiels : la recherche complète n'a pas pu aboutir à temps.")

    return "\n".join(lignes)


def _nettoyer_les_suggestions(suggestions: list[str]) -> list[str]:
    propres = []

    for suggestion in suggestions:
        suggestion = re.sub(r"\s+", " ", str(suggestion)).strip()

        if suggestion and len(suggestion) <= 40 and "http" not in suggestion.lower() and suggestion not in propres:
            propres.append(suggestion)

    return propres[:3]


def _message_valide(texte: str) -> bool:
    return bool(texte) and len(texte) <= 1500 and "http" not in texte.lower()


def rediger_avec_l_ia(message: str, historique: list[dict], bloc: str, meta: dict) -> ReponseChat | None:
    resultat = agent_ia.demander_json_detaille(construire_messages_chat(historique[-config.CHAT_MESSAGES_MAX_EN_MEMOIRE:],
                                                                        message, bloc),
                                               ReponseChat, max_tokens=160, temperature=0.3,
                                               delai_max=config.CHAT_DELAI_REDACTION_EN_SECONDES)

    if resultat is None:
        return None

    reponse, informations = resultat
    reponse.message = reponse.message.strip().replace("**", "")

    if not _message_valide(reponse.message):
        return None

    meta["fournisseur_ia"] = informations.fournisseur
    meta["modele_ia"] = informations.modele
    reponse.suggestions = _nettoyer_les_suggestions(reponse.suggestions)

    return reponse


def repondre_librement(message: str, historique: list[dict], meta: dict) -> ReponseChat | None:
    """Conversation générale : texte naturel et outils LangChain, sans l'enfermer dans le schéma des lieux."""
    messages = [{
        "role": "system",
        "content": (
            "Tu es Connectéo, un assistant généraliste utile, clair et précis, comparable à un assistant "
            "génératif moderne. Réponds directement à toute demande légitime : connaissances générales, personnes, "
            "explications, rédaction, résumé, traduction, idées, calcul simple et conseils. Utilise la recherche web "
            "seulement si l'information est récente, incertaine ou si l'utilisateur demande une vérification. "
            "N'invente jamais une source. Réponds dans la langue de l'utilisateur, sans parler de ton architecture."
        ),
    }]
    messages += [{"role": tour["role"], "content": tour["text"]}
                 for tour in historique[-config.CHAT_MESSAGES_MAX_EN_MEMOIRE:]
                 if tour.get("role") in ("user", "assistant") and tour.get("text")]
    messages.append({"role": "user", "content": message})
    resultat = agent_ia.completer(messages, max_tokens=400, temperature=0.3,
                                  delai_max=config.CHAT_DELAI_REDACTION_EN_SECONDES)

    if resultat is None or not resultat.texte.strip() or len(resultat.texte) > 5000:
        return None

    meta["fournisseur_ia"], meta["modele_ia"] = resultat.fournisseur, resultat.modele
    return ReponseChat(message=resultat.texte.strip(), suggestions=[])


def reponse_de_secours(analyse: AnalyseTour, message: str, infos: dict | None, lieux: list[dict]) -> ReponseChat:
    """Texte rédigé sans IA : poli, exact, et qui ne dit que ce qui a été trouvé."""
    if infos is None:
        mots = set(_mots(message))

        if mots & MOTS_DE_REMERCIEMENT:
            return ReponseChat(message="Avec plaisir ! N'hésitez pas si vous souhaitez chercher autre chose.",
                               suggestions=SUGGESTIONS_PAR_DEFAUT[:2])

        if est_une_formule_de_politesse(message):
            return ReponseChat(message=f"Bonjour ! {MESSAGE_PRESENTATION}", suggestions=SUGGESTIONS_PAR_DEFAUT)

        return ReponseChat(message="Je peux répondre à cette demande, mais mon modèle local est momentanément "
                                   "indisponible. Reformulez brièvement votre question ou réessayez dans un instant.",
                           suggestions=SUGGESTIONS_PAR_DEFAUT[:2])

    quoi = (poi_osm.libelle_de_la_categorie(infos["categorie"]).lower() if infos.get("categorie") else None)
    ou = f" à {infos['lieu']}" if infos.get("lieu") else ""

    if not lieux:
        cherche = f"{_article_indefini(quoi)}{ou}" if quoi else f"« {infos['requete']} »"

        return ReponseChat(message=f"Je n'ai trouvé aucun résultat pour {cherche} pour le moment. Souhaitez-vous essayer "
                                   "un autre quartier, une autre ville ou une autre catégorie ?")

    noms = [lieu["nom"] for lieu in lieux[:3]]
    liste = noms[0] if len(noms) == 1 else ", ".join(noms[:-1]) + " et " + noms[-1]
    pluriel = "résultat" if len(lieux) == 1 else "résultats"

    return ReponseChat(message=f"J'ai trouvé {len(lieux)} {pluriel}{ou}, notamment {liste}. Souhaitez-vous plus de détails "
                               "sur l'un d'eux ?", suggestions=["Voir sur la carte"])


# --- Assemblage du résultat ----------------------------------------------------------------------------------------------
def _enveloppe(*, identifiant: str, session_id: str, statut: str, date_creation: str, message: str, texte_original: str,
               intention: str | None = None, mots_cles: list[str] | None = None, lieux: list[dict] | None = None,
               sources: list[dict] | None = None, suggestions: list[str] | None = None, garder_resultats: bool = False,
               ouvrir_carte: bool = False, urgence: dict | None = None, avertissements: list[str] | None = None,
               erreur: str | None = None, source_principale: str = "aucune", meta: dict | None = None,
               requete_info: dict | None = None) -> dict:
    lieux = lieux or []

    return {
        "id_resultat": identifiant,
        "session_id": session_id,
        "statut": statut,
        "date_creation": date_creation,
        "date_fin": None if statut == "en_cours" else resultat_json.maintenant(),
        "message": message,
        "suggestions": suggestions or [],
        "garder_resultats": garder_resultats,
        "ouvrir_carte": ouvrir_carte,
        "requete": {"texte_original": texte_original, "intention": intention, "mots_cles": mots_cles or [],
                    "categorie": (requete_info or {}).get("categorie"), "lieu": (requete_info or {}).get("lieu")},
        "reponse": {"texte": message, "source_principale": source_principale,
                    "recherche_google": "non_necessaire"},
        "lieux": lieux,
        "carte": resultat_json.calculer_carte_depuis_sorties(lieux),
        "sources": sources or [],
        "clarification": None,
        "urgence": urgence,
        "avertissements": list(dict.fromkeys(avertissements or [])),
        "erreur": erreur,
        "meta": meta or {},
    }


def _produire_le_resultat(session: Session, historique: list[dict], message: str, identifiant: str, date_creation: str,
                          avertissements: list[str], meta: dict) -> dict:
    base = {"identifiant": identifiant, "session_id": session.id, "date_creation": date_creation,
            "texte_original": message, "avertissements": avertissements, "meta": meta}

    # 1) Urgence : réponse immédiate, sans IA
    if detecter_urgence(message):
        contacts = config.NUMEROS_D_URGENCE
        texte_contacts = ", ".join(f"{contact['service']} : {contact['numero']}" for contact in contacts)

        if contacts and not config.NUMEROS_D_URGENCE_VERIFIES:
            avertissements.append("Numéros d'urgence à vérifier auprès d'une source officielle (config.py).")

        texte = (f"{config.MESSAGE_URGENCE} {texte_contacts + '.' if texte_contacts else ''} Je peux aussi vous aider à trouver "
                 "un hôpital ou une pharmacie : dites-moi dans quelle ville vous êtes.").replace("  ", " ")
        meta["comprehension"] = "urgence"

        return _enveloppe(statut="urgence", message=texte, garder_resultats=True,
                          suggestions=["Trouver un hôpital", "Trouver une pharmacie"],
                          urgence={"message": config.MESSAGE_URGENCE, "contacts": contacts}, **base)

    # 2) Compréhension
    debut = time.monotonic()
    analyse = analyser(message, session, historique, meta)
    meta.setdefault("etapes_ms", {})["comprehension"] = int((time.monotonic() - debut) * 1000)
    meta["action"] = analyse.action

    # 3) Action
    infos, lieux, ouvrir_carte, garder, note_du_bloc = None, [], False, False, ""

    if analyse.action == "chercher" and not analyse.lieu and poi_osm.detecter_categorie(analyse.categorie or analyse.requete):
        analyse.action = "preciser"                      # un établissement sans ville : on demande la ville
        analyse.categorie = poi_osm.detecter_categorie(analyse.categorie or analyse.requete)

    if analyse.action == "carte":
        if session.lieux:
            lieux, ouvrir_carte = session.lieux, True
            texte = "Voici les lieux sur la carte. Dites-moi si vous souhaitez des précisions sur l'un d'eux."

            return _enveloppe(statut="termine", message=texte, lieux=lieux, ouvrir_carte=True, **base)

        analyse = AnalyseTour(action="discuter")
        garder = True
        note_du_bloc = "L'utilisateur demande la carte, mais aucun lieu n'a encore été proposé : invite-le à décrire ce qu'il cherche."

    elif analyse.action == "preciser":
        categorie = poi_osm.detecter_categorie(analyse.categorie) or poi_osm.detecter_categorie(message)
        question = (analyse.question or "").strip() or (_question_de_ville(categorie) if categorie
                                                        else "Pouvez-vous préciser ce que vous cherchez ?")
        session.contexte["en_attente"] = {"categorie": categorie} if categorie else None
        suggestions = ["Antananarivo", "Toamasina", "Nosy Be"] if categorie else SUGGESTIONS_PAR_DEFAUT

        return _enveloppe(statut="termine", message=question, suggestions=suggestions, garder_resultats=True,
                          requete_info={"categorie": categorie}, **base)

    if analyse.action == "chercher":
        session.contexte["en_attente"] = None
        debut = time.monotonic()
        lieux, infos = rechercher(analyse, message, avertissements, meta)
        meta.setdefault("etapes_ms", {})["recherche_totale"] = int((time.monotonic() - debut) * 1000)

        if infos.get("lieu"):
            session.contexte["lieu"] = infos["lieu"]

        if infos.get("categorie"):
            session.contexte["categorie"] = infos["categorie"]

        debut = time.monotonic()
        nombre_avec_image = recherche_images.enrichir_avec_images(lieux)
        meta.setdefault("etapes_ms", {})["images"] = int((time.monotonic() - debut) * 1000)
        meta["lieux_avec_image"] = nombre_avec_image
    elif analyse.action == "discuter":
        garder = True

    # 4) Réponse rédigée
    bloc = construire_le_bloc_de_resultats(infos, lieux, avertissements, note_du_bloc)
    debut = time.monotonic()
    reponse = (repondre_librement(message, historique, meta) if analyse.action == "discuter" and infos is None
               else rediger_avec_l_ia(message, historique, bloc, meta))
    meta.setdefault("etapes_ms", {})["redaction"] = int((time.monotonic() - debut) * 1000)

    if reponse is None:
        meta.setdefault("fournisseur_ia", "aucun")
        reponse = reponse_de_secours(analyse, message, infos, lieux)

        if note_du_bloc:
            reponse = ReponseChat(message="Je n'ai pas encore de lieu à afficher. Dites-moi ce que vous cherchez, par exemple "
                                          "un restaurant, un hôtel ou une pharmacie dans une ville.",
                                  suggestions=SUGGESTIONS_PAR_DEFAUT)

    if infos and lieux and not any("carte" in s.lower() for s in reponse.suggestions):
        reponse.suggestions = (reponse.suggestions + ["Voir sur la carte"])[:3]

    origines = {lieu.get("origine") for lieu in lieux}
    source_principale = next((o for o in ("google", "osm", "base_connaissances", "referentiel") if o in origines), "aucune")

    return _enveloppe(statut="termine", message=reponse.message, suggestions=reponse.suggestions, lieux=lieux,
                      garder_resultats=garder, ouvrir_carte=ouvrir_carte, source_principale=source_principale,
                      intention=(infos or {}).get("intention"), requete_info=infos, sources=(infos or {}).get("sources"),
                      mots_cles=[mot for mot in extraire_mots_utiles((infos or {}).get("requete", ""))], **base)


# --- Exécution d'un tour -----------------------------------------------------------------------------------------------------
def _executer(session: Session, identifiant: str, message: str, date_creation: str):
    debut = time.monotonic()
    avertissements: list[str] = []
    meta: dict = {}

    try:
        with session.verrou_tour:                          # deux messages de la même session ne se mélangent jamais
            historique = list(session.historique)
            resultat = _produire_le_resultat(session, historique, message, identifiant, date_creation, avertissements, meta)
            session.historique += [{"role": "user", "text": message}, {"role": "assistant", "text": resultat["message"]}]
            session.historique = session.historique[-config.CHAT_MESSAGES_MAX_EN_MEMOIRE * 2:]

            if resultat["lieux"] and not resultat["garder_resultats"]:
                session.lieux = resultat["lieux"]
    except Exception as erreur:  # noqa: BLE001 - un fil d'arrière-plan doit toujours écrire un résultat
        journal.exception("Le tour %s a échoué", identifiant)
        resultat = _enveloppe(identifiant=identifiant, session_id=session.id, statut="erreur", date_creation=date_creation,
                              message="Je rencontre un problème technique. Pouvez-vous réessayer dans un instant ?",
                              texte_original=message, garder_resultats=True, avertissements=avertissements,
                              erreur=str(erreur), meta=meta)

    resultat["meta"]["duree_ms"] = int((time.monotonic() - debut) * 1000)
    resultat_json.ecrire_resultat(resultat)
    evenement = _evenements.get(identifiant)

    if evenement:
        evenement.set()


def _arreter_une_attente_trop_longue(session: Session, identifiant: str, message: str, date_creation: str):
    """Garantit qu'un client ne relit jamais indéfiniment un résultat resté en cours."""
    time.sleep(config.CHAT_DUREE_MAX_EN_SECONDES)
    resultat = resultat_json.lire_resultat(identifiant)

    if not resultat or resultat.get("statut") != "en_cours":
        return

    resultat = _enveloppe(
        identifiant=identifiant, session_id=session.id, statut="termine", date_creation=date_creation,
        message="La recherche prend plus de temps que prévu. Précisez le lieu ou le service recherché pour obtenir une réponse plus rapide.",
        texte_original=message, garder_resultats=True,
        avertissements=["Délai maximal de traitement atteint ; la réponse longue a été interrompue."],
        meta={"duree_ms": int(config.CHAT_DUREE_MAX_EN_SECONDES * 1000), "delai_depasse": True})
    resultat_json.ecrire_resultat(resultat)
    evenement = _evenements.get(identifiant)

    if evenement:
        evenement.set()


def _attendre_le_resultat(identifiant: str, delai: float) -> dict | None:
    evenement = _evenements.get(identifiant)

    if evenement:
        evenement.wait(delai)

    resultat = resultat_json.lire_resultat(identifiant)

    if resultat and resultat["statut"] != "en_cours":
        _evenements.pop(identifiant, None)

    return resultat


def traiter_message(message: str, session_id: str | None = None, requete_id: str | None = None,
                    attente_max: float | None = None) -> dict:
    """Point d'entrée de POST /chat. Lève ValueError si le message est vide."""
    message = nettoyer_message(message)

    if not message:
        raise ValueError("Message vide")

    session = obtenir_session(session_id)
    requete_id = requete_id if requete_id and re.fullmatch(r"[A-Za-z0-9_-]{6,64}", requete_id) else None
    delai = config.CHAT_ATTENTE_MAX_EN_SECONDES if attente_max is None else attente_max

    with _verrou_sessions:
        if requete_id and requete_id in session.requetes:       # même requête renvoyée (rechargement, nouvel essai réseau)
            identifiant = session.requetes[requete_id]
            deja_lancee = True
        else:
            identifiant = f"{resultat_json.creer_identifiant_resultat(message)}-{secrets.token_hex(4)}"
            deja_lancee = False

            if requete_id:
                session.requetes[requete_id] = identifiant

                while len(session.requetes) > 50:
                    session.requetes.popitem(last=False)

    if not deja_lancee:
        date_creation = resultat_json.maintenant()
        _evenements[identifiant] = threading.Event()
        resultat_json.ecrire_resultat(_enveloppe(
            identifiant=identifiant, session_id=session.id, statut="en_cours", date_creation=date_creation,
            message="Je réfléchis à votre demande...", texte_original=message, garder_resultats=True))
        threading.Thread(target=_executer, args=(session, identifiant, message, date_creation), daemon=True).start()
        threading.Thread(target=_arreter_une_attente_trop_longue,
                         args=(session, identifiant, message, date_creation), daemon=True).start()

    resultat = _attendre_le_resultat(identifiant, delai)

    return resultat or {"id_resultat": identifiant, "session_id": session.id, "statut": "erreur",
                        "message": "Résultat introuvable.", "erreur": "Résultat introuvable"}
