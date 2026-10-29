from __future__ import annotations

import json
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx

import base_donnees
import clarification
import config
import connaissances_json
import coordonnees
import indexation
import modele_ia
import recherche_web
import resultat_json
from base_donnees import BaseIndisponible
from classement import classer_lieux
from modeles import FragmentConnaissance, Lieu, ReponseDuModele, SourceDisponible
from outils import extraire_mots_utiles
from prompts import construire_messages_extraction, construire_messages_resume
from recherche_web import PageWeb
from requete import RequeteAnalysee, analyser_requete, rassembler_mots_cles

journal = logging.getLogger("recherche")

TEXTE_AUCUN_LIEU = "Aucun lieu trouvé pour cette recherche."
TEXTE_REDACTION_EN_COURS = "Rédaction de la réponse en cours..."
TEXTE_GOOGLE_EN_COURS = "Recherche sur Google en cours..."
TEXTE_REQUETE_VIDE = "Merci de saisir un lieu ou un thème à rechercher."

cache_des_resultats = resultat_json.CacheDesResultats(config.DUREE_CACHE_RESULTATS_EN_SECONDES)


@dataclass
class ReponseRedigee:
    texte: str
    intention: str | None
    mots_cles: list[str]
    lieux: list[Lieu]
    sources: list[SourceDisponible]
    recherche_google: str


def trouver_lieux_du_referentiel(requete: RequeteAnalysee, avertissements: list[str]) -> list[Lieu]:
    noms_recherches = list(dict.fromkeys([" ".join(requete.mots_cles), *requete.mots_cles]))

    try:
        return base_donnees.chercher_lieux_du_referentiel(noms_recherches)
    except BaseIndisponible as erreur:
        avertissements.append(f"Base PostgreSQL indisponible : {erreur}")
        return []


def convertir_fragment_en_lieu(fragment: FragmentConnaissance, pertinence: float) -> Lieu:
    lieu = Lieu(nom=fragment.nom_lieu, niveau=fragment.niveau_lieu, code_officiel=fragment.code_lieu,
                region=fragment.region, district=fragment.district, produit=fragment.produit,
                categorie=fragment.categorie, description=fragment.texte, note_google=fragment.note_google,
                nombre_avis_google=fragment.nombre_avis_google, avis=fragment.avis, sources_citees=fragment.sources_citees,
                mots_cles=[mot.lower() for mot in fragment.mots_cles], pertinence=pertinence,
                confiance=fragment.confiance, origine="base_connaissances",
                source=fragment.source_url or fragment.fichier_json)

    if fragment.latitude is not None:
        lieu.definir_coordonnees(fragment.latitude, fragment.longitude, fragment.precision_coordonnees)

    return lieu


def chercher_connaissances(requete: RequeteAnalysee, avertissements: list[str]) -> list[Lieu]:
    try:
        vecteur_requete = list(modele_ia.calculer_vecteur_de_la_requete(requete.texte_original))
    except (httpx.HTTPError, ValueError) as erreur:
        avertissements.append(f"Vecteur de la requête indisponible, recherche par mots-clés seulement : {erreur}")
        vecteur_requete = None

    try:
        fragments = base_donnees.chercher_fragments(vecteur_requete, requete.mots_cles_avec_synonymes,
                                                    config.NOMBRE_FRAGMENTS_RECUPERES)
    except BaseIndisponible as erreur:
        avertissements.append(f"Base PostgreSQL indisponible : {erreur}. Utilisation des fichiers JSON locaux.")
        fragments = chercher_fragments_dans_les_fichiers(requete)

    lieux = []

    for fragment in fragments:
        mots_cles_du_fragment = set(fragment.mots_cles)
        groupes_couverts = sum(1 for groupe in requete.groupes_de_synonymes if groupe & mots_cles_du_fragment)
        couverture = groupes_couverts / len(requete.groupes_de_synonymes)

        if fragment.similarite < config.SEUIL_SIMILARITE_FRAGMENT and couverture < config.SEUIL_COUVERTURE_MOTS_CLES:
            continue

        pertinence = min(1.0, fragment.similarite + config.BONUS_MOT_CLE_COMMUN * couverture)
        lieux.append(convertir_fragment_en_lieu(fragment, pertinence))

    return sorted(lieux, key=lambda lieu: lieu.pertinence, reverse=True)


