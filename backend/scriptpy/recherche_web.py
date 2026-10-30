from __future__ import annotations

import ipaddress
import logging
import re
import socket
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

import config
from outils import coordonnees_valides, extraire_mots_utiles, normaliser_nom, retirer_accents

journal = logging.getLogger("recherche_web")

URL_GOOGLE = "https://www.googleapis.com/customsearch/v1"
NOMBRE_RESULTATS_WEB = 6
DELAI_RECHERCHE_EN_SECONDES = 15
DELAI_PAGE_EN_SECONDES = 8
NATURES_ADRESSE_PRECISES = {
    "village", "hamlet", "suburb", "neighbourhood", "quarter", "isolated_dwelling", "amenity", "tourism",
    "natural", "historic", "shop", "leisure", "building", "man_made", "road",
}


class RechercheGoogleIndisponible(Exception):
    pass


@dataclass
class PageWeb:
    titre: str
    url: str
    texte: str


def expliquer_erreur_google(reponse: httpx.Response) -> str:
    try:
        detail = reponse.json().get("error", {})
        message, raison = detail.get("message", ""), (detail.get("errors") or [{}])[0].get("reason", "")
    except ValueError:
        message, raison = reponse.text[:150], ""

    conseils = {
        400: "clé API ou identifiant de moteur (GOOGLE_CX) invalide",
        403: "API « Custom Search » non activée pour cette clé, ou quota dépassé (100 requêtes gratuites par jour)",
        429: "trop de requêtes : quota Google dépassé",
    }

    return f"Google a répondu {reponse.status_code} ({raison or 'erreur'}) : {conseils.get(reponse.status_code, 'erreur inattendue')}. {message}".strip()


class FournisseurIndisponible(Exception):
    pass


def _recherche_searxng(question: str, nombre: int) -> list[dict]:
    """SearXNG installé sur la machine : gratuit, sans clé, sans quota (voir LISEZMOI_RECHERCHE.md)."""
    if not config.URL_SEARXNG:
        raise FournisseurIndisponible("SEARXNG_URL non définie")

    try:
        reponse = httpx.get(f"{config.URL_SEARXNG}/search", timeout=DELAI_RECHERCHE_EN_SECONDES,
                            params={"q": question, "format": "json", "language": "fr", "safesearch": 1})
    except httpx.HTTPError as erreur:
        raise FournisseurIndisponible(f"SearXNG injoignable ({erreur})") from erreur

    if reponse.status_code == 403:
        raise FournisseurIndisponible("SearXNG refuse le format JSON : ajouter « json » dans search.formats de settings.yml")

    if reponse.status_code != 200:
        raise FournisseurIndisponible(f"SearXNG a répondu {reponse.status_code}")

    return [{"title": r.get("title", ""), "link": r.get("url", ""), "snippet": r.get("content", "")}
            for r in reponse.json().get("results", [])[:nombre]]


def _recherche_brave(question: str, nombre: int) -> list[dict]:
    if not config.CLE_API_BRAVE:
        raise FournisseurIndisponible("BRAVE_API_KEY non définie")

    try:
        reponse = httpx.get("https://api.search.brave.com/res/v1/web/search", timeout=DELAI_RECHERCHE_EN_SECONDES,
                            headers={"X-Subscription-Token": config.CLE_API_BRAVE, "Accept": "application/json"},
                            params={"q": question, "count": nombre, "country": "ALL", "search_lang": "fr"})
    except httpx.HTTPError as erreur:
        raise FournisseurIndisponible(f"Brave injoignable ({erreur})") from erreur

    if reponse.status_code != 200:
        raise FournisseurIndisponible(f"Brave a répondu {reponse.status_code} (clé invalide ou quota dépassé)")

    return [{"title": r.get("title", ""), "link": r.get("url", ""), "snippet": r.get("description", "")}
            for r in reponse.json().get("web", {}).get("results", [])[:nombre]]


