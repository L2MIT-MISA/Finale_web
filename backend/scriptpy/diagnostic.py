import httpx

import agent_ia
import base_donnees
import config
import recherche_web
from base_donnees import BaseIndisponible


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


def verifier_ollama() -> dict:
    consequence = "Pas de vecteurs ni de modèle local : recherche par mots-clés seulement, réponses rédigées automatiquement."

    try:
        reponse = httpx.get(f"{config.URL_OLLAMA}/api/tags", timeout=3)
        reponse.raise_for_status()
    except httpx.HTTPError as erreur:
        return _construire_etat("Ollama", False, f"injoignable ({erreur})", consequence)

    modeles_installes = [modele["name"] for modele in reponse.json().get("models", [])]
    modeles_manquants = [nom for nom in (config.MODELE_REDACTION, config.MODELE_VECTEURS)
                         if not any(installe == nom or installe.startswith(f"{nom}:") for installe in modeles_installes)]

    if modeles_manquants:
        return _construire_etat("Ollama", False, f"modèles à installer (ollama pull) : {', '.join(modeles_manquants)}", consequence)

    return _construire_etat("Ollama", True, f"modèles prêts : {config.MODELE_REDACTION}, {config.MODELE_VECTEURS}", consequence)


def verifier_langchain() -> dict:
    return _construire_etat("Agent LangChain", True, f"ChatOllama local : {config.MODELE_REDACTION}",
                            "Sans LangChain, le serveur ne peut pas démarrer.")


def verifier_google() -> dict:
    fonctionne, message = recherche_web.tester_google()

    return _construire_etat("Recherche web", fonctionne, message, "Pas de recherche web : seules les données locales sont utilisées.")


def diagnostiquer_services() -> list[dict]:
    return [verifier_postgresql(), verifier_langchain(), verifier_ollama(), verifier_google()]
