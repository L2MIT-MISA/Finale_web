"""Vecteurs Gemini (768 dimensions) et réponses structurées via l'agent LangChain."""
from __future__ import annotations

import functools
import logging
import math
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as DelaiDepasse

import httpx

import agent_ia
import config
from modeles import ReponseDuModele, ResumeDuModele

journal = logging.getLogger("modele_ia")

DELAI_VECTEURS_EN_SECONDES = 120
NOMBRE_DE_TOKENS_RESUME = 120
NOMBRE_DE_TOKENS_EXTRACTION = 900
# Extraction des lieux des pages web : tâche d'arrière-plan, bornée pour ne pas monopoliser l'IA
DELAI_EXTRACTION_EN_SECONDES = 90

_quota_vecteurs = None
_verrou_quota = threading.Lock()
_executeur_vecteurs = ThreadPoolExecutor(max_workers=2, thread_name_prefix="vecteurs")


class VecteursDesactives(ValueError):
    pass


def vecteurs_actifs() -> bool:
    return config.VECTEURS_FOURNISSEUR == "gemini"


def _normaliser(vecteur: list[float]) -> list[float]:
    """Gemini ne normalise pas les vecteurs réduits à 768 dimensions : la documentation demande de le faire soi-même."""
    norme = math.sqrt(sum(valeur * valeur for valeur in vecteur))

    return [valeur / norme for valeur in vecteur] if norme else vecteur


def _reserver_quota_vecteurs() -> bool:
    global _quota_vecteurs

    with _verrou_quota:
        if _quota_vecteurs is None:
            _quota_vecteurs = agent_ia.EtatFournisseur()

    return _quota_vecteurs.reserver(par_minute=config.VECTEURS_APPELS_PAR_MINUTE, par_jour=config.VECTEURS_APPELS_PAR_JOUR)


def _vecteurs_gemini(textes: list[str], type_de_texte: str, delai: float) -> list[list[float]]:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    if not config.AGENT_API_CLE:
        raise VecteursDesactives("AGENT_API_CLE absente : vecteurs Gemini impossibles")

    if not _reserver_quota_vecteurs():
        raise VecteursDesactives("quota de vecteurs atteint")

    modele = GoogleGenerativeAIEmbeddings(model=config.MODELE_VECTEURS, api_key=config.AGENT_API_CLE,
                                          output_dimensionality=config.DIMENSION_VECTEUR)

    def calculer():
        if type_de_texte == "requete":
            return [modele.embed_query(textes[0])]

        return modele.embed_documents(textes)

    # Le client Gemini ne reçoit pas de délai par LangChain : la durée est bornée ici.
    futur = _executeur_vecteurs.submit(calculer)

    try:
        vecteurs = futur.result(timeout=delai)
    except DelaiDepasse as erreur:
        raise httpx.TimeoutException(f"Gemini n'a pas renvoyé les vecteurs en {delai:.1f} s") from erreur

    return [_normaliser(list(vecteur)) for vecteur in vecteurs]


def calculer_vecteurs(textes: list[str], type_de_texte: str = "document",
                      delai: float = DELAI_VECTEURS_EN_SECONDES) -> list[list[float]]:
    if not vecteurs_actifs():
        raise VecteursDesactives("recherche vectorielle désactivée (VECTEURS_FOURNISSEUR=off)")

    vecteurs = _vecteurs_gemini(textes, type_de_texte, delai)

    for vecteur in vecteurs:
        if len(vecteur) != config.DIMENSION_VECTEUR:
            raise ValueError(f"Le modèle {config.MODELE_VECTEURS} renvoie {len(vecteur)} dimensions "
                             f"au lieu de {config.DIMENSION_VECTEUR} (voir schema_rag.sql et migration_vecteurs_768.sql)")

    return vecteurs


@functools.lru_cache(maxsize=256)
def calculer_vecteur_de_la_requete(texte: str) -> tuple[float, ...]:
    return tuple(calculer_vecteurs([texte], "requete", config.DELAI_VECTEUR_REQUETE_EN_SECONDES)[0])


def rediger_resume(messages: list[dict]) -> ResumeDuModele | None:
    return agent_ia.demander_json(messages, ResumeDuModele, NOMBRE_DE_TOKENS_RESUME, delai_max=45)


def extraire_lieux(messages: list[dict]) -> ReponseDuModele | None:
    # Priorité basse : une conversation en cours passe toujours avant cette tâche d'arrière-plan
    return agent_ia.demander_json(messages, ReponseDuModele, NOMBRE_DE_TOKENS_EXTRACTION,
                                  delai_max=DELAI_EXTRACTION_EN_SECONDES, prioritaire=False)