def _recherche_duckduckgo(question: str, nombre: int) -> list[dict]:
    """Sans clé ni installation de serveur (pip install ddgs). Moins stable : DuckDuckGo peut limiter le débit."""
    try:
        from ddgs import DDGS
    except ImportError as erreur:
        raise FournisseurIndisponible("module ddgs absent (pip install ddgs)") from erreur

    try:
        resultats = DDGS(timeout=DELAI_RECHERCHE_EN_SECONDES).text(question, region="fr-fr", max_results=nombre)
    except Exception as erreur:  # noqa: BLE001 - la bibliothèque lève plusieurs types d'erreurs
        raise FournisseurIndisponible(f"DuckDuckGo a échoué ({erreur})") from erreur

    return [{"title": r.get("title", ""), "link": r.get("href", ""), "snippet": r.get("body", "")} for r in resultats]


def _recherche_google(question: str, nombre: int) -> list[dict]:
    if not (config.CLE_API_GOOGLE and config.IDENTIFIANT_MOTEUR_GOOGLE):
        raise FournisseurIndisponible("GOOGLE_API_KEY et GOOGLE_CX non définies")

    try:
        reponse = httpx.get(URL_GOOGLE, timeout=DELAI_RECHERCHE_EN_SECONDES, params={
            "key": config.CLE_API_GOOGLE, "cx": config.IDENTIFIANT_MOTEUR_GOOGLE, "q": question,
            "num": min(nombre, 10), "gl": "mg", "lr": "lang_fr"})
    except httpx.HTTPError as erreur:
        raise FournisseurIndisponible(f"Google injoignable ({erreur})") from erreur

    if reponse.status_code != 200:
        raise FournisseurIndisponible(expliquer_erreur_google(reponse))

    return [{"title": r.get("title", ""), "link": r.get("link", ""), "snippet": r.get("snippet", "")}
            for r in reponse.json().get("items", [])]


def _recherche_wikipedia(question: str, nombre: int) -> list[dict]:
    """API officielle de Wikipédia : gratuite, sans clé (la requête doit porter un User-Agent identifiable)."""
    resultats = []

    for langue in ("fr", "en"):
        try:
            reponse = httpx.get(f"https://{langue}.wikipedia.org/w/api.php", timeout=DELAI_RECHERCHE_EN_SECONDES,
                                headers={"User-Agent": config.IDENTIFIANT_APPLICATION},
                                params={"action": "query", "list": "search", "srsearch": question,
                                        "srlimit": nombre, "format": "json"})
        except httpx.HTTPError as erreur:
            raise FournisseurIndisponible(f"Wikipédia injoignable ({erreur})") from erreur

        if reponse.status_code != 200:
            raise FournisseurIndisponible(f"Wikipédia a répondu {reponse.status_code}")

        for r in reponse.json().get("query", {}).get("search", []):
            titre = r.get("title", "")
            extrait = BeautifulSoup(r.get("snippet", ""), "html.parser").get_text()
            resultats.append({"title": titre, "snippet": extrait,
                              "link": f"https://{langue}.wikipedia.org/wiki/{titre.replace(' ', '_')}"})

        if len(resultats) >= nombre:
            break

    return resultats[:nombre]


def _recherche_tavily(question: str, nombre: int) -> list[dict]:
    """API Tavily : résultats et images liées à la question (les images servent aux photos des réponses)."""
    if not config.CLE_API_TAVILY:
        raise FournisseurIndisponible("TAVILY_API_CLE non définie")

    try:
        reponse = httpx.post("https://api.tavily.com/search", timeout=DELAI_RECHERCHE_EN_SECONDES,
                             headers={"Authorization": f"Bearer {config.CLE_API_TAVILY}"},
                             json={"query": question, "search_depth": "basic", "max_results": nombre, "include_images": True})
    except httpx.HTTPError as erreur:
        raise FournisseurIndisponible(f"Tavily injoignable ({type(erreur).__name__})") from erreur

    if reponse.status_code != 200:
        raise FournisseurIndisponible(f"Tavily a répondu {reponse.status_code} (clé invalide ou quota mensuel atteint)")

    donnees = reponse.json()
    images = [image if isinstance(image, str) else image.get("url") for image in donnees.get("images") or []]
    resultats = [{"title": r.get("title", ""), "link": r.get("url", ""), "snippet": r.get("content", "")}
                 for r in donnees.get("results", [])[:nombre]]

    if resultats:
        resultats[0]["images"] = [image for image in images if image]

    return resultats