def chercher_fragments_dans_les_fichiers(requete: RequeteAnalysee) -> list[FragmentConnaissance]:
    """Repli rapide sans PostgreSQL : exploite les mêmes JSON que l'indexation RAG."""
    recherches = {mot.upper() for mot in requete.mots_cles_avec_synonymes}
    trouves: list[FragmentConnaissance] = []

    for nom_fichier, document in connaissances_json.lire_documents():
        for fragment in connaissances_json.construire_fragments(nom_fichier, document):
            mots_fragment = {mot.upper() for mot in fragment.mots_cles}
            texte = fragment.texte.upper()

            if recherches & mots_fragment or any(mot in texte for mot in recherches if len(mot) >= 3):
                couverture = len(recherches & mots_fragment) / max(1, len(recherches))
                fragment.similarite = max(0.55, min(0.9, 0.55 + couverture * 0.35))
                trouves.append(fragment)

    return sorted(trouves, key=lambda fragment: fragment.similarite, reverse=True)[:config.NOMBRE_FRAGMENTS_RECUPERES]


def decrire_lieu_pour_le_modele(lieu: Lieu) -> str:
    parents = ", ".join(partie for partie in (lieu.district and f"district {lieu.district}",
                                              lieu.region and f"région {lieu.region}") if partie)
    note = ""

    if lieu.note_google is not None:
        nombre_avis = f" ({lieu.nombre_avis_google} avis)" if lieu.nombre_avis_google else ""
        note = f", note Google {lieu.note_google}/5{nombre_avis}"

    return f"{lieu.nom} ({lieu.niveau}{', ' + parents if parents else ''}{note}) : {lieu.description}"


def rediger_resume_sans_modele(requete: RequeteAnalysee, lieux: list[Lieu]) -> str:
    if not lieux:
        return TEXTE_AUCUN_LIEU

    noms = ", ".join(lieu.nom for lieu in lieux[:3])

    return f"{len(lieux)} lieu(x) trouvé(s) pour « {requete.texte_original} » : {noms}."


def construire_sources_connaissances(lieux: list[Lieu]) -> list[SourceDisponible]:
    fichiers = list(dict.fromkeys(lieu.source for lieu in lieux if lieu.origine == "base_connaissances" and lieu.source))
    sources = [SourceDisponible(reference=f"F{numero}", origine="base_connaissances", fichier_json=fichier)
               for numero, fichier in enumerate(fichiers, start=1)]

    if any(lieu.origine == "referentiel" for lieu in lieux):
        sources.insert(0, SourceDisponible(reference="R1", origine="referentiel"))

    return sources


def produire_reponse_avec_connaissances(requete: RequeteAnalysee, candidats: list[Lieu],
                                        avertissements: list[str], avec_resume_ia: bool = True) -> ReponseRedigee:
    coordonnees.completer_coordonnees(candidats, autoriser_geocodage=True)
    nombre_sans_coordonnees = sum(1 for lieu in candidats if not lieu.a_des_coordonnees())

    if nombre_sans_coordonnees:
        avertissements.append(f"{nombre_sans_coordonnees} lieu(x) écarté(s) faute de coordonnées vérifiables.")

    lieux = classer_lieux(candidats)
    resume = None

    if lieux and avec_resume_ia:
        texte_lieux = "\n".join(f"[{numero}] {decrire_lieu_pour_le_modele(lieu)}"
                                for numero, lieu in enumerate(lieux[:config.NOMBRE_LIEUX_POUR_LE_RESUME], start=1))
        resume = modele_ia.rediger_resume(construire_messages_resume(requete.texte_original, texte_lieux))

    if resume is None:
        if lieux and avec_resume_ia:
            avertissements.append("Le modèle n'a pas répondu : réponse rédigée automatiquement.")

        intention = "lieu" if any(lieu.origine == "referentiel" for lieu in lieux) else "theme"

        return ReponseRedigee(rediger_resume_sans_modele(requete, lieux), intention, rassembler_mots_cles(requete, []),
                              lieux, construire_sources_connaissances(lieux), "non_necessaire")

    return ReponseRedigee(resume.reponse, resume.intention, rassembler_mots_cles(requete, resume.mots_cles),
                          lieux, construire_sources_connaissances(lieux), "non_necessaire")


