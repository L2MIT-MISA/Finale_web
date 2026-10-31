from __future__ import annotations

import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from urllib.parse import quote, unquote, urljoin, urlparse

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
            journal.debug("Recherche d'images indisponible : %s", erreur)

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


def _texte_sans_balises(html: str | None) -> str:
    return " ".join(BeautifulSoup(html or "", "html.parser").get_text(" ").split())[:80]


def _coordonnees(lieu: dict) -> tuple[float, float] | None:
    coordonnees = lieu.get("coordonnees") or {}

    if coordonnees.get("latitude") is None or coordonnees.get("longitude") is None:
        return None

    return float(coordonnees["latitude"]), float(coordonnees["longitude"])


def _est_un_etablissement(lieu: dict) -> bool:
    return lieu.get("origine") == "osm" and "touristique" not in (lieu.get("categorie") or "").lower()


def _images_commons(lieu: dict, delai: float) -> list[dict]:
    """Photos libres de Wikimedia Commons prises autour du lieu. Établissement : 80 m et nom dans le titre du fichier
    (sinon une photo de la rue voisine passerait pour l'établissement) ; site ou localité : quelques kilomètres."""
    position = _coordonnees(lieu)

    if not config.IMAGES_COMMONS or position is None:
        return []

    etablissement = _est_un_etablissement(lieu)
    rayon = 80 if etablissement else (2000 if lieu.get("niveau") == "site" else 5000)

    try:
        reponse = httpx.get("https://commons.wikimedia.org/w/api.php", timeout=delai,
                            headers={"User-Agent": config.IDENTIFIANT_APPLICATION},
                            params={"action": "query", "format": "json", "generator": "geosearch",
                                    "ggscoord": f"{position[0]}|{position[1]}", "ggsradius": rayon, "ggslimit": 12,
                                    "ggsnamespace": 6, "prop": "imageinfo", "iiprop": "url|extmetadata",
                                    "iiurlwidth": 640, "iiextmetadatafilter": "Artist|LicenseShortName"})
        pages = reponse.json().get("query", {}).get("pages", {}) if reponse.status_code == 200 else {}
    except (httpx.HTTPError, ValueError):
        return []

    images = []

    for page in sorted(pages.values(), key=lambda page: page.get("index", 99)):
        titre = page.get("title", "")
        info = (page.get("imageinfo") or [{}])[0]
        url = url_image_valide(info.get("thumburl"))

        if not url or not re.search(r"\.(jpe?g|png|webp)$", titre, re.I):
            continue

        if etablissement and not texte_correspond_au_nom(lieu.get("nom") or "", titre):
            continue

        meta = info.get("extmetadata") or {}
        auteur = _texte_sans_balises((meta.get("Artist") or {}).get("value"))
        licence = (meta.get("LicenseShortName") or {}).get("value") or ""
        credit = ", ".join(partie for partie in (auteur, licence) if partie)
        images.append({"url": url, "legende": f"Photo : {credit + ' — ' if credit else ''}Wikimedia Commons"})

    return images


def _images_mapillary(lieu: dict, delai: float) -> list[dict]:
    position = _coordonnees(lieu)

    if not config.IMAGES_MAPILLARY_JETON or position is None or not _est_un_etablissement(lieu):
        return []

    try:
        reponse = httpx.get("https://graph.mapillary.com/images", timeout=delai,
                            headers={"Authorization": f"OAuth {config.IMAGES_MAPILLARY_JETON}"},
                            params={"fields": "id,thumb_1024_url", "lat": position[0], "lng": position[1],
                                    "radius": 50, "limit": 2})
        donnees = reponse.json().get("data", []) if reponse.status_code == 200 else []
    except (httpx.HTTPError, ValueError):
        return []

    return [{"url": url, "legende": "Vue de la rue — Mapillary"}
            for url in (url_image_valide(image.get("thumb_1024_url")) for image in donnees) if url]