FOURNISSEURS = {"tavily": _recherche_tavily, "searxng": _recherche_searxng, "brave": _recherche_brave, "wikipedia": _recherche_wikipedia,
                "duckduckgo": _recherche_duckduckgo, "google": _recherche_google}


def _interroger_web(texte_requete: str) -> list[dict]:
    """Essaie les fournisseurs dans l'ordre de config.ORDRE_FOURNISSEURS_RECHERCHE jusqu'au premier qui répond."""
    question = texte_requete if "madagascar" in texte_requete.lower() else f"{texte_requete} Madagascar"
    echecs = []

    for nom in config.ORDRE_FOURNISSEURS_RECHERCHE:
        fournisseur = FOURNISSEURS.get(nom)

        if fournisseur is None:
            continue

        try:
            resultats = [r for r in fournisseur(question, NOMBRE_RESULTATS_WEB) if r["link"]]
        except FournisseurIndisponible as erreur:
            echecs.append(f"{nom} : {erreur}")
            continue

        if resultats:
            journal.info("Recherche web faite avec %s (%d résultats)", nom, len(resultats))
            return resultats

        echecs.append(f"{nom} : aucun résultat")

    raise RechercheGoogleIndisponible(" | ".join(echecs) or "aucun fournisseur configuré")


_executeur_assistant = ThreadPoolExecutor(max_workers=12, thread_name_prefix="web-assistant")
# ddgs (moteur bing) colle parfois plusieurs titres : « … | LinkedInAndry Rasoanaivo - Google Scholar… »
MOTIF_TITRES_COLLES = re.compile(r"(?<=[a-zà-ÿ.)\]])(?=[A-ZÀ-Ý][a-zà-ÿ]+ [A-ZÀ-Ý])")


def nettoyer_titre(titre: str) -> str:
    titre = " ".join((titre or "").split())

    return MOTIF_TITRES_COLLES.split(titre, maxsplit=1)[0].strip()[:160]


def resultat_pertinent(question: str, texte: str) -> bool:
    """Tous les noms propres de la question doivent figurer dans le résultat (une page qui ne cite que « Rasoanaivo »
    ne répond pas à « Andry Rasoanaivo ») ; pour les autres mots, la moitié suffit (« président actuel »)."""
    texte_normalise = f" {normaliser_nom(texte)} "
    noms_propres = {normaliser_nom(mot) for mot in re.findall(r"\b[A-ZÀ-Ý][\w'-]{2,}", question)}
    noms_propres = {mot for mot in noms_propres if mot and mot not in {"MADAGASCAR"}}
    autres = [mot for mot in extraire_mots_utiles(question) if len(mot) >= 3 and mot not in noms_propres]

    if any(f" {mot} " not in texte_normalise for mot in noms_propres):
        return False

    # mots ordinaires : début de mot, pour accepter le pluriel (« président » / « présidents »)
    return not autres or sum(1 for mot in autres if f" {mot}" in texte_normalise) * 2 >= len(autres)


