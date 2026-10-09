import config
from modeles import Lieu
from outils import normaliser_nom

NOTE_MAXIMALE = 5
SCORE_NOTE_INCONNUE = 0.5


def calculer_score_note(lieu: Lieu) -> float:
    if lieu.note_google is None:
        return SCORE_NOTE_INCONNUE

    nombre_avis = lieu.nombre_avis_google or 0
    note_ajustee = ((lieu.note_google * nombre_avis + config.NOTE_MOYENNE_DE_REFERENCE * config.NOMBRE_AVIS_DE_REFERENCE)
                    / (nombre_avis + config.NOMBRE_AVIS_DE_REFERENCE))

    return note_ajustee / NOTE_MAXIMALE


def calculer_score_classement(lieu: Lieu) -> float:
    poids = config.POIDS_CLASSEMENT

    return (poids["pertinence"] * lieu.pertinence
            + poids["note"] * calculer_score_note(lieu)
            + poids["confiance"] * lieu.confiance
            + poids["origine"] * config.POIDS_ORIGINE[lieu.origine]
            + poids["precision"] * config.POIDS_PRECISION[lieu.precision_coordonnees])


def classer_lieux(lieux: list[Lieu]) -> list[Lieu]:
    lieux_uniques: dict[tuple[str, str, str], Lieu] = {}
    lieux_avec_coordonnees = [lieu for lieu in lieux if lieu.a_des_coordonnees()]

    for lieu in sorted(lieux_avec_coordonnees, key=calculer_score_classement, reverse=True):
        cle = (normaliser_nom(lieu.nom), normaliser_nom(lieu.district), normaliser_nom(lieu.produit))
        meilleur = lieux_uniques.setdefault(cle, lieu)

        if meilleur is not lieu:
            if len(lieu.description) > len(meilleur.description):
                meilleur.description = lieu.description

            meilleur.mots_cles = list(dict.fromkeys([*meilleur.mots_cles, *lieu.mots_cles]))

    return list(lieux_uniques.values())[:config.NOMBRE_LIEUX_MAX]
