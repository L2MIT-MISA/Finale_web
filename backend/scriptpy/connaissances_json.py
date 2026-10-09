from __future__ import annotations

import json
import logging
import re
from datetime import date

import config
from modeles import FragmentConnaissance, Lieu, convertir_en_niveau_valide, convertir_en_precision_valide
from outils import (convertir_en_decimal, convertir_en_entier, coordonnees_valides, corriger_coordonnees, creer_slug,
                    est_vide, extraire_mots_utiles, normaliser_code, normaliser_nom, normaliser_nom_colonne,
                    trouver_groupe_synonymes)

journal = logging.getLogger("connaissances_json")

NOM_DU_PAYS = "MADAGASCAR"
NOMBRE_DE_DECIMALES_D_UN_SITE = 5
MARQUEUR_DE_GEOCODAGE = "GEOLOCALISATION OSM"
MOTIF_LIEN_DE_GEOCODAGE = re.compile(r"\s*;?\s*G[ée]olocalisation OSM\s*:\s*\S+", re.IGNORECASE)
MOTIF_ADRESSE_WEB = re.compile(r"https?://\S+")


def _dossiers_de_connaissances() -> dict:
    return {"lieux": config.DOSSIER_LIEUX_JSON, "produits": config.DOSSIER_PRODUITS_JSON,
            "complementaires": config.DOSSIER_COMPLEMENTAIRES_JSON}


def lister_fichiers_connaissances() -> list[str]:
    noms_fichiers = []

    for nom_dossier, dossier in _dossiers_de_connaissances().items():
        if dossier.exists():
            noms_fichiers.extend(f"{nom_dossier}/{chemin.name}" for chemin in sorted(dossier.glob("*.json")))

    return noms_fichiers


