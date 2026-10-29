"""Établissements précis (restaurants, hôtels, agences de voyage...) depuis OpenStreetMap, sans clé d'API.

Pourquoi : le référentiel PostgreSQL ne contient que des zones administratives (« Antananarivo I », « Antananarivo II »).
Pour « un restaurant à Antananarivo », l'utilisateur veut le NOM EXACT de l'établissement avec sa vraie position.
Les coordonnées viennent directement d'OpenStreetMap : rien n'est inventé ni déduit par le modèle.

Étapes : lieu cité -> Nominatim (centre + emprise) -> Overpass (établissements nommés autour du centre) -> classement.
"""
from __future__ import annotations

import functools
import logging
import math
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

import config
from modeles import Lieu
from outils import coordonnees_valides, normaliser_nom, retirer_accents
from recherche_web import _limiteur_nominatim

journal = logging.getLogger("poi_osm")


class PoiIndisponible(Exception):
    pass


# libelle : nom affiché ; mots : façons de le demander (sans accents, minuscules) ; filtres : étiquettes OpenStreetMap
CATEGORIES: dict[str, dict] = {
    # « j'ai faim », « noana aho » (malgache) : un besoin exprimé désigne aussi la catégorie, sans passer par l'IA
    "restaurant": {"libelle": "Restaurant", "mots": ["restaurant", "resto", "restau", "gargote", "hotely", "manger", "dejeuner",
                                                     "diner", "faim", "affame", "affamee", "noana", "mihinana", "sakafo",
                                                     "petit dejeuner", "bouffer", "grignoter", "repas"],
                   "filtres": ['["amenity"~"^(restaurant|fast_food|food_court)$"]']},
    "cafe": {"libelle": "Café", "mots": ["cafe", "cafeteria", "salon de the", "coffee", "soif", "boire un verre", "mangetaheta"],
             "filtres": ['["amenity"="cafe"]']},
    "bar": {"libelle": "Bar", "mots": ["bar", "pub", "boite de nuit", "discotheque", "nightclub"],
            "filtres": ['["amenity"~"^(bar|pub|nightclub)$"]']},
    "hotel": {"libelle": "Hôtel", "mots": ["hotel", "hebergement", "auberge", "gite", "lodge", "bungalow", "guesthouse",
                                           "guest house", "chambre d hote", "dormir", "logement", "motel", "resort",
                                           "fatigue", "fatiguee", "sommeil", "nuit", "matory"],
              "filtres": ['["tourism"~"^(hotel|guest_house|hostel|motel|apartment|chalet|resort)$"]']},
    "agence de voyage": {"libelle": "Agence de voyage",
                         "mots": ["agence de voyage", "agence de voyages", "agence voyage", "voyagiste", "tour operateur",
                                  "tour operator", "agence touristique", "agence de tourisme", "travel agency"],
                         "filtres": ['["shop"="travel_agency"]', '["office"~"^(travel_agent|tour_operator)$"]']},
    "pharmacie": {"libelle": "Pharmacie", "mots": ["pharmacie", "pharmacies", "pharmacy"],
                  "filtres": ['["amenity"="pharmacy"]']},
    "hopital": {"libelle": "Hôpital ou centre de santé",
                "mots": ["hopital", "clinique", "csb", "dispensaire", "centre de sante", "medecin", "docteur", "hospital",
                         "malade", "soigner", "consultation"],
                "filtres": ['["amenity"~"^(hospital|clinic|doctors)$"]', '["healthcare"~"^(hospital|clinic|centre)$"]']},
    "banque": {"libelle": "Banque", "mots": ["banque", "bank", "distributeur", "atm"],
               "filtres": ['["amenity"~"^(bank|atm)$"]']},
    "supermarche": {"libelle": "Supermarché", "mots": ["supermarche", "supermarket", "epicerie", "hypermarche", "magasin"],
                    "filtres": ['["shop"~"^(supermarket|convenience|mall|department_store)$"]']},
    "ecole": {"libelle": "École", "mots": ["ecole", "lycee", "college", "universite", "school"],
              "filtres": ['["amenity"~"^(school|college|university)$"]']},
    "station-service": {"libelle": "Station-service", "mots": ["station service", "station essence", "essence", "carburant"],
                        "filtres": ['["amenity"="fuel"]']},
    "musee": {"libelle": "Musée", "mots": ["musee", "museum", "galerie"], "filtres": ['["tourism"~"^(museum|gallery)$"]']},
    "plage": {"libelle": "Plage", "mots": ["plage", "beach"], "filtres": ['["natural"="beach"]']},
    "marche": {"libelle": "Marché", "mots": ["marche", "market"], "filtres": ['["amenity"="marketplace"]']},
    "boulangerie": {"libelle": "Boulangerie", "mots": ["boulangerie", "patisserie", "boulanger"],
                    "filtres": ['["shop"~"^(bakery|pastry)$"]']},
    "poste": {"libelle": "Bureau de poste", "mots": ["poste", "bureau de poste"], "filtres": ['["amenity"="post_office"]']},
    "police": {"libelle": "Police", "mots": ["commissariat", "police", "gendarmerie"],
               "filtres": ['["amenity"="police"]']},
    "aeroport": {"libelle": "Aéroport", "mots": ["aeroport", "airport", "aerodrome"],
                  "filtres": ['["aeroway"="aerodrome"]']},
    "site touristique": {
        "libelle": "Site touristique",
        "mots": ["lieu", "lieux", "endroit", "endroits", "site touristique", "sites touristiques",
                 "attraction", "attractions", "a visiter", "visiter", "point de vue"],
        "filtres": [
            '["tourism"~"^(attraction|viewpoint|museum|gallery|information)$"]',
            '["leisure"="nature_reserve"]',
            '["boundary"="national_park"]',
            '["natural"~"^(peak|waterfall|cave_entrance|beach|rock)$"]',
            '["historic"]',
        ],
    },
}
LIBELLES_CUISINE = {"malagasy": "cuisine malgache", "french": "cuisine française", "italian": "cuisine italienne",
                    "chinese": "cuisine chinoise", "indian": "cuisine indienne", "pizza": "pizzas", "burger": "burgers",
                    "seafood": "fruits de mer", "regional": "cuisine régionale", "african": "cuisine africaine",
                    "asian": "cuisine asiatique", "coffee_shop": "café", "grill": "grillades", "japanese": "cuisine japonaise",
                    "vietnamese": "cuisine vietnamienne", "thai": "cuisine thaïlandaise", "sushi": "sushis"}
