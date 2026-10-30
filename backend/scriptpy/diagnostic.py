import threading
import time

import agent_ia
import base_donnees
import config
import recherche_web
from base_donnees import BaseIndisponible

DUREE_CACHE_SANTE_EN_SECONDES = 60
_cache_sante: tuple[float, list[dict]] | None = None
_verrou_sante = threading.Lock()


def _construire_etat(service: str, fonctionne: bool, message: str, consequence_si_absent: str) -> dict:
    return {"service": service, "ok": fonctionne, "message": message, "consequence_si_absent": consequence_si_absent}


def verifier_postgresql() -> dict:
    consequence = "Aucun lieu officiel ni connaissance : seule la recherche Google fonctionnera."

    try:
        tables_manquantes = base_donnees.lister_tables_manquantes()

        if tables_manquantes:
            return _construire_etat("PostgreSQL", False, f"tables manquantes : {', '.join(tables_manquantes)}", consequence)

        return _construire_etat("PostgreSQL", True, f"{base_donnees.compter_fragments()} fragments de connaissances indexés", consequence)
    except BaseIndisponible as erreur:
        return _construire_etat("PostgreSQL", False, str(erreur), consequence)


def verifier_agent_ia(appel_reel: bool) -> dict:
    """appel_reel=True (démarrage, console) : petit appel à chaque fournisseur pour vérifier clé et modèle."""
    consequence = "Pas d'IA : règles, résultats web et réponses rédigées automatiquement."
    fournisseurs = agent_ia.lister_les_fournisseurs()

    if not agent_ia.LANGCHAIN_DISPONIBLE:
        return _construire_etat("Agent IA (LangChain)", False, "LangChain non installé", consequence)

    if not fournisseurs:
        return _construire_etat("Agent IA (LangChain)", False,
                                f"désactivé (AGENT_FOURNISSEUR={config.AGENT_FOURNISSEUR}, clé absente ou fournisseur inconnu)",
                                consequence)

    if not appel_reel:
        etat = agent_ia.etat_public()
        return _construire_etat("Agent IA (LangChain)", etat["ia"] == "ok", etat["ia"], consequence)

    bilans = agent_ia.tester_les_fournisseurs()
    message = " ; ".join(f"{bilan['fournisseur']} : {bilan['message']}" for bilan in bilans)

    return _construire_etat("Agent IA (LangChain)", any(bilan["ok"] for bilan in bilans), message, consequence)


def verifier_vecteurs() -> dict:
    consequence = "Recherche par mots-clés seulement (pas de recherche par le sens)."

    if config.VECTEURS_FOURNISSEUR == "off":
        return _construire_etat("Vecteurs (RAG)", False, "désactivés (VECTEURS_FOURNISSEUR=off)", consequence)

    message = f"{config.VECTEURS_FOURNISSEUR} ({config.MODELE_VECTEURS}, {config.DIMENSION_VECTEUR} dimensions)"
    message += ", indexation automatique " + ("activée" if config.INDEXATION_AUTO else "désactivée")

    return _construire_etat("Vecteurs (RAG)", True, message, consequence)


def verifier_google() -> dict:
    fonctionne, message = recherche_web.tester_google()

    return _construire_etat("Recherche web", fonctionne, message, "Pas de recherche web : seules les données locales sont utilisées.")


def diagnostiquer_services(appel_reel_ia: bool = False) -> list[dict]:
    return [verifier_postgresql(), verifier_agent_ia(appel_reel_ia), verifier_vecteurs(), verifier_google()]


def etat_public_des_services() -> list[dict]:
    """Pour la route publique /sante : seulement le nom du service et ok, mis en cache (aucun appel par visite)."""
    global _cache_sante

    with _verrou_sante:
        if _cache_sante and time.monotonic() - _cache_sante[0] < DUREE_CACHE_SANTE_EN_SECONDES:
            return _cache_sante[1]

    etats = [{"service": etat["service"], "ok": etat["ok"]} for etat in diagnostiquer_services(appel_reel_ia=False)]

    with _verrou_sante:
        _cache_sante = (time.monotonic(), etats)

    return etats