def lire_documents(noms_fichiers: list[str] | None = None) -> list[tuple[str, object]]:
    documents = []

    for nom_fichier in (lister_fichiers_connaissances() if noms_fichiers is None else noms_fichiers):
        try:
            contenu = json.loads((config.DOSSIER_DONNEES / nom_fichier).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erreur:
            journal.warning("Fichier ignoré (%s) : %s", nom_fichier, erreur)
            continue

        documents.append((nom_fichier, contenu))

    return documents


def _liste_de(dictionnaire: dict, cle: str) -> list:
    valeur = dictionnaire.get(cle)
    return valeur if isinstance(valeur, list) else []


def _dictionnaire_de(dictionnaire: dict, cle: str) -> dict:
    valeur = dictionnaire.get(cle)
    return valeur if isinstance(valeur, dict) else {}


def _ajouter_details(*morceaux: str | None) -> str:
    details = [morceau for morceau in morceaux if morceau]
    return f" ({', '.join(details)})" if details else ""


def construire_fragments(nom_fichier: str, contenu) -> list[FragmentConnaissance]:
    if isinstance(contenu, list):
        return construire_fragments_enregistrements(nom_fichier, contenu)

    if isinstance(contenu, dict):
        return construire_fragments_lieu(nom_fichier, contenu)

    return []


def construire_fragments_lieu(nom_fichier: str, document: dict) -> list[FragmentConnaissance]:
    lieu = _dictionnaire_de(document, "lieu")
    nom_lieu = lieu.get("nom")

    if not nom_lieu:
        return []

    niveau = convertir_en_niveau_valide(lieu.get("niveau"))
    a_des_coordonnees = coordonnees_valides(lieu.get("latitude"), lieu.get("longitude"))
    mots_cles_du_document = [normaliser_nom(mot) for mot in _liste_de(document, "tags_recherche")]
    mots_cles_du_lieu = [normaliser_nom(nom_lieu), *extraire_mots_utiles(nom_lieu)]
    champs_communs = {
        "nom_lieu": nom_lieu, "niveau_lieu": niveau,
        "code_lieu": str(lieu["code"]) if lieu.get("code") else None,
        "latitude": convertir_en_decimal(lieu.get("latitude")) if a_des_coordonnees else None,
        "longitude": convertir_en_decimal(lieu.get("longitude")) if a_des_coordonnees else None,
        "precision_coordonnees": (convertir_en_precision_valide(lieu.get("precision_niveau"), "centroide")
                                  if a_des_coordonnees else "absent"),
        "fichier_json": nom_fichier,
        "confiance": convertir_en_decimal(document.get("confiance_globale")) or 0.4,
    }
    fragments: list[FragmentConnaissance] = []

    def ajouter_fragment(texte: str, mots_cles_supplementaires=(), **champs_specifiques):
        mots_cles = {mot for mot in (*mots_cles_du_document, *mots_cles_du_lieu,
                                     *(normaliser_nom(mot) for mot in mots_cles_supplementaires)) if mot}
        fragments.append(FragmentConnaissance(texte=texte, mots_cles=sorted(mots_cles),
                                              **{**champs_communs, **champs_specifiques}))

    description = _dictionnaire_de(document, "profil").get("description_courte")

    if description:
        ajouter_fragment(f"{nom_lieu} ({niveau}) : {description}")

    for culture in _liste_de(document, "cultures"):
        if isinstance(culture, dict) and culture.get("nom"):
            details = _ajouter_details(
                culture.get("categorie"),
                f"importance {culture['importance']}" if culture.get("importance") else None,
                f"récolte {culture['saison_recolte']}" if culture.get("saison_recolte") else None)
            ajouter_fragment(f"À {nom_lieu}, on cultive {culture['nom']}{details}.", [culture["nom"]])

    for ressource in _liste_de(document, "elevage_peche_ressources"):
        if isinstance(ressource, dict) and ressource.get("nom"):
            ajouter_fragment(f"À {nom_lieu}, {ressource.get('type') or 'ressource'} : {ressource['nom']}"
                             f"{_ajouter_details(ressource.get('details'))}.", [ressource["nom"]])

    for site in _liste_de(document, "lieux_celebres"):
        if not isinstance(site, dict) or not site.get("nom"):
            continue

        if coordonnees_valides(site.get("latitude"), site.get("longitude")):
            position_du_site = {
                "latitude": convertir_en_decimal(site["latitude"]), "longitude": convertir_en_decimal(site["longitude"]),
                "precision_coordonnees": convertir_en_precision_valide(site.get("precision_niveau"), "precis")}
        else:
            position_du_site = {
                "latitude": champs_communs["latitude"], "longitude": champs_communs["longitude"],
                "precision_coordonnees": "repli_hierarchique" if a_des_coordonnees else "absent"}

        ajouter_fragment(f"{site['nom']} ({site.get('type') or 'site'}), à {nom_lieu}. {site.get('description') or ''}".strip(),
                         [site["nom"], site.get("type") or ""], nom_lieu=site["nom"], niveau_lieu="site",
                         code_lieu=None, **position_du_site)

    traditions = _dictionnaire_de(document, "culture_traditions")

    for fete in _liste_de(traditions, "fetes_evenements"):
        if isinstance(fete, dict) and fete.get("nom"):
            ajouter_fragment(f"À {nom_lieu}, fête ou événement : {fete['nom']}"
                             f"{_ajouter_details(fete.get('periode'))}. {fete.get('description') or ''}".strip(),
                             [fete["nom"]])

    gastronomie = [str(plat) for plat in _liste_de(traditions, "gastronomie_locale")]

    if gastronomie:
        ajouter_fragment(f"Gastronomie locale à {nom_lieu} : {', '.join(gastronomie)}.", gastronomie)

    groupes_ethniques = [str(groupe) for groupe in _liste_de(traditions, "groupes_ethniques")]
    langues = [str(langue) for langue in _liste_de(traditions, "langues_dialectes")]

    if groupes_ethniques or langues:
        ajouter_fragment(f"À {nom_lieu} : groupes ethniques {', '.join(groupes_ethniques) or 'non précisés'} ; "
                         f"langues {', '.join(langues) or 'non précisées'}.")

    if not fragments:
        sujets = ", ".join(str(mot) for mot in _liste_de(document, "tags_recherche")) or "non précisé"
        ajouter_fragment(f"{nom_lieu} ({niveau}) : lieu associé à {sujets}.")

    return fragments


def _normaliser_cles(enregistrement: dict) -> dict:
    return {normaliser_nom_colonne(cle): valeur for cle, valeur in enregistrement.items()}


def _texte_ou_none(valeur) -> str | None:
    if isinstance(valeur, list):
        valeur = " | ".join(str(element) for element in valeur if not est_vide(element))

    return None if est_vide(valeur) else " ".join(str(valeur).split())


def _compter_decimales(valeur) -> int:
    morceaux = str(valeur).strip().replace(",", ".").split(".")
    return len(morceaux[1]) if len(morceaux) > 1 else 0


def _nettoyer_description(description: str | None) -> str | None:
    if description is None:
        return None

    description = MOTIF_ADRESSE_WEB.sub("", MOTIF_LIEN_DE_GEOCODAGE.sub("", description))

    return description.strip(" ;") or None


def _deviner_precision(champs: dict, nom_lieu: str, description: str | None, latitude_brute, longitude_brute) -> str:
    precision_indiquee = convertir_en_precision_valide(champs.get("PRECISION"), "")

    if precision_indiquee:
        return precision_indiquee

    if normaliser_nom(nom_lieu) == NOM_DU_PAYS:
        return "repli_hierarchique"

    if MARQUEUR_DE_GEOCODAGE in normaliser_nom(description):
        return "centroide"

    # Une position à 5 décimales ou plus (Google Places) désigne un site ; avec moins, c'est le centre d'une ville ou d'une zone
    nombre_de_decimales = min(_compter_decimales(latitude_brute), _compter_decimales(longitude_brute))

    return "precis" if nombre_de_decimales >= NOMBRE_DE_DECIMALES_D_UN_SITE else "centroide"


def construire_fragments_enregistrements(nom_fichier: str, enregistrements: list) -> list[FragmentConnaissance]:
    fragments = []

    for numero, enregistrement in enumerate(enregistrements, start=1):
        if not isinstance(enregistrement, dict):
            continue

        champs = _normaliser_cles(enregistrement)
        latitude, longitude, etat_coordonnees = corriger_coordonnees(champs.get("LATITUDE"), champs.get("LONGITUDE"))
        produit = _texte_ou_none(champs.get("PRODUIT"))
        zone = _texte_ou_none(champs.get("ZONE") or champs.get("REGION"))
        region = None if zone and normaliser_nom(zone) == NOM_DU_PAYS else zone
        nom_lieu = _texte_ou_none(champs.get("LIEU"))

        if not nom_lieu and produit and region and latitude is not None:
            nom_lieu = f"{produit} ({region})"
            journal.warning("%s : enregistrement %d sans nom de lieu, nommé %r", nom_fichier, numero, nom_lieu)

        if not nom_lieu:
            journal.warning("%s : enregistrement %d sans nom de lieu, ignoré", nom_fichier, numero)
            continue

        if etat_coordonnees not in ("ok", "absent"):
            journal.warning("%s : coordonnées de %r corrigées ou rejetées (%s)", nom_fichier, nom_lieu, etat_coordonnees)

        categorie = _texte_ou_none(champs.get("CATEGORIE"))
        description_brute = _texte_ou_none(champs.get("DESCRIPTION") or champs.get("AUTRES"))
        description = _nettoyer_description(description_brute)
        avis = _texte_ou_none(champs.get("AVIS"))
        sources_citees = _texte_ou_none(champs.get("SOURCES") or champs.get("SOURCE"))

        if sources_citees:
            sources_citees = re.sub(r"^sources?\s*:\s*", "", sources_citees, flags=re.IGNORECASE)

        note_google = convertir_en_decimal(champs.get("NOTEGOOGLE"))
        nombre_avis = convertir_en_entier(champs.get("NBAVISGOOGLE"))
        precision = _deviner_precision(champs, nom_lieu, description_brute, champs.get("LATITUDE"), champs.get("LONGITUDE"))
        niveau = (convertir_en_niveau_valide(champs.get("NIVEAU")) if champs.get("NIVEAU")
                  else ("site" if precision == "precis" else "autre"))

        morceaux_du_texte = [f"{nom_lieu}{_ajouter_details(categorie)}"]

        if produit:
            morceaux_du_texte.append(f"produit : {produit}")

        if region:
            morceaux_du_texte.append(f"zone : {region}")

        texte = " — ".join(morceaux_du_texte) + "."

        if description:
            texte += f" {description}"

        if note_google is not None:
            texte += f" Note Google : {note_google}/5" + (f" sur {nombre_avis} avis." if nombre_avis else ".")

        if avis:
            texte += f" Avis : {avis}"

        mots_cles = {mot for mot in (
            *(trouver_groupe_synonymes(normaliser_nom(produit)) if produit else ()),
            *(extraire_mots_utiles(produit) if produit else ()),
            normaliser_nom(nom_lieu), *extraire_mots_utiles(nom_lieu),
            normaliser_nom(region), *extraire_mots_utiles(region or ""),
            *extraire_mots_utiles(categorie or "")) if mot}

        fragments.append(FragmentConnaissance(
            nom_lieu=nom_lieu, niveau_lieu=niveau, texte=texte, fichier_json=nom_fichier,
            code_lieu=normaliser_code(champs.get("CODE")), region=region, district=_texte_ou_none(champs.get("DISTRICT")),
            latitude=latitude, longitude=longitude, precision_coordonnees=precision if latitude is not None else "absent",
            produit=produit, categorie=categorie, note_google=note_google, nombre_avis_google=nombre_avis, avis=avis,
            sources_citees=sources_citees, mots_cles=sorted(mots_cles), confiance=config.CONFIANCE_DONNEES_PRODUITS))

    return fragments


def _nom_de_fichier_du_lieu(lieu: Lieu) -> str:
    if lieu.code_officiel:
        return f"{lieu.niveau}_{lieu.code_officiel}.json"

    return f"web_{creer_slug(lieu.nom)}_{creer_slug(lieu.district or '')}.json"


def _creer_document_vide(lieu: Lieu) -> dict:
    code = lieu.code_officiel or ""

    return {
        "meta": {"version_format": "1.0", "date_collecte": date.today().isoformat(),
                 "collecte_par": "ia", "statut": "brouillon"},
        "lieu": {"niveau": lieu.niveau, "code": lieu.code_officiel,
                 "code_region": code[:2] or None, "code_district": code[:4] if len(code) >= 4 else None,
                 "code_commune": code[:6] if len(code) >= 6 else None,
                 "code_fokontany": code[:8] if len(code) >= 8 else None,
                 "nom": lieu.nom, "latitude": None, "longitude": None, "precision_niveau": "absent"},
        "profil": {"description_courte": "", "milieu": None, "altitude_m": None, "climat": None},
        "cultures": [], "elevage_peche_ressources": [], "lieux_celebres": [],
        "culture_traditions": {"groupes_ethniques": [], "langues_dialectes": [], "fetes_evenements": [],
                               "fady_coutumes": [], "gastronomie_locale": []},
        "economie_acces": {"marches": [], "produits_locaux_vendus": [], "route_principale": None,
                           "distance_chef_lieu_km": None, "praticable_toute_annee": None},
        "tags_recherche": [], "sources": [], "confiance_globale": 0.0,
    }


def enregistrer_lieu_dans_json(lieu: Lieu, mots_cles: list[str]) -> str:
    config.DOSSIER_LIEUX_JSON.mkdir(parents=True, exist_ok=True)
    nom_fichier = _nom_de_fichier_du_lieu(lieu)
    chemin = config.DOSSIER_LIEUX_JSON / nom_fichier
    document = json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else _creer_document_vide(lieu)

    profil = document.setdefault("profil", {})
    description_actuelle = profil.get("description_courte") or ""

    if lieu.description and lieu.description not in description_actuelle:
        profil["description_courte"] = f"{description_actuelle} {lieu.description}".strip()[:600]

    document["tags_recherche"] = sorted(set(_liste_de(document, "tags_recherche")) | {mot.lower() for mot in mots_cles})

    sources = document.setdefault("sources", [])

    if lieu.source and lieu.source not in {source.get("url") for source in sources if isinstance(source, dict)}:
        sources.append({"id": f"S{len(sources) + 1}", "id_source_db": None, "type": "web", "titre": "",
                        "url": lieu.source, "date_acces": date.today().isoformat(), "fiabilite": "moyenne"})

    position = document.setdefault("lieu", {})
    precision_actuelle = config.POIDS_PRECISION.get(position.get("precision_niveau"), 0.0)

    if lieu.a_des_coordonnees() and config.POIDS_PRECISION[lieu.precision_coordonnees] > precision_actuelle:
        position.update(latitude=lieu.latitude, longitude=lieu.longitude, precision_niveau=lieu.precision_coordonnees)

    document["confiance_globale"] = max(convertir_en_decimal(document.get("confiance_globale")) or 0.0, lieu.confiance)
    chemin.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")

    return f"lieux/{nom_fichier}"