def preparer_sources_extraction(lieux_referentiel: list[Lieu], pages_web: list[PageWeb]) -> dict[str, SourceDisponible]:
    sources = {}

    for numero, lieu in enumerate(lieux_referentiel, start=1):
        reference = f"R{numero}"
        sources[reference] = SourceDisponible(reference, "referentiel", decrire_lieu_pour_le_modele(lieu), lieu=lieu)

    for numero, page in enumerate(pages_web, start=1):
        reference = f"W{numero}"
        sources[reference] = SourceDisponible(reference, "google", page.texte, titre=page.titre, url=page.url)

    return sources


def convertir_lieux_proposes(reponse_modele: ReponseDuModele, sources: dict[str, SourceDisponible],
                             mots_cles_requete: list[str], avertissements: list[str]) -> list[Lieu]:
    lieux = []

    for lieu_propose in reponse_modele.lieux:
        source = sources.get(lieu_propose.reference_source or "")

        if source is None:
            avertissements.append(f"Lieu « {lieu_propose.nom} » écarté : la source citée n'existe pas.")
            continue

        if source.lieu is not None:
            continue

        lieu = Lieu(nom=lieu_propose.nom, niveau=lieu_propose.niveau, region=lieu_propose.region,
                    district=lieu_propose.district, description=lieu_propose.description, mots_cles=mots_cles_requete,
                    pertinence=lieu_propose.confiance, confiance=lieu_propose.confiance, origine="google",
                    source=source.url)
        a_des_coordonnees_proposees = lieu_propose.latitude is not None and lieu_propose.longitude is not None

        if a_des_coordonnees_proposees:
            if coordonnees.coordonnees_citees_dans_la_source(lieu_propose.latitude, lieu_propose.longitude, source.texte):
                lieu.definir_coordonnees(lieu_propose.latitude, lieu_propose.longitude, "precis")
            else:
                avertissements.append(f"Coordonnées de « {lieu.nom} » ignorées : absentes de la source citée.")

        lieux.append(lieu)

    return lieux


def memoriser_lieux_google(lieux: list[Lieu], mots_cles: list[str], avertissements: list[str]):
    noms_fichiers = [connaissances_json.enregistrer_lieu_dans_json(lieu, mots_cles)
                     for lieu in lieux if lieu.origine == "google"]

    if not noms_fichiers:
        return

    try:
        indexation.indexer_fichiers(noms_fichiers)
    except (BaseIndisponible, httpx.HTTPError, ValueError) as erreur:
        avertissements.append(f"Indexation pgvector impossible (les fichiers JSON sont bien enregistrés) : {erreur}")


def produire_reponse_avec_google(requete: RequeteAnalysee, lieux_referentiel: list[Lieu],
                                 avertissements: list[str]) -> ReponseRedigee:
    try:
        pages_web = recherche_web.chercher_pages_sur_google(requete.texte_original, requete.mots_cles_avec_synonymes)
        etat_recherche_google = "terminee"
    except (recherche_web.RechercheGoogleIndisponible, httpx.HTTPError) as erreur:
        avertissements.append(f"Recherche Google impossible : {erreur}")
        pages_web, etat_recherche_google = [], "indisponible"

    sources = preparer_sources_extraction(lieux_referentiel, pages_web)
    reponse_modele = None

    if pages_web:
        texte_referentiel = "\n".join(f"[{reference}] {source.texte}" for reference, source in sources.items()
                                      if source.origine == "referentiel")
        texte_web = "\n".join(f"[{reference}] {source.titre} ({source.url})\n{source.texte}"
                              for reference, source in sources.items() if source.origine == "google")
        reponse_modele = modele_ia.extraire_lieux(
            construire_messages_extraction(requete.texte_original, texte_referentiel, texte_web))

        if reponse_modele is None:
            avertissements.append("Le modèle n'a pas répondu : les pages Google n'ont pas pu être analysées.")

    lieux = list(lieux_referentiel)
    texte_reponse = TEXTE_AUCUN_LIEU if not lieux_referentiel else rediger_resume_sans_modele(requete, lieux_referentiel)
    intention = "lieu" if lieux_referentiel else None
    mots_cles_du_modele: list[str] = []

    if reponse_modele is not None:
        lieux += convertir_lieux_proposes(reponse_modele, sources, requete.mots_cles_avec_synonymes, avertissements)
        texte_reponse, intention, mots_cles_du_modele = reponse_modele.reponse, reponse_modele.intention, reponse_modele.mots_cles

    coordonnees.completer_coordonnees(lieux, autoriser_geocodage=True)
    nombre_sans_coordonnees = sum(1 for lieu in lieux if not lieu.a_des_coordonnees())

    if nombre_sans_coordonnees:
        avertissements.append(f"{nombre_sans_coordonnees} lieu(x) écarté(s) faute de coordonnées vérifiables.")

    lieux_classes = classer_lieux(lieux)
    mots_cles = rassembler_mots_cles(requete, mots_cles_du_modele)
    memoriser_lieux_google(lieux_classes, mots_cles, avertissements)

    return ReponseRedigee(texte_reponse, intention, mots_cles, lieux_classes, list(sources.values()),
                          etat_recherche_google)


