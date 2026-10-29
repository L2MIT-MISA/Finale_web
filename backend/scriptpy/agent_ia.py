"""Agent Connectéo local construit avec LangChain et Ollama.

Tous les appels génératifs passent par ``langchain-ollama``. Aucun service de
modèle distant ni clé OpenRouter n'est utilisé. Les fonctions publiques gardent
le contrat historique afin que recherche.py et conversation.py restent stables.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as DelaiDepasse
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

try:
    from langchain.agents import create_agent
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langchain_core.tools import tool
    from langchain_ollama import ChatOllama
    LANGCHAIN_DISPONIBLE = True
except ImportError:
    create_agent = ChatOllama = None
    AIMessage = HumanMessage = SystemMessage = None
    LANGCHAIN_DISPONIBLE = False

    def tool(fonction):
        return fonction

import config

journal = logging.getLogger("agent_ia")
CONTEXTE_LOCAL_EN_TOKENS = 4096
DELAI_LOCAL_EN_SECONDES = 30
NOM_LOCAL = "langchain_ollama"


class _CreneauLocal:
    """Sérialise qwen et donne la priorité aux conversations utilisateur."""
    def __init__(self):
        self._condition = threading.Condition()
        self._occupe = False
        self._prioritaires_en_attente = 0

    def prendre(self, prioritaire: bool, delai: float) -> bool:
        fin = time.monotonic() + max(0, delai)
        with self._condition:
            if prioritaire:
                self._prioritaires_en_attente += 1
            try:
                while self._occupe or (not prioritaire and self._prioritaires_en_attente):
                    reste = fin - time.monotonic()
                    if reste <= 0:
                        return False
                    self._condition.wait(reste)
                self._occupe = True
                return True
            finally:
                if prioritaire:
                    self._prioritaires_en_attente -= 1
                    self._condition.notify_all()

    def rendre(self):
        with self._condition:
            self._occupe = False
            self._condition.notify_all()


_creneau_local = _CreneauLocal()
_verrou_etat = threading.Lock()
_en_panne_jusqua = 0.0
_executeur = ThreadPoolExecutor(max_workers=1, thread_name_prefix="langchain-ollama")


@dataclass
class ReponseAgent:
    texte: str
    fournisseur: str
    modele: str
    duree_en_ms: int


def nettoyer_texte_du_modele(texte: str) -> str:
    return re.sub(r"<think>.*?</think>", "", texte or "", flags=re.S | re.I).strip()


def extraire_objet_json(texte: str) -> str | None:
    texte, debut = nettoyer_texte_du_modele(texte), nettoyer_texte_du_modele(texte).find("{")
    if debut < 0:
        return None
    profondeur, chaine, echappe = 0, False, False
    for position in range(debut, len(texte)):
        caractere = texte[position]
        if chaine:
            if echappe: echappe = False
            elif caractere == "\\": echappe = True
            elif caractere == '"': chaine = False
            continue
        if caractere == '"': chaine = True
        elif caractere == "{": profondeur += 1
        elif caractere == "}":
            profondeur -= 1
            if profondeur == 0: return texte[debut:position + 1]
    return None


def _messages_langchain(messages: list[dict]):
    classes = {"system": SystemMessage, "assistant": AIMessage, "user": HumanMessage}
    return [classes.get(message.get("role"), HumanMessage)(content=str(message.get("content", "")))
            for message in messages]


def _modele(max_tokens: int, temperature: float) -> ChatOllama:
    return ChatOllama(
        model=config.MODELE_REDACTION, base_url=config.URL_OLLAMA,
        temperature=temperature, top_p=config.TOP_P, num_ctx=CONTEXTE_LOCAL_EN_TOKENS,
        num_predict=max_tokens, keep_alive=config.DUREE_MODELE_EN_MEMOIRE,
        reasoning=False, validate_model_on_init=False,
    )


def _est_en_panne() -> bool:
    with _verrou_etat:
        return _en_panne_jusqua > time.monotonic()


def _declarer_en_panne(secondes: float = 10):
    global _en_panne_jusqua
    with _verrou_etat:
        _en_panne_jusqua = time.monotonic() + secondes


def reinitialiser_les_pannes():
    global _en_panne_jusqua
    with _verrou_etat:
        _en_panne_jusqua = 0.0


def fournisseurs_configures() -> list[str]:
    return [NOM_LOCAL] if config.AGENT_LOCAL_ACTIF and LANGCHAIN_DISPONIBLE else []


def _executer_borne(fonction, delai: float):
    global _executeur
    futur = _executeur.submit(fonction)
    try:
        return futur.result(timeout=max(1.0, delai))
    except DelaiDepasse:
        futur.cancel()
        # Un appel réseau déjà commencé ne peut pas être tué par Future.cancel().
        # On remplace donc la file afin qu'un appel Ollama lent ne bloque pas tous les tours suivants.
        ancien_executeur = _executeur
        _executeur = ThreadPoolExecutor(max_workers=1, thread_name_prefix="langchain-ollama")
        ancien_executeur.shutdown(wait=False, cancel_futures=True)
        raise TimeoutError(f"Ollama n'a pas répondu en {delai:.0f} s")


def _contenu(message) -> str:
    contenu = getattr(message, "content", message)
    if isinstance(contenu, list):
        contenu = "".join(str(bloc.get("text", "")) if isinstance(bloc, dict) else str(bloc) for bloc in contenu)
    return nettoyer_texte_du_modele(str(contenu or ""))


@tool
def rechercher_sur_le_web(question: str) -> str:
    """Recherche des informations actuelles ou vérifiables sur le web lorsque les connaissances du modèle ne suffisent pas."""
    try:
        import recherche_web

        echecs = []
        for nom in config.ORDRE_FOURNISSEURS_RECHERCHE:
            fournisseur = recherche_web.FOURNISSEURS.get(nom)
            if fournisseur is None:
                continue
            try:
                resultats = fournisseur(question, 5)
            except recherche_web.FournisseurIndisponible as erreur:
                echecs.append(f"{nom}: {erreur}")
                continue
            if resultats:
                return "\n".join(
                    f"- {r.get('title', 'Sans titre')} — {r.get('snippet', '')[:500]} — {r.get('link', '')}"
                    for r in resultats[:5]
                )
        return "Recherche indisponible. " + " | ".join(echecs[:3])
    except Exception as erreur:
        journal.info("Outil web indisponible : %s", erreur)
        return "La recherche web est momentanément indisponible. Réponds avec tes connaissances et signale l'incertitude."


OUTILS_AGENT = [rechercher_sur_le_web]


def completer(messages: list[dict], *, max_tokens: int = 400,
              temperature: float | None = None, delai_max: float | None = None) -> ReponseAgent | None:
    """Réponse générale via un agent LangChain local capable d'utiliser ses outils."""
    if not LANGCHAIN_DISPONIBLE or not config.AGENT_LOCAL_ACTIF or _est_en_panne():
        return None
    temperature = config.TEMPERATURE if temperature is None else temperature
    budget = DELAI_LOCAL_EN_SECONDES if delai_max is None else max(1.0, delai_max)
    debut = time.monotonic()
    if not _creneau_local.prendre(True, budget):
        return None
    try:
        modele = _modele(max_tokens, temperature)
        agent = create_agent(model=modele, tools=OUTILS_AGENT)
        sortie = _executer_borne(lambda: agent.invoke({"messages": _messages_langchain(messages)}),
                                 budget)
        texte = _contenu(sortie["messages"][-1])
        if not texte:
            return None
        return ReponseAgent(texte, NOM_LOCAL, config.MODELE_REDACTION,
                            int((time.monotonic() - debut) * 1000))
    except Exception as erreur:  # LangChain/Ollama doit toujours laisser fonctionner le repli déterministe
        journal.warning("Agent LangChain/Ollama indisponible : %s", erreur)
        _declarer_en_panne()
        return None
    finally:
        _creneau_local.rendre()


