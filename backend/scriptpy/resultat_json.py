from __future__ import annotations

import json
import os
import re
import secrets
import threading
import time
from datetime import datetime

import config
from modeles import Lieu, SourceDisponible
from outils import creer_slug

MOTIF_IDENTIFIANT_RESULTAT = re.compile(r"^[a-z0-9-]+$")
STATUTS_MEMORISABLES = ("en_cours", "termine")


def maintenant() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def creer_identifiant_resultat(texte_requete: str) -> str:
    return f"{datetime.now():%Y%m%d-%H%M%S}-{creer_slug(texte_requete)[:30]}-{secrets.token_hex(2)}"


def calculer_carte_depuis_positions(positions: list[tuple[float, float]]) -> dict | None:
    """positions : liste de (latitude, longitude). Retourne le centre, l'emprise et un zoom conseillé."""
    if not positions:
        return None

    latitudes = [latitude for latitude, _ in positions]
    longitudes = [longitude for _, longitude in positions]
    ecart_maximal = max(max(latitudes) - min(latitudes), max(longitudes) - min(longitudes))
    zooms_par_ecart = ((0.05, 13), (0.2, 11), (0.5, 10), (1.0, 9), (2.0, 8), (4.0, 7))
    zoom = 11 if len(positions) == 1 else next((zoom for ecart, zoom in zooms_par_ecart if ecart_maximal <= ecart), 6)

    return {"centre": {"latitude": round((max(latitudes) + min(latitudes)) / 2, 6),
                       "longitude": round((max(longitudes) + min(longitudes)) / 2, 6)},
            "emprise": {"sud": min(latitudes), "nord": max(latitudes), "ouest": min(longitudes), "est": max(longitudes)},
            "zoom_suggere": zoom}


def calculer_carte(lieux: list[Lieu]) -> dict | None:
    return calculer_carte_depuis_positions([(lieu.latitude, lieu.longitude) for lieu in lieux])


def calculer_carte_depuis_sorties(lieux: list[dict]) -> dict | None:
    """Même calcul à partir des lieux déjà convertis en dictionnaires (format de sortie du site)."""
    positions = [(lieu["coordonnees"]["latitude"], lieu["coordonnees"]["longitude"]) for lieu in lieux
                 if lieu.get("coordonnees", {}).get("latitude") is not None
                 and lieu.get("coordonnees", {}).get("longitude") is not None]

    return calculer_carte_depuis_positions(positions)


def determiner_source_principale(lieux: list[Lieu]) -> str:
    origines = {lieu.origine for lieu in lieux}

    for origine in ("google", "osm", "base_connaissances", "referentiel"):
        if origine in origines:
            return origine

    return "aucune"


def _assembler_enveloppe(*, identifiant, statut, date_creation, texte_requete, intention, mots_cles, texte_reponse,
                         recherche_google, lieux, sources, clarification, urgence, avertissements, erreur) -> dict:
    return {
        "id_resultat": identifiant,
        "statut": statut,
        "date_creation": date_creation,
        "date_fin": None if statut == "en_cours" else maintenant(),
        "requete": {"texte_original": texte_requete, "intention": intention, "mots_cles": mots_cles},
        "reponse": {"texte": texte_reponse, "source_principale": determiner_source_principale(lieux),
                    "recherche_google": recherche_google},
        "lieux": [lieu.vers_dictionnaire_sortie() for lieu in lieux],
        "carte": calculer_carte(lieux),
        "sources": [{"reference": source.reference, "origine": source.origine, "titre": source.titre,
                     "url": source.url, "fichier": source.fichier_json} for source in sources],
        "clarification": clarification,
        "urgence": urgence,
        "avertissements": list(dict.fromkeys(avertissements)),
        "erreur": erreur,
    }


