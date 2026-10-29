"""Images d'aperçu des lieux (comme les résultats de Google), ajoutées aux lieux avant leur envoi au front.

Principe : mieux vaut AUCUNE image qu'une image qui n'a rien à voir. Une image n'est retenue que si elle vient
  1. d'OpenStreetMap (étiquette image / wikimedia_commons, déjà présente dans le lieu) ;
  2. du site officiel de l'établissement (balise og:image) ;
  3. d'une recherche d'images dont le titre ou l'adresse contient le nom du lieu ;
  4. de Wikipédia (article dont le titre correspond au nom du lieu).
Le front reçoit `images` (liste d'URL https) et `image` (la première). Tout est mis en cache 24 h (y compris l'absence
d'image, 1 h) et limité dans le temps : la réponse du chat ne dépend jamais d'une image lente.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

import config
from outils import normaliser_nom

journal = logging.getLogger("recherche_images")

MOTS_GENERIQUES = {"RESTAURANT", "HOTEL", "AGENCE", "VOYAGE", "VOYAGES", "PHARMACIE", "CHEZ", "LE", "LA", "LES", "DE", "DU",
                   "DES", "ET", "AU", "AUX", "MADAGASCAR", "TANANARIVE", "ANTANANARIVO", "BAR", "CAFE", "THE", "SARL",
                   "TOURS", "TOUR", "LODGE", "RESORT", "SPA", "BANQUE", "ECOLE", "HOPITAL", "CLINIQUE"}
TAILLE_MAX_PAGE_EN_OCTETS = 250_000
TAILLE_MAX_URL = 800
DUREE_CACHE_SANS_IMAGE_EN_SECONDES = 3600

_cache: dict[str, tuple[float, list[str]]] = {}
_verrou = threading.Lock()


# --- Outils --------------------------------------------------------------------------------------------------------
def url_image_valide(url) -> str | None:
    """Garde uniquement les URL web sûres. http est transformé en https (le site peut être servi en https)."""
    if not isinstance(url, str):
        return None

    url = url.strip()

    if not url or len(url) > TAILLE_MAX_URL or any(caractere in url for caractere in " \\\"'<>"):
        return None

    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]

    return reduire_la_taille(url) if url.startswith("https://") else None


def reduire_la_taille(url: str) -> str:
    """Demande une miniature quand l'hébergeur le permet (réseaux mobiles lents : pas d'image de 2500 pixels)."""
    url = re.sub(r"/v1/fill/w_\d+,h_\d+", "/v1/fill/w_480,h_320", url)                    # Wix
    url = re.sub(r"([?&]w=)\d+", r"\g<1>480", url)                                          # Tripadvisor, CDN courants
    url = re.sub(r"([?&]h=)\d+", r"\g<1>-1", url) if "dynamic-media-cdn.tripadvisor" in url else url

    return url


def mots_distinctifs(nom: str) -> list[str]:
    nom_sans_parentheses = re.sub(r"\(.*?\)", " ", nom or "")

    return [mot for mot in normaliser_nom(nom_sans_parentheses).split() if len(mot) >= 3 and mot not in MOTS_GENERIQUES]


def texte_correspond_au_nom(nom: str, texte: str) -> bool:
    """Tous les mots distinctifs du nom (ou au moins les deux tiers s'il y en a plus de trois) sont dans le texte."""
    mots = mots_distinctifs(nom)

    if not mots:
        return False

    texte_normalise = " " + normaliser_nom(texte) + " "
    presents = sum(1 for mot in mots if f" {mot} " in texte_normalise or mot in texte_normalise)
    exiges = len(mots) if len(mots) <= 3 else -(-2 * len(mots) // 3)

    return presents >= exiges


# --- Sources --------------------------------------------------------------------------------------------------------
def _image_du_site(site_web: str | None) -> str | None:
    if not site_web or not site_web.startswith(("http://", "https://")):
        return None

    try:
        with httpx.stream("GET", site_web, timeout=config.IMAGES_DELAI_REQUETE_EN_SECONDES, follow_redirects=True,
                          headers={"User-Agent": config.IDENTIFIANT_APPLICATION}) as reponse:
            if reponse.status_code != 200 or "text/html" not in reponse.headers.get("content-type", ""):
                return None

            contenu = b""

            for morceau in reponse.iter_bytes():
                contenu += morceau

                if len(contenu) >= TAILLE_MAX_PAGE_EN_OCTETS:
                    break

            adresse_finale = str(reponse.url)
    except httpx.HTTPError:
        return None

    page = BeautifulSoup(contenu.decode("utf-8", errors="ignore"), "html.parser")

    for selecteur in ({"property": "og:image"}, {"property": "og:image:secure_url"}, {"name": "twitter:image"}):
        balise = page.find("meta", attrs=selecteur)

        if balise and balise.get("content"):
            url = url_image_valide(urljoin(adresse_finale, balise["content"].strip()))

            if url:
                return url

    return None


def _image_depuis_une_recherche(nom: str, lieu: str) -> str | None:
    requete = f'"{nom}" {lieu} Madagascar'.strip()
    candidats: list[dict] = []

    if config.URL_SEARXNG:
        try:
            reponse = httpx.get(f"{config.URL_SEARXNG}/search", timeout=config.IMAGES_DELAI_REQUETE_EN_SECONDES,
                                params={"q": requete, "format": "json", "categories": "images", "safesearch": 1})

            if reponse.status_code == 200:
                candidats += [{"titre": r.get("title", ""), "page": r.get("url", ""),
                               "image": r.get("thumbnail_src") or r.get("img_src")}
                              for r in reponse.json().get("results", [])[:10]]
        except (httpx.HTTPError, ValueError):
            pass

    if not candidats:
        try:
            from ddgs import DDGS

            resultats = DDGS(timeout=config.IMAGES_DELAI_REQUETE_EN_SECONDES).images(requete, region="fr-fr", max_results=10)
            candidats += [{"titre": r.get("title", ""), "page": r.get("url", ""),
                           "image": r.get("thumbnail") or r.get("image")} for r in resultats]
        except Exception as erreur:  # noqa: BLE001 - ddgs absent, limité ou en panne : on passe à la source suivante
            journal.info("Recherche d'images indisponible : %s", erreur)

    for candidat in candidats:
        url = url_image_valide(candidat["image"])

        if url and texte_correspond_au_nom(nom, f"{candidat['titre']} {candidat['page']}"):
            return url

    return None


def _image_wikipedia(nom: str) -> str | None:
    nom_propre = re.sub(r"\(.*?\)", " ", nom).strip()

    for langue in ("fr", "en"):
        try:
            reponse = httpx.get(f"https://{langue}.wikipedia.org/w/api.php", timeout=config.IMAGES_DELAI_REQUETE_EN_SECONDES,
                                headers={"User-Agent": config.IDENTIFIANT_APPLICATION},
                                params={"action": "query", "format": "json", "generator": "search",
                                        "gsrsearch": f"{nom_propre} Madagascar", "gsrlimit": 3, "prop": "pageimages",
                                        "piprop": "thumbnail", "pithumbsize": 640})

            if reponse.status_code != 200:
                continue

            pages = sorted(reponse.json().get("query", {}).get("pages", {}).values(), key=lambda page: page.get("index", 99))
        except (httpx.HTTPError, ValueError):
            continue

        for page in pages:
            miniature = (page.get("thumbnail") or {}).get("source")
            url = url_image_valide(miniature)

            if url and texte_correspond_au_nom(nom_propre, page.get("title", "")):
                return url

    return None


# --- Orchestration --------------------------------------------------------------------------------------------------
def _cle(lieu: dict) -> str:
    return f"{normaliser_nom(lieu.get('nom'))}|{normaliser_nom(lieu.get('district') or lieu.get('adresse') or lieu.get('region'))}"


def _chercher_pour_un_lieu(lieu: dict) -> list[str]:
    nom = lieu.get("nom") or ""
    localite = lieu.get("district") or lieu.get("region") or ""
    etablissement = lieu.get("origine") == "osm"
    source = _image_du_site(lieu.get("site_web"))

    if source:
        return [source]

    ordre = ((lambda: _image_depuis_une_recherche(nom, localite), lambda: _image_wikipedia(nom)) if etablissement
             else (lambda: _image_wikipedia(nom), lambda: _image_depuis_une_recherche(nom, localite)))

    for essayer in ordre:
        url = essayer()

        if url:
            return [url]

    return []


def _lire_le_cache(cle: str) -> list[str] | None:
    with _verrou:
        entree = _cache.get(cle)

    if entree is None:
        return None

    age = time.monotonic() - entree[0]
    duree = config.IMAGES_DUREE_CACHE_EN_SECONDES if entree[1] else DUREE_CACHE_SANS_IMAGE_EN_SECONDES

    return entree[1] if age < duree else None


def enrichir_avec_images(lieux: list[dict], nombre_max: int | None = None, delai_max: float | None = None) -> int:
    """Ajoute `images` et `image` aux lieux (dictionnaires de sortie). Retourne le nombre de lieux qui ont une image."""
    for lieu in lieux:
        lieu["images"] = [url for url in map(url_image_valide, lieu.get("images") or []) if url]
        lieu["image"] = lieu["images"][0] if lieu["images"] else None

    if not config.IMAGES_ACTIVES:
        return sum(1 for lieu in lieux if lieu["images"])

    nombre_max = config.IMAGES_NOMBRE_LIEUX if nombre_max is None else nombre_max
    delai_max = config.IMAGES_DELAI_TOTAL_EN_SECONDES if delai_max is None else delai_max
    a_traiter = []

    for lieu in lieux[:nombre_max]:
        if lieu["images"]:
            continue

        en_cache = _lire_le_cache(_cle(lieu))

        if en_cache is not None:
            lieu["images"], lieu["image"] = en_cache, (en_cache[0] if en_cache else None)
        else:
            a_traiter.append(lieu)

    if a_traiter:
        executeur = ThreadPoolExecutor(max_workers=min(6, len(a_traiter)))
        futurs = {executeur.submit(_chercher_pour_un_lieu, lieu): lieu for lieu in a_traiter}
        termines, _ = wait(futurs, timeout=delai_max)
        executeur.shutdown(wait=False, cancel_futures=True)       # une source trop lente ne bloque jamais la réponse

        for futur in termines:
            lieu = futurs[futur]

            try:
                images = futur.result()
            except Exception:  # noqa: BLE001 - une image manquante ne doit jamais faire échouer la recherche
                journal.exception("Recherche d'image échouée pour %s", lieu.get("nom"))
                continue

            with _verrou:
                _cache[_cle(lieu)] = (time.monotonic(), images)

            lieu["images"], lieu["image"] = images, (images[0] if images else None)

    return sum(1 for lieu in lieux if lieu["images"])
