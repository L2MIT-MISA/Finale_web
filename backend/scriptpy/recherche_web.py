from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

import config
from outils import coordonnees_valides, retirer_accents

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


FOURNISSEURS = {"searxng": _recherche_searxng, "brave": _recherche_brave, "wikipedia": _recherche_wikipedia,
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