def demander_json_detaille(messages: list[dict], classe: type[BaseModel], max_tokens: int = 400,
                           temperature: float | None = None, delai_max: float | None = None,
                           prioritaire: bool = True) -> tuple[BaseModel, ReponseAgent] | None:
    """Réponse structurée native LangChain, validée par le modèle Pydantic demandé."""
    if not LANGCHAIN_DISPONIBLE or not config.AGENT_LOCAL_ACTIF or _est_en_panne():
        return None
    temperature = config.TEMPERATURE if temperature is None else temperature
    budget = DELAI_LOCAL_EN_SECONDES if delai_max is None else max(1.0, delai_max)
    debut = time.monotonic()
    if not _creneau_local.prendre(prioritaire, budget):
        return None
    try:
        structure = _modele(max_tokens, temperature).with_structured_output(classe, method="json_schema")
        objet = _executer_borne(lambda: structure.invoke(_messages_langchain(messages)), budget)
        if not isinstance(objet, classe):
            objet = classe.model_validate(objet)
        informations = ReponseAgent(objet.model_dump_json(), NOM_LOCAL, config.MODELE_REDACTION,
                                    int((time.monotonic() - debut) * 1000))
        return objet, informations
    except Exception as erreur:
        journal.warning("Sortie structurée LangChain/Ollama indisponible : %s", erreur)
        if not isinstance(erreur, TimeoutError):
            _declarer_en_panne(5)
        return None
    finally:
        _creneau_local.rendre()


def demander_json(messages: list[dict], classe: type[BaseModel], max_tokens: int = 400,
                  temperature: float | None = None, delai_max: float | None = None,
                  prioritaire: bool = True) -> BaseModel | None:
    resultat = demander_json_detaille(messages, classe, max_tokens, temperature, delai_max, prioritaire)
    return resultat[0] if resultat else None


def etat_des_fournisseurs() -> list[dict]:
    return [{"fournisseur": NOM_LOCAL, "configure": config.AGENT_LOCAL_ACTIF and LANGCHAIN_DISPONIBLE,
             "modele": config.MODELE_REDACTION, "en_panne": _est_en_panne(), "framework": "LangChain"}]
