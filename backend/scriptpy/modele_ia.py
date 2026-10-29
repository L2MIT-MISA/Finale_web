"""Vecteurs Ollama et réponses structurées via l'agent LangChain local."""
from __future__ import annotations

import functools
import logging

import httpx

import agent_ia
import config
from modeles import ReponseDuModele, ResumeDuModele

journal = logging.getLogger("modele_ia")

DELAI_VECTEURS_EN_SECONDES = 120
# Vecteur de la requête de l'utilisateur : au-delà, la recherche se fait par mots-clés seulement (plutôt qu'attendre)
DELAI_VECTEUR_REQUETE_EN_SECONDES = 1.5
NOMBRE_DE_TOKENS_RESUME = 120
NOMBRE_DE_TOKENS_EXTRACTION = 900
# Extraction des lieux des pages web : tâche d'arrière-plan, bornée pour ne pas monopoliser le modèle local
DELAI_EXTRACTION_EN_SECONDES = 90


def _prefixe(type_de_texte: str) -> str:
    """nomic-embed-text donne de bien meilleurs résultats avec ces préfixes (documentés par ses auteurs)."""
    if "nomic" not in config.MODELE_VECTEURS.lower():
        return ""

    return "search_query: " if type_de_texte == "requete" else "search_document: "


def calculer_vecteurs(textes: list[str], type_de_texte: str = "document",
                      delai: float = DELAI_VECTEURS_EN_SECONDES) -> list[list[float]]:
    prefixe = _prefixe(type_de_texte)
    reponse = httpx.post(f"{config.URL_OLLAMA}/api/embed", timeout=httpx.Timeout(delai, connect=3.0),
                         json={"model": config.MODELE_VECTEURS, "input": [prefixe + texte for texte in textes],
                               "keep_alive": config.DUREE_MODELE_EN_MEMOIRE})
    reponse.raise_for_status()

    try:
        vecteurs = reponse.json()["embeddings"]
    except (KeyError, TypeError, ValueError) as erreur:
        raise ValueError("Ollama a renvoyé une réponse sans vecteurs") from erreur

    for vecteur in vecteurs:
        if len(vecteur) != config.DIMENSION_VECTEUR:
            raise ValueError(f"Le modèle {config.MODELE_VECTEURS} renvoie {len(vecteur)} dimensions "
                             f"au lieu de {config.DIMENSION_VECTEUR} (voir schema_rag.sql et migration_vecteurs_768.sql)")

    return vecteurs


@functools.lru_cache(maxsize=256)
def calculer_vecteur_de_la_requete(texte: str) -> tuple[float, ...]:
    return tuple(calculer_vecteurs([texte], "requete", DELAI_VECTEUR_REQUETE_EN_SECONDES)[0])


def rediger_resume(messages: list[dict]) -> ResumeDuModele | None:
    return agent_ia.demander_json(messages, ResumeDuModele, NOMBRE_DE_TOKENS_RESUME, delai_max=45)


def extraire_lieux(messages: list[dict]) -> ReponseDuModele | None:
    # Priorité basse : une conversation en cours passe toujours avant cette tâche d'arrière-plan
    return agent_ia.demander_json(messages, ReponseDuModele, NOMBRE_DE_TOKENS_EXTRACTION,
                                  delai_max=DELAI_EXTRACTION_EN_SECONDES, prioritaire=False)


def prechauffer_modeles():
    """Charge en mémoire les modèles locaux utilisés par LangChain et le RAG."""
    try:
        calculer_vecteurs(["préchauffage"])

        if not config.AGENT_LOCAL_ACTIF:
            return

        reponse = httpx.post(f"{config.URL_OLLAMA}/api/chat", timeout=agent_ia.DELAI_LOCAL_EN_SECONDES, json={
            "model": config.MODELE_REDACTION, "messages": [{"role": "user", "content": "ok"}], "stream": False,
            "think": False, "keep_alive": config.DUREE_MODELE_EN_MEMOIRE,
            "options": {"num_ctx": agent_ia.CONTEXTE_LOCAL_EN_TOKENS, "num_predict": 1}})
        reponse.raise_for_status()
    except (httpx.HTTPError, ValueError) as erreur:
        journal.warning("Préchauffage des modèles impossible : %s", erreur)