DELAI_OVERPASS_EN_SECONDES = 12
DELAI_DE_GRACE_OVERPASS_EN_SECONDES = 3
URL_PHOTON = "https://photon.komoot.io/api/"
DUREE_CACHE_EN_SECONDES = 1800
MOTIF_TELEPHONE = re.compile(r"^[+\d][\d\s().\-/;+]{3,40}$")
MOTIF_FICHIER_COMMONS = re.compile(r"^File:(.+\.(?:jpe?g|png|webp|gif))$", re.I)


# --- Reconnaissance de la catégorie dans le texte ------------------------------------------------------------------
def _normaliser_pour_mots(texte: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", retirer_accents(texte or "").lower()).strip() + " "


def detecter_categorie(texte: str | None) -> str | None:
    """Retourne la clé de CATEGORIES (ex. « restaurant ») si le texte parle d'un établissement, sinon None."""
    texte_normalise = _normaliser_pour_mots(texte or "")
    meilleur, longueur_max = None, 0

    for cle, definition in CATEGORIES.items():
        for mot in definition["mots"]:
            if f" {mot} " in texte_normalise or f" {mot}s " in texte_normalise:
                # « lieu/endroit » est un repli générique et ne doit jamais écraser
                # une intention précise déjà trouvée (« faim » -> restaurant, « dormir » -> hôtel).
                prioritaire = cle != "site touristique" or meilleur is None
                if prioritaire and len(mot) > longueur_max:      # les expressions précises l'emportent sur les mots courts
                    meilleur, longueur_max = cle, len(mot)

    return meilleur


def libelle_de_la_categorie(cle: str) -> str:
    return CATEGORIES[cle]["libelle"]


# --- Position du lieu cité (Nominatim) -----------------------------------------------------------------------------
@functools.lru_cache(maxsize=256)
def _geocoder_le_lieu(lieu: str) -> tuple[float, float, float] | None:
    """Retourne (latitude, longitude, rayon en mètres) ; None si le lieu est introuvable à Madagascar."""
    _limiteur_nominatim.attendre_son_tour()

    try:
        reponse = httpx.get(config.URL_NOMINATIM, timeout=10, headers={"User-Agent": config.IDENTIFIANT_APPLICATION},
                            params={"q": f"{lieu}, Madagascar", "format": "jsonv2", "limit": 1, "countrycodes": "mg",
                                    "accept-language": "fr"})
        reponse.raise_for_status()
        resultats = reponse.json()
    except (httpx.HTTPError, ValueError) as erreur:
        raise PoiIndisponible(f"Nominatim injoignable ({type(erreur).__name__})") from erreur

    if not resultats:
        return None

    latitude, longitude = float(resultats[0]["lat"]), float(resultats[0]["lon"])

    if not coordonnees_valides(latitude, longitude):
        return None

    rayon = config.POI_RAYON_PAR_DEFAUT_EN_METRES

    try:
        sud, nord, ouest, est = (float(valeur) for valeur in resultats[0]["boundingbox"])
        hauteur = (nord - sud) * 111_320
        largeur = (est - ouest) * 111_320 * math.cos(math.radians(latitude))
        rayon = math.hypot(hauteur, largeur) / 2
    except (KeyError, ValueError):
        pass

    return latitude, longitude, min(max(rayon, 2000.0), float(config.POI_RAYON_MAX_EN_METRES))


# --- Overpass --------------------------------------------------------------------------------------------------------
def _construire_requete_overpass(cle_categorie: str, latitude: float, longitude: float, rayon: float) -> str:
    zone = f"(around:{int(rayon)},{latitude:.6f},{longitude:.6f})"
    blocs = "".join(f"nwr{filtre}[\"name\"]{zone};" for filtre in CATEGORIES[cle_categorie]["filtres"])

    return f"[out:json][timeout:10];({blocs});out center tags 60;"


def _interroger_overpass(requete: str) -> list[dict]:
    erreurs = []

    for url in config.URLS_OVERPASS:
        try:
            reponse = httpx.post(url, data={"data": requete}, timeout=DELAI_OVERPASS_EN_SECONDES,
                                 headers={"User-Agent": config.IDENTIFIANT_APPLICATION})
        except httpx.HTTPError as erreur:
            erreurs.append(f"{url} : {type(erreur).__name__}")
            continue

        if reponse.status_code != 200:
            erreurs.append(f"{url} : {reponse.status_code}")
            continue

        try:
            return reponse.json().get("elements", [])
        except ValueError:
            erreurs.append(f"{url} : réponse illisible")

    raise PoiIndisponible("Overpass indisponible (" + " | ".join(erreurs) + ")")


# --- Conversion en lieux ----------------------------------------------------------------------------------------------
def _distance_en_metres(latitude_a, longitude_a, latitude_b, longitude_b) -> float:
    x = math.radians(longitude_b - longitude_a) * math.cos(math.radians((latitude_a + latitude_b) / 2))
    y = math.radians(latitude_b - latitude_a)

    return math.hypot(x, y) * 6_371_000


def _adresse(etiquettes: dict) -> str | None:
    rue = " ".join(partie for partie in (etiquettes.get("addr:housenumber"), etiquettes.get("addr:street")) if partie)
    parties = [partie for partie in (rue, etiquettes.get("addr:suburb"), etiquettes.get("addr:city")) if partie]

    return ", ".join(parties) or None


def _image(etiquettes: dict) -> str | None:
    image = (etiquettes.get("image") or "").strip()

    if image.startswith(("http://", "https://")):
        return image

    correspondance = MOTIF_FICHIER_COMMONS.match((etiquettes.get("wikimedia_commons") or "").strip())

    if correspondance:
        nom_fichier = correspondance.group(1).replace(" ", "_")
        return f"https://commons.wikimedia.org/wiki/Special:FilePath/{nom_fichier}?width=640"

    return None


def _site_web(etiquettes: dict) -> str | None:
    site = (etiquettes.get("website") or etiquettes.get("contact:website") or "").strip()

    if not site:
        return None

    return site if site.startswith(("http://", "https://")) else f"https://{site}"


def _telephone(etiquettes: dict) -> str | None:
    telephone = (etiquettes.get("phone") or etiquettes.get("contact:phone") or "").strip()

    return telephone if MOTIF_TELEPHONE.match(telephone) else None


def _decrire(etiquettes: dict, libelle: str) -> str:
    details = []
    cuisines = [LIBELLES_CUISINE.get(c.strip(), c.strip().replace("_", " "))
                for c in (etiquettes.get("cuisine") or "").split(";") if c.strip()]

    if cuisines:
        details.append(", ".join(cuisines[:3]))

    if etiquettes.get("stars", "").strip().isdigit():
        details.append(f"{etiquettes['stars'].strip()} étoiles")

    if etiquettes.get("internet_access") in ("wlan", "yes", "wifi"):
        details.append("Wi-Fi")

    if etiquettes.get("outdoor_seating") == "yes":
        details.append("terrasse")

    if etiquettes.get("takeaway") in ("yes", "only"):
        details.append("vente à emporter")

    return libelle + (" : " + ", ".join(details) if details else "")


def _richesse(etiquettes: dict) -> float:
    """Plus la fiche est complète (et plus l'établissement est notable), plus il est mis en avant."""
    points = 0.0

    for cle, poids in (("phone", 1.0), ("contact:phone", 1.0), ("website", 1.0), ("contact:website", 1.0),
                       ("opening_hours", 1.0), ("addr:street", 0.5), ("cuisine", 0.5), ("stars", 0.5),
                       ("email", 0.3), ("image", 0.5), ("wikimedia_commons", 0.5), ("wikidata", 1.0),
                       ("wikipedia", 1.0), ("internet_access", 0.3)):
        if etiquettes.get(cle):
            points += poids

    return points


def _convertir_element(element: dict, cle_categorie: str, centre: tuple[float, float]) -> tuple[float, Lieu] | None:
    etiquettes = element.get("tags") or {}
    nom = (etiquettes.get("name:fr") or etiquettes.get("name") or "").strip()
    latitude = element.get("lat", (element.get("center") or {}).get("lat"))
    longitude = element.get("lon", (element.get("center") or {}).get("lon"))

    if not nom or latitude is None or longitude is None or not coordonnees_valides(latitude, longitude):
        return None

    libelle = libelle_de_la_categorie(cle_categorie)
    image = _image(etiquettes)
    distance = _distance_en_metres(centre[0], centre[1], latitude, longitude)
    score = _richesse(etiquettes) - distance / 5000.0
    lieu = Lieu(nom=nom, niveau="site", categorie=libelle, description=_decrire(etiquettes, libelle),
                adresse=_adresse(etiquettes), telephone=_telephone(etiquettes), site_web=_site_web(etiquettes),
                horaires=(etiquettes.get("opening_hours") or "").strip()[:200] or None,
                images=[image] if image else [], origine="osm", confiance=0.85,
                source=f"https://www.openstreetmap.org/{element.get('type', 'node')}/{element.get('id')}",
                mots_cles=[cle_categorie, libelle.lower()])
    lieu.definir_coordonnees(float(latitude), float(longitude), "precis")

    return score, lieu


def _depuis_overpass(cle_categorie: str, latitude: float, longitude: float, rayon: float) -> list[tuple[float, Lieu]]:
    elements = _interroger_overpass(_construire_requete_overpass(cle_categorie, latitude, longitude, rayon))

    return [resultat for element in elements
            if (resultat := _convertir_element(element, cle_categorie, (latitude, longitude)))]


# --- Photon (recherche rapide dans les données OpenStreetMap) : secours si Overpass est lent ou en panne ------------
def _etiquettes_photon(cle_categorie: str) -> list[str]:
    etiquettes = []

    for filtre in CATEGORIES[cle_categorie]["filtres"]:
        simple = re.fullmatch(r'\["(\w+)"="(\w+)"\]', filtre)
        multiple = re.fullmatch(r'\["(\w+)"~"\^\(([\w|]+)\)\$"\]', filtre)

        if simple:
            etiquettes.append(f"{simple.group(1)}:{simple.group(2)}")
        elif multiple:
            etiquettes += [f"{multiple.group(1)}:{valeur}" for valeur in multiple.group(2).split("|")]

    return list(dict.fromkeys(etiquettes))[:3]


def _mot_de_recherche_photon(cle_categorie: str) -> str:
    return CATEGORIES[cle_categorie]["mots"][0].split()[0]


def _depuis_photon(cle_categorie: str, latitude: float, longitude: float, rayon: float) -> list[tuple[float, Lieu]]:
    degres_latitude = rayon / 111_320
    degres_longitude = rayon / (111_320 * max(0.2, math.cos(math.radians(latitude))))
    libelle = libelle_de_la_categorie(cle_categorie)
    resultats = []

    def interroger(etiquette: str) -> list[dict]:
        try:
            reponse = httpx.get(URL_PHOTON, timeout=8, headers={"User-Agent": config.IDENTIFIANT_APPLICATION}, params={
                "q": _mot_de_recherche_photon(cle_categorie), "lat": latitude, "lon": longitude, "limit": 30,
                "lang": "fr", "osm_tag": etiquette,
                "bbox": f"{longitude - degres_longitude},{latitude - degres_latitude},"
                        f"{longitude + degres_longitude},{latitude + degres_latitude}"})
            reponse.raise_for_status()

            return reponse.json().get("features", [])
        except (httpx.HTTPError, ValueError) as erreur:
            raise PoiIndisponible(f"Photon indisponible ({type(erreur).__name__})") from erreur

    etiquettes = _etiquettes_photon(cle_categorie)

    if not etiquettes:
        return []

    with ThreadPoolExecutor(max_workers=len(etiquettes)) as executeur:
        lots = list(executeur.map(interroger, etiquettes))

    for entite in (entite for lot in lots for entite in lot):
        proprietes, coordonnees = entite.get("properties", {}), (entite.get("geometry") or {}).get("coordinates") or []

        if len(coordonnees) != 2 or not proprietes.get("name"):
            continue

        longitude_lieu, latitude_lieu = coordonnees

        if not coordonnees_valides(latitude_lieu, longitude_lieu):
            continue

        distance = _distance_en_metres(latitude, longitude, latitude_lieu, longitude_lieu)

        if distance > rayon * 1.1:
            continue

        adresse = ", ".join(partie for partie in (" ".join(p for p in (proprietes.get("housenumber"), proprietes.get("street")) if p),
                                                  proprietes.get("district"), proprietes.get("city")) if partie) or None
        lieu = Lieu(nom=proprietes["name"].strip(), niveau="site", categorie=libelle, description=libelle,
                    adresse=adresse, origine="osm", confiance=0.7, mots_cles=[cle_categorie, libelle.lower()],
                    source=f"https://www.openstreetmap.org/{ {'N': 'node', 'W': 'way', 'R': 'relation'}.get(proprietes.get('osm_type'), 'node') }/{proprietes.get('osm_id')}")
        lieu.definir_coordonnees(float(latitude_lieu), float(longitude_lieu), "precis")
        resultats.append((-distance / 5000.0, lieu))

    return resultats


# --- Orchestration -----------------------------------------------------------------------------------------------------
_cache: dict[tuple[str, str], tuple[float, list[Lieu]]] = {}
_verrou_cache = threading.Lock()


def _attendre(futur, delai: float):
    try:
        return futur.result(timeout=max(0.1, delai)), None
    except Exception as erreur:  # noqa: BLE001 - délai dépassé ou source en panne : l'autre source prend le relais
        return [], erreur


def chercher_etablissements(cle_categorie: str, lieu_cite: str | None) -> tuple[list[Lieu], str | None]:
    """Retourne (lieux classés, nom du lieu cherché). Lève PoiIndisponible si aucune source ne répond à temps."""
    if cle_categorie not in CATEGORIES:
        return [], lieu_cite

    if not lieu_cite or not lieu_cite.strip():
        raise PoiIndisponible("aucun lieu précisé")

    lieu_cite = lieu_cite.strip()
    cle_cache = (cle_categorie, normaliser_nom(lieu_cite))

    with _verrou_cache:
        en_cache = _cache.get(cle_cache)

    if en_cache and time.monotonic() - en_cache[0] < DUREE_CACHE_EN_SECONDES:
        return [lieu.model_copy(deep=True) for lieu in en_cache[1]], lieu_cite

    position = None
    position_est_un_parc = False
    if cle_categorie == "site touristique" and "parc" not in normaliser_nom(lieu_cite).split():
        # « Isalo » peut désigner une localité homonyme très éloignée du parc. Pour une demande
        # touristique, tenter d'abord le parc national évite de chercher autour du mauvais point.
        position = _geocoder_le_lieu(f"Parc national de l'{lieu_cite}")
        position_est_un_parc = position is not None
    position = position or _geocoder_le_lieu(lieu_cite)

    if position is None:
        raise PoiIndisponible(f"lieu « {lieu_cite} » introuvable à Madagascar")

    latitude, longitude, rayon = position
    debut = time.monotonic()
    executeur = ThreadPoolExecutor(max_workers=2)
    futur_photon = executeur.submit(_depuis_photon, cle_categorie, latitude, longitude, rayon)
    futur_overpass = executeur.submit(_depuis_overpass, cle_categorie, latitude, longitude, rayon)
    executeur.shutdown(wait=False)                      # on n'attend pas une source trop lente

    de_photon, erreur_photon = _attendre(futur_photon, config.POI_DELAI_EN_SECONDES)
    # Photon répond vite : s'il a déjà de quoi répondre, Overpass (fiches plus riches) n'a qu'un court délai de grâce
    delai_overpass = config.POI_DELAI_EN_SECONDES - (time.monotonic() - debut)

    if len(de_photon) >= 5:
        delai_overpass = min(delai_overpass, DELAI_DE_GRACE_OVERPASS_EN_SECONDES)

    de_overpass, erreur_overpass = _attendre(futur_overpass, delai_overpass)

    if erreur_photon and erreur_overpass:
        raise PoiIndisponible(f"{erreur_overpass or 'Overpass : délai dépassé'} | {erreur_photon or 'Photon : délai dépassé'}")

    # Overpass (fiches complètes) d'abord, puis ce que Photon a de plus
    vus, convertis = set(), []

    if position_est_un_parc:
        article = "l'" if retirer_accents(lieu_cite[:1]).lower() in "aeiouy" else ""
        parc = Lieu(nom=f"Parc national de {article}{lieu_cite}", niveau="site",
                    categorie=libelle_de_la_categorie(cle_categorie),
                    description=f"Parc national et site touristique autour de {lieu_cite}",
                    origine="osm", confiance=0.9, pertinence=1.0,
                    source="https://www.openstreetmap.org/search?query=" + lieu_cite.replace(" ", "%20"),
                    mots_cles=[cle_categorie, "parc national", lieu_cite.lower()])
        parc.definir_coordonnees(latitude, longitude, "centroide")
        convertis.append(parc)
        vus.add(normaliser_nom(parc.nom))

    for score, lieu in sorted(de_overpass, key=lambda couple: couple[0], reverse=True) + sorted(
            de_photon, key=lambda couple: couple[0], reverse=True):
        cle_nom = normaliser_nom(lieu.nom)

        if cle_nom not in vus:
            vus.add(cle_nom)
            convertis.append(lieu)

        if len(convertis) >= config.POI_NOMBRE_MAX:
            break

    for rang, lieu in enumerate(convertis):
        lieu.pertinence = max(0.5, 0.95 - 0.04 * rang)

    if convertis:
        with _verrou_cache:
            _cache[cle_cache] = (time.monotonic(), [lieu.model_copy(deep=True) for lieu in convertis])

    return convertis, lieu_cite