def construire_clarification(identifiant: str, date_creation: str, texte_requete: str, raison: str) -> dict:
    question = config.QUESTION_REQUETE_FLOUE if raison == "requete_floue" else config.QUESTION_AUCUN_RESULTAT

    return resultat_json.assembler_clarification(
        identifiant=identifiant, date_creation=date_creation, texte_requete=texte_requete,
        type_clarification="choix_categorie", raison=raison, question=question,
        options=clarification.lister_options_publiques(), option_choisie=None, avertissements=[])


def terminer_recherche(identifiant: str, date_creation: str, requete: RequeteAnalysee, candidats: list[Lieu],
                       avertissements: list[str], utiliser_google: bool, deja_precise: bool, avec_resume_ia: bool = True):
    try:
        if utiliser_google:
            reponse = produire_reponse_avec_google(requete, candidats, avertissements)
        else:
            reponse = produire_reponse_avec_connaissances(requete, candidats, avertissements, avec_resume_ia)

        recherche_sans_resultat = not reponse.lieux and reponse.recherche_google != "indisponible"

        if recherche_sans_resultat and not deja_precise:
            resultat = construire_clarification(identifiant, date_creation, requete.texte_original, "aucun_resultat")
        else:
            resultat = resultat_json.assembler_resultat(
                identifiant=identifiant, statut="termine", date_creation=date_creation,
                texte_requete=requete.texte_original, intention=reponse.intention, mots_cles=reponse.mots_cles,
                texte_reponse=reponse.texte, recherche_google=reponse.recherche_google, lieux=reponse.lieux,
                sources=reponse.sources, avertissements=avertissements)
    except Exception as erreur:  # noqa: BLE001 - un fil d'arrière-plan doit toujours écrire un résultat
        journal.exception("La recherche %s a échoué", identifiant)
        resultat = resultat_json.assembler_resultat(
            identifiant=identifiant, statut="erreur", date_creation=date_creation, texte_requete=requete.texte_original,
            intention=None, mots_cles=rassembler_mots_cles(requete, []), texte_reponse="La recherche a échoué.",
            recherche_google="indisponible", lieux=classer_lieux(candidats), sources=[],
            avertissements=avertissements, erreur=str(erreur))

    resultat_json.ecrire_resultat(resultat)