def _images_google_places(lieu: dict, delai: float) -> list[dict]:
    """Photos Google Maps de l'établissement. Conditions de Google : auteur crédité, aucune mise en cache."""
    position = _coordonnees(lieu)
    nom = lieu.get("nom") or ""

    if not config.IMAGES_GOOGLE_PLACES_CLE or position is None:
        return []

    try:
        reponse = httpx.post("https://places.googleapis.com/v1/places:searchText", timeout=delai,
                             headers={"X-Goog-Api-Key": config.IMAGES_GOOGLE_PLACES_CLE,
                                      "X-Goog-FieldMask": "places.displayName,places.photos"},
                             json={"textQuery": f"{nom}, {lieu.get('district') or lieu.get('region') or ''} Madagascar",
                                   "maxResultCount": 1,
                                   "locationBias": {"circle": {"center": {"latitude": position[0], "longitude": position[1]},
                                                               "radius": 300.0}}})
        place = (reponse.json().get("places") or [{}])[0] if reponse.status_code == 200 else {}
    except (httpx.HTTPError, ValueError):
        return []

    if not texte_correspond_au_nom(nom, (place.get("displayName") or {}).get("text", "")):
        return []

    images = []

    for photo in (place.get("photos") or [])[:2]:
        try:
            media = httpx.get(f"https://places.googleapis.com/v1/{photo['name']}/media", timeout=delai,
                              params={"maxWidthPx": 640, "skipHttpRedirect": "true", "key": config.IMAGES_GOOGLE_PLACES_CLE})
            url = url_image_valide(media.json().get("photoUri")) if media.status_code == 200 else None
        except (httpx.HTTPError, ValueError, KeyError):
            url = None

        if url:
            auteurs = ", ".join(auteur.get("displayName", "") for auteur in photo.get("authorAttributions") or [] if auteur.get("displayName"))
            images.append({"url": url, "legende": f"Photo : {auteurs + ' — ' if auteurs else ''}Google Maps", "google": True})

    return images


# --- Photos d'une réponse générale (« Connais-tu… ? »), comme une recherche Google ------------------------------------
MOTIF_PAGE_WIKIPEDIA = re.compile(r"^https://([a-z]{2,3})\.wikipedia\.org/wiki/([^#?]+)")


def _images_des_pages_wikipedia(requete: str, resultats: list[dict], delai: float) -> list[dict]:
    """Image principale des pages Wikipédia trouvées, seulement si le titre de la page répond à la question
    (pour « le président actuel », la page d'un ancien président est écartée)."""
    import recherche_web

    titres_par_langue: dict[str, list[str]] = {}

    for resultat in resultats:
        correspondance = MOTIF_PAGE_WIKIPEDIA.match(resultat.get("url") or "")

        if correspondance:
            titre = unquote(correspondance.group(2)).replace("_", " ")

            if recherche_web.resultat_pertinent(requete, titre):
                titres_par_langue.setdefault(correspondance.group(1), []).append(titre)

    images = []

    for langue, titres in titres_par_langue.items():
        try:
            reponse = httpx.get(f"https://{langue}.wikipedia.org/w/api.php", timeout=delai,
                                headers={"User-Agent": config.IDENTIFIANT_APPLICATION},
                                params={"action": "query", "format": "json", "titles": "|".join(titres[:10]), "redirects": 1,
                                        "prop": "pageimages", "piprop": "thumbnail", "pithumbsize": 640})
            pages = reponse.json().get("query", {}).get("pages", {}) if reponse.status_code == 200 else {}
        except (httpx.HTTPError, ValueError):
            continue

        ordre = {titre: rang for rang, titre in enumerate(titres)}

        for page in sorted(pages.values(), key=lambda page: ordre.get(page.get("title"), 99)):
            url = url_image_valide((page.get("thumbnail") or {}).get("source"))

            if url:
                images.append({"url": url, "legende": f"Wikipédia — {page.get('title', '')}",
                               "page": f"https://{langue}.wikipedia.org/wiki/{quote(page.get('title', '').replace(' ', '_'))}"})

    return images


