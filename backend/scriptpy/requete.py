from __future__ import annotations

from dataclasses import dataclass

from outils import extraire_mots_utiles, trouver_groupe_synonymes


@dataclass
class RequeteAnalysee:
    texte_original: str
    mots_cles: list[str]                   
    mots_cles_avec_synonymes: list[str]    
    groupes_de_synonymes: list[set[str]]   


def analyser_requete(texte_requete: str) -> RequeteAnalysee:
    mots_cles = extraire_mots_utiles(texte_requete)
    groupes_de_synonymes = [trouver_groupe_synonymes(mot) for mot in mots_cles]
    mots_cles_avec_synonymes = sorted(set().union(*groupes_de_synonymes))

    return RequeteAnalysee(texte_original=texte_requete.strip(), mots_cles=mots_cles,
                           mots_cles_avec_synonymes=mots_cles_avec_synonymes,
                           groupes_de_synonymes=groupes_de_synonymes)


def rassembler_mots_cles(requete: RequeteAnalysee, mots_cles_du_modele: list[str]) -> list[str]:
    tous = [*requete.mots_cles, *requete.mots_cles_avec_synonymes, *mots_cles_du_modele]

    return list(dict.fromkeys(mot.lower().strip() for mot in tous if mot.strip()))
