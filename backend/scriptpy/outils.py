from __future__ import annotations

import math
import re
import unicodedata
from difflib import SequenceMatcher

import config

VALEURS_VIDES = {"", "NAN", "NONE", "NULL", "-", "<NA>", "NAT"}
MOTS_VIDES = {
    "DE", "DU", "DES", "LA", "LE", "LES", "L", "D", "ET", "A", "AU", "AUX", "EN", "DANS", "SUR", "POUR", "OU",
    "UN", "UNE", "QUI", "QUE", "EST", "SONT", "IL", "Y", "MADAGASCAR", "LIEU", "LIEUX", "TROUVER", "TROUVE",
    "CHERCHE", "CHERCHER", "VEUX", "VOUDRAIS", "AVEC", "PAR", "AIDE", "AIDER", "BESOIN", "INFO", "INFOS",
    "INFORMATION", "INFORMATIONS", "TRUC", "CHOSE", "QUELQUE", "QUELQUES", "SVP", "BONJOUR", "SALUT", "MERCI",
    "PLAIT", "JE", "TU", "NOUS", "VOUS", "MON", "MA", "MES", "CE", "CET", "CETTE", "CES", "SE", "QUEL", "QUELLE",
    "QUELS", "QUELLES", "COMMENT", "POURQUOI", "QU",
}
MOTIF_NUMERO_FINAL = re.compile(r"(I{1,3}|IV|V|VI{0,3}|IX|X|\d+)")


def retirer_accents(texte: str) -> str:
    return "".join(caractere for caractere in unicodedata.normalize("NFD", texte)
                   if unicodedata.category(caractere) != "Mn")


def est_vide(valeur) -> bool:
    if valeur is None or (isinstance(valeur, float) and math.isnan(valeur)):
        return True

    return str(valeur).strip().upper() in VALEURS_VIDES


def normaliser_nom(valeur) -> str:
    if est_vide(valeur):
        return ""

    return re.sub(r"[^A-Z0-9]+", " ", retirer_accents(str(valeur)).upper()).strip()


def normaliser_texte_libre(valeur) -> str | None:
    if est_vide(valeur):
        return None

    return re.sub(r"\s+", " ", retirer_accents(str(valeur)).upper()).strip()


def normaliser_nom_colonne(valeur) -> str:
    return re.sub(r"[^A-Z0-9]", "", retirer_accents(str(valeur)).upper().replace("%", "PCT"))


def normaliser_code(valeur) -> str | None:
    if est_vide(valeur):
        return None

    if isinstance(valeur, float) and valeur.is_integer():
        valeur = int(valeur)

    texte = str(valeur).strip()

    if texte.endswith(".0"):
        texte = texte[:-2]

    return texte if texte.isdigit() else None


def convertir_en_decimal(valeur) -> float | None:
    if est_vide(valeur):
        return None

    texte = str(valeur).strip().replace("\u00a0", "").replace(" ", "").replace(",", ".")

    try:
        return float(texte)
    except ValueError:
        return None


def convertir_en_entier(valeur) -> int | None:
    nombre = convertir_en_decimal(valeur)
    return None if nombre is None else int(round(nombre))


def convertir_en_booleen(valeur) -> bool | None:
    texte = "" if est_vide(valeur) else str(valeur).strip().upper()

    if texte in {"1", "1.0", "OUI", "TRUE", "X"}:
        return True

    if texte in {"0", "0.0", "NON", "FALSE"}:
        return False

    return None


def coordonnees_valides(latitude, longitude) -> bool:
    try:
        return (config.LATITUDE_MIN <= float(latitude) <= config.LATITUDE_MAX
                and config.LONGITUDE_MIN <= float(longitude) <= config.LONGITUDE_MAX)
    except (TypeError, ValueError):
        return False


def corriger_coordonnees(latitude_brute, longitude_brute):
    """Retourne (latitude, longitude, etat) ; etat : ok, signe_oublie, inversees, inversees_signe_oublie, absent ou invalide."""
    latitude = convertir_en_decimal(latitude_brute)
    longitude = convertir_en_decimal(longitude_brute)

    if latitude is None or longitude is None:
        return None, None, "absent"

    essais = (("ok", latitude, longitude), ("signe_oublie", -latitude, longitude),
              ("inversees", longitude, latitude), ("inversees_signe_oublie", -longitude, latitude))

    for etat, latitude_essayee, longitude_essayee in essais:
        if coordonnees_valides(latitude_essayee, longitude_essayee):
            return latitude_essayee, longitude_essayee, etat

    return None, None, "invalide"


def trouver_meilleur_rapprochement(nom, candidats: dict, seuil: float = 0.90, marge: float = 0.02):
    """Retourne (code, score) ; code vaut None si aucun candidat n'atteint le seuil ou si deux sont à égalité."""
    nom_cherche = normaliser_nom(nom)
    notes = sorted(((SequenceMatcher(None, nom_cherche, normaliser_nom(nom_candidat)).ratio(), code)
                    for code, nom_candidat in candidats.items()), reverse=True)

    if not notes or notes[0][0] < seuil:
        return None, (notes[0][0] if notes else 0.0)

    if len(notes) > 1 and notes[0][0] - notes[1][0] < marge:
        return None, notes[0][0]

    return notes[0][1], notes[0][0]


def extraire_numero_final(nom) -> str:
    mots = normaliser_nom(nom).split()
    return mots[-1] if mots and MOTIF_NUMERO_FINAL.fullmatch(mots[-1]) else ""


def creer_slug(texte: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", retirer_accents(str(texte)).lower()).strip("-") or "sans-nom"


def extraire_mots_utiles(texte: str) -> list[str]:
    return [mot for mot in normaliser_nom(texte).split() if mot not in MOTS_VIDES and len(mot) > 1]


def trouver_groupe_synonymes(mot_normalise: str) -> set[str]:
    for groupe in config.GROUPES_DE_SYNONYMES:
        groupe_normalise = {normaliser_nom(synonyme) for synonyme in groupe}

        if mot_normalise in groupe_normalise:
            return groupe_normalise

    return {mot_normalise}