def _images_du_web(requete: str, nombre: int, delai: float) -> list[dict]:
    """Recherche d'images : seules celles dont le titre ou l'adresse contient le nom cherché sont gardées."""
    try:
        from ddgs import DDGS

        resultats = DDGS(timeout=max(1, int(delai))).images(requete, region="fr-fr", max_results=15)
    except Exception as erreur:  # noqa: BLE001 - ddgs absent, limité ou en panne : pas d'image plutôt qu'une erreur
        journal.debug("Recherche d'images indisponible : %s", type(erreur).__name__)
        return []

    images = []

    for resultat in resultats:
        url = url_image_valide(resultat.get("thumbnail") or resultat.get("image"))
        page = resultat.get("url") or ""

        if url and texte_correspond_au_nom(requete, f"{resultat.get('title', '')} {page}") and len(images) < nombre:
            images.append({"url": url, "legende": f"Image trouvée sur le web — {urlparse(page).hostname or ''}".strip(" —"),
                           "page": page if page.startswith(("http://", "https://")) else None})

    return images


def images_pour_une_reponse(requete: str, resultats: list[dict], nombre: int = 4, delai: float | None = None) -> list[dict]:
    """Photos à montrer sous une réponse générale : Wikipédia d'abord (fiable, sous licence libre), puis le web.
    Mieux vaut aucune photo qu'une photo d'une autre personne."""
    if not config.IMAGES_ACTIVES or not requete:
        return []

    fin = time.monotonic() + (config.IMAGES_DELAI_TOTAL_EN_SECONDES if delai is None else delai)
    noms_propres = [mot for mot in re.findall(r"\b[A-ZÀ-Ý][\w'-]{2,}", requete) if normaliser_nom(mot) != "MADAGASCAR"]
    # Images fournies par l'API de recherche (Tavily) : seulement pour un nom propre, comme la recherche d'images
    images_de_la_recherche = [{"url": url, "legende": "Image trouvée sur le web (Tavily)", "page": None}
                              for resultat in resultats for url in map(url_image_valide, resultat.get("images") or []) if url]
    images = (images_de_la_recherche if noms_propres else []) + _images_des_pages_wikipedia(requete, resultats, min(config.IMAGES_DELAI_REQUETE_EN_SECONDES, max(0.5, fin - time.monotonic())))
    reste = fin - time.monotonic()

    # Recherche d'images sur le web seulement pour un nom propre (« Marc Ravalomanana ») : pour une question descriptive
    # (« le président actuel »), un mot comme « actuel » suffirait à retenir la photo d'une autre personne.
    if noms_propres and len(images) < nombre and reste > 1:
        urls = {image["url"] for image in images}
        images += [image for image in _images_du_web(requete, nombre - len(images), reste) if image["url"] not in urls]

    return images[:nombre]


# --- Orchestration --------------------------------------------------------------------------------------------------
def _cle(lieu: dict) -> str:
    return f"{normaliser_nom(lieu.get('nom'))}|{normaliser_nom(lieu.get('district') or lieu.get('adresse') or lieu.get('region'))}"


def _chercher_pour_un_lieu(lieu: dict, fin: float | None = None, google_autorise: bool = False) -> list[dict]:
    """Images trouvées pour un lieu, dans l'ordre de confiance, jusqu'à IMAGES_PAR_LIEU et avant l'instant `fin`."""
    nom = lieu.get("nom") or ""
    localite = lieu.get("district") or lieu.get("region") or ""
    fin = time.monotonic() + config.IMAGES_DELAI_TOTAL_EN_SECONDES if fin is None else fin
    voulues = max(1, config.IMAGES_PAR_LIEU - len(lieu.get("images") or []))
    images: list[dict] = []

    def unique(url: str | None, legende: str | None) -> list[dict]:
        return [{"url": url, "legende": legende}] if url else []

    sources = [lambda delai: unique(_image_du_site(lieu.get("site_web")), "Photo : site de l'établissement")]

    if _est_un_etablissement(lieu):
        if google_autorise:
            sources.append(lambda delai: _images_google_places(lieu, delai))

        sources += [lambda delai: _images_mapillary(lieu, delai), lambda delai: _images_commons(lieu, delai),
                    lambda delai: unique(_image_depuis_une_recherche(nom, localite), "Image trouvée sur le web"),
                    lambda delai: unique(_image_wikipedia(nom), "Photo : Wikipédia")]
    else:
        sources += [lambda delai: _images_commons(lieu, delai),
                    lambda delai: unique(_image_wikipedia(nom), "Photo : Wikipédia"),
                    lambda delai: unique(_image_depuis_une_recherche(nom, localite), "Image trouvée sur le web")]

    for source in sources:
        reste = fin - time.monotonic()

        if reste < 0.5 or len(images) >= voulues:
            break

        for image in source(min(config.IMAGES_DELAI_REQUETE_EN_SECONDES, reste)):
            if image["url"] not in {deja["url"] for deja in images}:
                images.append(image)

    return images[:voulues]