def lancer_recherche(texte_requete: str, attendre_la_fin: bool = False, deja_precise: bool = False,
                     avec_resume_ia: bool = True) -> dict:
    """avec_resume_ia=False : pas de résumé rédigé par l'IA (le chat rédige sa propre réponse), résultat plus rapide."""
    requete = analyser_requete(texte_requete)
    identifiant = resultat_json.creer_identifiant_resultat(texte_requete)
    date_creation = resultat_json.maintenant()
    avertissements: list[str] = []

    if not requete.mots_cles:
        if deja_precise:
            resultat = resultat_json.assembler_resultat(
                identifiant=identifiant, statut="termine", date_creation=date_creation,
                texte_requete=requete.texte_original, intention=None, mots_cles=[], texte_reponse=TEXTE_REQUETE_VIDE,
                recherche_google="non_necessaire", lieux=[], sources=[], avertissements=avertissements)
        else:
            resultat = construire_clarification(identifiant, date_creation, requete.texte_original, "requete_floue")

        resultat_json.ecrire_resultat(resultat)

        return resultat

    cle_du_cache = " ".join(sorted(requete.mots_cles)) + ("" if avec_resume_ia else " |sans_resume")
    resultat_existant = cache_des_resultats.trouver_resultat(cle_du_cache)

    if resultat_existant is not None:
        return resultat_existant

    with ThreadPoolExecutor(max_workers=1) as executeur:
        lieux_referentiel_a_venir = executeur.submit(trouver_lieux_du_referentiel, requete, avertissements)
        lieux_connaissances = chercher_connaissances(requete, avertissements)
        lieux_referentiel = lieux_referentiel_a_venir.result()

    candidats = [*lieux_connaissances, *lieux_referentiel]
    coordonnees.completer_coordonnees(candidats, autoriser_geocodage=False)
    utiliser_google = not lieux_connaissances

    resultat_provisoire = resultat_json.assembler_resultat(
        identifiant=identifiant, statut="en_cours", date_creation=date_creation, texte_requete=requete.texte_original,
        intention=None, mots_cles=rassembler_mots_cles(requete, []),
        texte_reponse=TEXTE_GOOGLE_EN_COURS if utiliser_google else TEXTE_REDACTION_EN_COURS,
        recherche_google="en_cours" if utiliser_google else "non_necessaire",
        lieux=classer_lieux(candidats), sources=[], avertissements=avertissements)
    resultat_json.ecrire_resultat(resultat_provisoire)
    cache_des_resultats.memoriser(cle_du_cache, identifiant)

    fil_arriere_plan = threading.Thread(
        target=terminer_recherche, daemon=True,
        args=(identifiant, date_creation, requete, candidats, avertissements, utiliser_google, deja_precise, avec_resume_ia))
    fil_arriere_plan.start()

    if attendre_la_fin:
        fil_arriere_plan.join()
        return resultat_json.lire_resultat(identifiant)

    return resultat_provisoire


def preciser_recherche(id_resultat: str, id_option: str, texte_libre: str | None = None,
                       attendre_la_fin: bool = False) -> dict:
    resultat_precedent = resultat_json.lire_resultat(id_resultat)

    if resultat_precedent is None or resultat_precedent["statut"] != "clarification_necessaire":
        raise ValueError("Ce résultat n'attend aucune précision.")

    option = clarification.trouver_option(id_option)

    if option is None:
        raise ValueError(f"Option inconnue : {id_option}")

    texte_initial = resultat_precedent["clarification"]["requete_initiale"]
    identifiant = resultat_json.creer_identifiant_resultat(texte_initial)
    date_creation = resultat_json.maintenant()

    if option.get("urgence"):
        resultat = resultat_json.assembler_urgence(identifiant=identifiant, date_creation=date_creation,
                                                   texte_requete=texte_initial)
        resultat_json.ecrire_resultat(resultat)

        return resultat

    texte_precision = (texte_libre or "").strip()
    precision_manquante = not texte_precision and (not extraire_mots_utiles(texte_initial) or not option["termes_de_recherche"])

    if precision_manquante:
        resultat = resultat_json.assembler_clarification(
            identifiant=identifiant, date_creation=date_creation, texte_requete=texte_initial,
            type_clarification="saisie_libre", raison="precision_demandee", question=option["question_suivante"],
            options=[], option_choisie=option["id"], avertissements=[])
        resultat_json.ecrire_resultat(resultat)

        return resultat

    texte_complet = " ".join(partie for partie in (texte_initial, texte_precision, *option["termes_de_recherche"]) if partie)

    return lancer_recherche(texte_complet, attendre_la_fin=attendre_la_fin, deja_precise=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    requete_saisie = " ".join(sys.argv[1:]).strip()

    if not requete_saisie:
        sys.exit('Usage : python recherche.py "cacao"')

    resultat_final = lancer_recherche(requete_saisie, attendre_la_fin=True)
    print(json.dumps(resultat_final, ensure_ascii=False, indent=2))
    print(f"\nFichier JSON : {resultat_json.chemin_du_resultat(resultat_final['id_resultat'])}")
