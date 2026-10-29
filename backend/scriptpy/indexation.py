from __future__ import annotations

import logging
import threading

import httpx

import base_donnees
import config
import connaissances_json
import modele_ia
from base_donnees import BaseIndisponible
from modeles import FragmentConnaissance

journal = logging.getLogger("indexation")

# Petits lots : Ollama traite les demandes de vecteurs une par une, donc une recherche d'utilisateur faite pendant
# l'indexation attend la fin du lot en cours (16 textes ≈ 20 s sur processeur, 4 textes ≈ 5 s).
TAILLE_DES_LOTS = 4


def _ajouter_noms_des_parents(fragments: list[FragmentConnaissance]):
    noms_parents_par_lieu: dict[tuple[str, str], tuple[str | None, str | None]] = {}

    for fragment in fragments:
        if fragment.code_lieu and not fragment.region:
            cle = (fragment.niveau_lieu, fragment.code_lieu)

            if cle not in noms_parents_par_lieu:
                noms_parents_par_lieu[cle] = base_donnees.trouver_noms_parents(*cle)

            fragment.region, fragment.district = noms_parents_par_lieu[cle]


def indexer_fichiers(noms_fichiers: list[str] | None = None) -> dict[str, int]:
    bilan = {"nouveaux": 0, "inchanges": 0, "supprimes": 0}
    fragments_a_enregistrer: list[FragmentConnaissance] = []
    fichiers_a_nettoyer: list[tuple[str, set[str]]] = []

    for nom_fichier, contenu in connaissances_json.lire_documents(noms_fichiers):
        fragments = connaissances_json.construire_fragments(nom_fichier, contenu)
        _ajouter_noms_des_parents(fragments)

        empreintes_actuelles = {fragment.calculer_empreinte() for fragment in fragments}
        empreintes_en_base = base_donnees.lister_empreintes_du_fichier(nom_fichier)

        if empreintes_en_base - empreintes_actuelles:
            fichiers_a_nettoyer.append((nom_fichier, empreintes_actuelles))

        nouveaux = [fragment for fragment in fragments if fragment.calculer_empreinte() not in empreintes_en_base]
        bilan["inchanges"] += len(fragments) - len(nouveaux)
        fragments_a_enregistrer.extend(nouveaux)

    # Chaque lot est enregistré dès que ses vecteurs sont calculés : sur un processeur sans carte graphique, tout indexer
    # prend de longues minutes. Un arrêt du serveur en cours de route ne fait donc rien perdre (la reprise saute les
    # fragments déjà en base), et les petits fichiers (lieux, produits, lus en premier) sont cherchables très vite.
    for debut in range(0, len(fragments_a_enregistrer), TAILLE_DES_LOTS):
        lot = fragments_a_enregistrer[debut:debut + TAILLE_DES_LOTS]
        vecteurs = modele_ia.calculer_vecteurs([fragment.texte for fragment in lot])
        bilan["nouveaux"] += base_donnees.enregistrer_fragments(lot, vecteurs) or 0

    # Les suppressions viennent après l'enregistrement : si le calcul des vecteurs échoue, rien n'est perdu
    for nom_fichier, empreintes_actuelles in fichiers_a_nettoyer:
        bilan["supprimes"] += base_donnees.supprimer_fragments_obsoletes(nom_fichier, empreintes_actuelles)

    if noms_fichiers is None:
        fichiers_presents = connaissances_json.lister_fichiers_connaissances()
        if fichiers_presents:
            bilan["supprimes"] += base_donnees.supprimer_fragments_des_fichiers_absents(fichiers_presents)

    return bilan


def reindexer_regulierement(evenement_arret: threading.Event):
    while not evenement_arret.is_set():
        try:
            bilan = indexer_fichiers()

            if bilan["nouveaux"] or bilan["supprimes"]:
                journal.info("Indexation automatique : %s", bilan)
        except (BaseIndisponible, httpx.HTTPError, ValueError) as erreur:
            journal.warning("Indexation automatique impossible : %s", erreur)

        evenement_arret.wait(config.INTERVALLE_REINDEXATION_EN_SECONDES)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print(indexer_fichiers())