def _lire_le_cache(cle: str) -> list[dict] | None:
    with _verrou:
        entree = _cache.get(cle)

    if entree is None:
        return None

    age = time.monotonic() - entree[0]
    duree = config.IMAGES_DUREE_CACHE_EN_SECONDES if entree[1] else DUREE_CACHE_SANS_IMAGE_EN_SECONDES

    return entree[1] if age < duree else None


def _appliquer(lieu: dict, trouvees: list[dict]):
    for image in trouvees:
        if image["url"] not in lieu["images"] and len(lieu["images"]) < max(1, config.IMAGES_PAR_LIEU):
            lieu["images"].append(image["url"])
            lieu["images_details"].append({"url": image["url"], "legende": image.get("legende")})

    lieu["image"] = lieu["images"][0] if lieu["images"] else None


def enrichir_avec_images(lieux: list[dict], nombre_max: int | None = None, delai_max: float | None = None) -> int:
    """Ajoute `images`, `image` et `images_details` aux lieux (dictionnaires de sortie). Retourne le nombre de lieux
    qui ont au moins une image."""
    for lieu in lieux:
        lieu["images"] = list(dict.fromkeys(url for url in map(url_image_valide, lieu.get("images") or []) if url))
        lieu["images_details"] = [{"url": url, "legende": None} for url in lieu["images"]]
        lieu["image"] = lieu["images"][0] if lieu["images"] else None

    if not config.IMAGES_ACTIVES:
        return sum(1 for lieu in lieux if lieu["images"])

    nombre_max = config.IMAGES_NOMBRE_LIEUX if nombre_max is None else nombre_max
    delai_max = config.IMAGES_DELAI_TOTAL_EN_SECONDES if delai_max is None else delai_max
    fin = time.monotonic() + max(0.5, delai_max - 0.3)
    google_restants = config.IMAGES_GOOGLE_PLACES_PAR_RECHERCHE if config.IMAGES_GOOGLE_PLACES_CLE else 0
    a_traiter = []

    for lieu in lieux[:nombre_max]:
        if len(lieu["images"]) >= config.IMAGES_PAR_LIEU:
            continue

        en_cache = _lire_le_cache(_cle(lieu))

        if en_cache is not None:
            _appliquer(lieu, en_cache)
        else:
            google_autorise = google_restants > 0 and _est_un_etablissement(lieu)
            google_restants -= 1 if google_autorise else 0
            a_traiter.append((lieu, google_autorise))

    if a_traiter:
        executeur = ThreadPoolExecutor(max_workers=min(6, len(a_traiter)))
        futurs = {executeur.submit(_chercher_pour_un_lieu, lieu, fin, google_autorise): lieu for lieu, google_autorise in a_traiter}
        termines, _ = wait(futurs, timeout=delai_max)
        executeur.shutdown(wait=False, cancel_futures=True)       # une source trop lente ne bloque jamais la réponse

        for futur in termines:
            lieu = futurs[futur]

            try:
                trouvees = futur.result()
            except Exception:  # noqa: BLE001 - une image manquante ne doit jamais faire échouer la recherche
                journal.warning("Recherche d'image échouée pour un lieu")
                continue

            with _verrou:
                # Les photos Google ne sont jamais mises en cache (conditions d'utilisation de Google Places)
                _cache[_cle(lieu)] = (time.monotonic(), [image for image in trouvees if not image.get("google")])

            _appliquer(lieu, trouvees)

    return sum(1 for lieu in lieux if lieu["images"])