def assembler_resultat(*, identifiant: str, statut: str, date_creation: str, texte_requete: str,
                       intention: str | None, mots_cles: list[str], texte_reponse: str, recherche_google: str,
                       lieux: list[Lieu], sources: list[SourceDisponible], avertissements: list[str],
                       erreur: str | None = None) -> dict:
    return _assembler_enveloppe(
        identifiant=identifiant, statut=statut, date_creation=date_creation, texte_requete=texte_requete,
        intention=intention, mots_cles=mots_cles, texte_reponse=texte_reponse, recherche_google=recherche_google,
        lieux=lieux, sources=sources, clarification=None, urgence=None, avertissements=avertissements, erreur=erreur)


def assembler_clarification(*, identifiant: str, date_creation: str, texte_requete: str, type_clarification: str,
                            raison: str, question: str, options: list[dict], option_choisie: str | None,
                            avertissements: list[str]) -> dict:
    clarification = {"type": type_clarification, "raison": raison, "question": question, "options": options,
                     "texte_libre_autorise": True, "option_choisie": option_choisie,
                     "requete_initiale": texte_requete}

    return _assembler_enveloppe(
        identifiant=identifiant, statut="clarification_necessaire", date_creation=date_creation,
        texte_requete=texte_requete, intention=None, mots_cles=[], texte_reponse=question,
        recherche_google="non_necessaire", lieux=[], sources=[], clarification=clarification, urgence=None,
        avertissements=avertissements, erreur=None)


def assembler_urgence(*, identifiant: str, date_creation: str, texte_requete: str) -> dict:
    avertissements = []

    if not config.NUMEROS_D_URGENCE:
        avertissements.append("Numéros d'urgence non configurés : renseigner NUMEROS_D_URGENCE dans config.py.")

    return _assembler_enveloppe(
        identifiant=identifiant, statut="urgence", date_creation=date_creation, texte_requete=texte_requete,
        intention=None, mots_cles=[], texte_reponse=config.MESSAGE_URGENCE, recherche_google="non_necessaire",
        lieux=[], sources=[], clarification=None,
        urgence={"message": config.MESSAGE_URGENCE, "contacts": config.NUMEROS_D_URGENCE},
        avertissements=avertissements, erreur=None)


def chemin_du_resultat(identifiant: str):
    return config.DOSSIER_RESULTATS / f"{identifiant}.json"


def ecrire_resultat(resultat: dict):
    # écriture atomique : le site ne lit jamais un fichier à moitié écrit
    config.DOSSIER_RESULTATS.mkdir(parents=True, exist_ok=True)
    chemin = chemin_du_resultat(resultat["id_resultat"])
    chemin_temporaire = chemin.with_suffix(".json.tmp")
    chemin_temporaire.write_text(json.dumps(resultat, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(chemin_temporaire, chemin)


def lire_resultat(identifiant: str) -> dict | None:
    if not MOTIF_IDENTIFIANT_RESULTAT.match(identifiant):
        return None

    chemin = chemin_du_resultat(identifiant)

    return json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else None


class CacheDesResultats:
    def __init__(self, duree_en_secondes: float):
        self.duree_en_secondes = duree_en_secondes
        self._entrees: dict[str, tuple[float, str]] = {}
        self._verrou = threading.Lock()

    def trouver_resultat(self, cle: str) -> dict | None:
        with self._verrou:
            entree = self._entrees.get(cle)

        if entree is None or time.monotonic() - entree[0] > self.duree_en_secondes:
            return None

        resultat = lire_resultat(entree[1])

        return resultat if resultat and resultat["statut"] in STATUTS_MEMORISABLES else None

    def memoriser(self, cle: str, identifiant: str):
        instant = time.monotonic()

        with self._verrou:
            self._entrees[cle] = (instant, identifiant)
            self._entrees = {cle_existante: entree for cle_existante, entree in self._entrees.items()
                             if instant - entree[0] <= self.duree_en_secondes}

    def vider(self):
        with self._verrou:
            self._entrees.clear()
