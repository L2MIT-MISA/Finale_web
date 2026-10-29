import math

import base_donnees
import recherche_web
from base_donnees import BaseIndisponible
from modeles import Lieu
from outils import normaliser_nom

SEUIL_SIMILARITE_NOM_POUR_COORDONNEES = 0.85


def coordonnees_citees_dans_la_source(latitude: float, longitude: float, texte_source: str) -> bool:
    """Vrai si latitude et longitude (à 0,1 degré près) sont écrites dans le texte : protège contre les coordonnées inventées."""
    texte = texte_source.replace(",", ".")

    return all(f"{math.floor(abs(valeur) * 10 + 1e-9) / 10}" in texte for valeur in (latitude, longitude))


def chercher_coordonnees_dans_le_referentiel(lieu: Lieu):
    if lieu.code_officiel and lieu.niveau in base_donnees.NIVEAUX_DU_REFERENTIEL:
        return base_donnees.trouver_coordonnees_officielles(lieu.niveau, lieu.code_officiel)

    correspondances = base_donnees.chercher_lieux_du_referentiel(
        [normaliser_nom(lieu.nom)], seuil_similarite=SEUIL_SIMILARITE_NOM_POUR_COORDONNEES)

    for correspondance in correspondances:
        if not correspondance.a_des_coordonnees():
            continue

        if correspondance.niveau == lieu.niveau:
            lieu.code_officiel = correspondance.code_officiel

        return correspondance.latitude, correspondance.longitude, correspondance.precision_coordonnees

    return None


def completer_coordonnees(lieux: list[Lieu], autoriser_geocodage: bool):
    base_disponible = True

    for lieu in lieux:
        if lieu.a_des_coordonnees():
            continue

        coordonnees = None

        if base_disponible:
            try:
                coordonnees = chercher_coordonnees_dans_le_referentiel(lieu)
            except BaseIndisponible:
                base_disponible = False

        if coordonnees is None and autoriser_geocodage:
            coordonnees = recherche_web.geocoder_avec_nominatim(lieu.nom, lieu.district, lieu.region)

        if coordonnees:
            lieu.definir_coordonnees(*coordonnees)