def chercher_resultats_web(question: str, nombre: int, delai: float) -> list[dict]:
    """Résultats web (titre, url, extrait) pour l'assistant, bornés dans le temps. Ne lève jamais d'exception.

    Tous les fournisseurs configurés sont interrogés en parallèle (un moteur lent ne retarde pas un moteur rapide) ;
    les résultats sont fusionnés dans l'ordre de config.ORDRE_FOURNISSEURS_RECHERCHE, sans doublon."""
    fin = time.monotonic() + max(0.5, delai)
    futurs = {nom: _executeur_assistant.submit(FOURNISSEURS[nom], question, nombre)
              for nom in config.ORDRE_FOURNISSEURS_RECHERCHE if nom in FOURNISSEURS}
    en_attente = set(futurs.values())

    # On s'arrête dès que les moteurs déjà terminés donnent assez de résultats pertinents (mesuré : Tavily 3 à 9 s,
    # DuckDuckGo jusqu'à 18 s) : un moteur lent ne retarde plus la réponse.
    while en_attente and time.monotonic() < fin:
        _, en_attente = wait(en_attente, timeout=fin - time.monotonic(), return_when=FIRST_COMPLETED)

        if len(_fusionner_resultats(question, nombre, futurs, en_attente, journaliser=False)) >= min(3, nombre):
            break

    return _fusionner_resultats(question, nombre, futurs, en_attente, journaliser=True)


def _fusionner_resultats(question: str, nombre: int, futurs: dict, en_attente: set, journaliser: bool) -> list[dict]:
    resultats: list[dict] = []
    urls_vues: set[str] = set()

    for nom, futur in futurs.items():
        if futur in en_attente:
            if journaliser:
                journal.info("Recherche web de l'assistant : %s trop lent", nom)
            continue

        try:
            trouves = futur.result()
        except Exception as erreur:  # noqa: BLE001 - un fournisseur en panne n'empêche pas les autres de répondre
            if journaliser:
                journal.debug("Recherche web de l'assistant : %s indisponible (%s)", nom, type(erreur).__name__)
            continue

        for trouve in trouves:
            url = (trouve.get("link") or "").strip()
            titre, extrait = nettoyer_titre(trouve.get("title")), " ".join((trouve.get("snippet") or "").split())[:400]

            if (url.startswith(("http://", "https://")) and url not in urls_vues
                    and resultat_pertinent(question, f"{titre} {extrait} {url}")):
                urls_vues.add(url)
                resultats.append({"titre": titre or url, "url": url, "extrait": extrait, "fournisseur": nom,
                                  "images": trouve.get("images") or []})

    return resultats[:nombre]


def adresse_publique(url: str) -> bool:
    """Vrai si l'URL est http(s) et que son hôte ne désigne ni la machine ni un réseau privé (protection SSRF)."""
    try:
        partie = urlparse(url)

        if partie.scheme not in ("http", "https") or not partie.hostname:
            return False

        adresses = {info[4][0] for info in socket.getaddrinfo(partie.hostname, None)}
    except (ValueError, OSError):
        return False

    for adresse in adresses:
        ip = ipaddress.ip_address(adresse.split("%")[0])

        if not ip.is_global:
            return False

    return bool(adresses)


def lire_page_publique(url: str, delai: float, caracteres_max: int = 4000) -> str:
    """Texte principal d'une page web publique, borné en taille et en temps. Chaîne vide si illisible."""
    if not adresse_publique(url):
        return ""

    futur = _executeur_assistant.submit(_lire_texte_de_la_page, url, [])

    try:
        texte = futur.result(timeout=max(1.0, delai))
    except Exception:  # noqa: BLE001 - délai dépassé ou page illisible
        return ""

    return texte[:caracteres_max]


def tester_google() -> tuple[bool, str]:
    """Nom conservé pour compatibilité : teste la chaîne complète des fournisseurs de recherche web."""
    echecs = []

    for nom in config.ORDRE_FOURNISSEURS_RECHERCHE:
        fournisseur = FOURNISSEURS.get(nom)

        if fournisseur is None:
            continue

        try:
            if fournisseur("Madagascar", 1):
                return True, f"fournisseur actif : {nom}" + (f" (indisponibles avant : {'; '.join(echecs)})" if echecs else "")

            echecs.append(f"{nom} : aucun résultat")
        except FournisseurIndisponible as erreur:
            echecs.append(f"{nom} : {erreur}")

    return False, "aucun fournisseur disponible -> " + " | ".join(echecs)


def _extraire_passage_pertinent(texte_page: str, mots_cles: list[str]) -> str:
    texte_sans_accents = retirer_accents(texte_page).lower()
    debut = 0

    for mot_cle in mots_cles:
        position = texte_sans_accents.find(mot_cle.lower())

        if position != -1:
            debut = max(0, position - 200)
            break

    return texte_page[debut:debut + config.CARACTERES_MAX_PAR_PAGE]


def _lire_texte_de_la_page(url: str, mots_cles: list[str]) -> str:
    try:
        reponse = httpx.get(url, timeout=DELAI_PAGE_EN_SECONDES, follow_redirects=True,
                            headers={"User-Agent": config.IDENTIFIANT_APPLICATION})

        if "text/html" not in reponse.headers.get("content-type", ""):
            return ""

        page = BeautifulSoup(reponse.text, "html.parser")

        for balise in page(["script", "style", "nav", "footer", "header", "aside", "form"]):
            balise.decompose()

        return _extraire_passage_pertinent(" ".join(page.get_text(" ").split()), mots_cles)
    except httpx.HTTPError as erreur:
        journal.info("Page illisible %s : %s", url, erreur)
        return ""


def chercher_pages_sur_google(texte_requete: str, mots_cles: list[str]) -> list[PageWeb]:
    resultats = _interroger_web(texte_requete)
    resultats = resultats[:config.NOMBRE_PAGES_WEB_LUES]

    if not resultats:
        return []

    with ThreadPoolExecutor(max_workers=len(resultats)) as executeur:
        textes_des_pages = list(executeur.map(lambda resultat: _lire_texte_de_la_page(resultat["link"], mots_cles),
                                              resultats))

    return [PageWeb(titre=resultat.get("title", ""), url=resultat["link"],
                    texte=f"{resultat.get('snippet', '')}\n{texte_page}".strip())
            for resultat, texte_page in zip(resultats, textes_des_pages)]


class LimiteurDeDebit:
    def __init__(self, secondes_entre_deux_appels: float):
        self.secondes_entre_deux_appels = secondes_entre_deux_appels
        self._verrou = threading.Lock()
        self._instant_du_dernier_appel = 0.0

    def attendre_son_tour(self):
        with self._verrou:
            attente = self.secondes_entre_deux_appels - (time.monotonic() - self._instant_du_dernier_appel)

            if attente > 0:
                time.sleep(attente)

            self._instant_du_dernier_appel = time.monotonic()


# Nominatim impose au maximum une requête par seconde
_limiteur_nominatim = LimiteurDeDebit(1.1)


def geocoder_avec_nominatim(nom: str, district: str | None, region: str | None):
    adresse = ", ".join(partie for partie in (nom, district, region, "Madagascar") if partie)
    _limiteur_nominatim.attendre_son_tour()

    try:
        reponse = httpx.get(config.URL_NOMINATIM, timeout=10, headers={"User-Agent": config.IDENTIFIANT_APPLICATION},
                            params={"q": adresse, "format": "jsonv2", "limit": 1, "countrycodes": "mg",
                                    "accept-language": "fr"})
        reponse.raise_for_status()
        resultats = reponse.json()
    except httpx.HTTPError as erreur:
        journal.warning("Géocodage impossible pour %r : %s", adresse, erreur)
        return None

    if not resultats:
        return None

    latitude, longitude = float(resultats[0]["lat"]), float(resultats[0]["lon"])

    if not coordonnees_valides(latitude, longitude):
        return None

    precision = "precis" if resultats[0].get("addresstype") in NATURES_ADRESSE_PRECISES else "centroide"

    return latitude, longitude, precision