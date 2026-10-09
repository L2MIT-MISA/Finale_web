import os
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

import agent_ia
import config
import conversation
import diagnostic
import indexation
import modele_ia
import recherche
import resultat_json


def demarrer_les_modeles_puis_indexer(evenement_arret):
    modele_ia.prechauffer_modeles()
    indexation.reindexer_regulierement(evenement_arret)


@asynccontextmanager
async def cycle_de_vie(application):
    evenement_arret = threading.Event()
    # Un seul fil, l'un après l'autre : charger deux modèles en même temps peut saturer la mémoire d'Ollama
    threading.Thread(target=demarrer_les_modeles_puis_indexer, args=(evenement_arret,), daemon=True).start()
    yield
    evenement_arret.set()


application = FastAPI(title="Recherche de lieux - Madagascar", lifespan=cycle_de_vie)
application.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
                           allow_methods=["GET", "POST", "DELETE", "OPTIONS"], allow_headers=["*"])
app = application


class DemandeDeRecherche(BaseModel):
    requete: str = Field(min_length=1, max_length=200)


class MessageDeChat(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=64)      # conservé par le client (web ou mobile) d'un message à l'autre
    requete_id: str | None = Field(default=None, max_length=64)      # identifiant unique de CE message : un renvoi ne le duplique pas


_appels_recents: dict[str, deque] = defaultdict(deque)
_verrou_limite = threading.Lock()


def limiter_le_debit(requete: Request):
    """Au plus LIMITE_REQUETES_PAR_MINUTE messages par minute et par adresse : protège le quota de l'API d'IA."""
    adresse = requete.client.host if requete.client else "inconnue"
    maintenant = time.monotonic()

    with _verrou_limite:
        appels = _appels_recents[adresse]

        while appels and maintenant - appels[0] > 60:
            appels.popleft()

        if len(appels) >= config.LIMITE_REQUETES_PAR_MINUTE:
            raise HTTPException(status_code=429, detail="Trop de messages envoyés. Réessayez dans une minute.")

        appels.append(maintenant)

        if len(_appels_recents) > 5000:
            for cle in [cle for cle, valeur in _appels_recents.items() if not valeur]:
                _appels_recents.pop(cle, None)


class ReponseDeClarification(BaseModel):
    id_resultat: str = Field(max_length=100)
    id_option: str = Field(max_length=50)
    texte_libre: str | None = Field(default=None, max_length=200)


@application.get("/")
def afficher_la_page_de_demonstration():
    if not config.PAGE_WEB_DEMONSTRATION.is_file():
        return {"service": "Assistant Connectéo - recherche de lieux",
                "routes": ["/chat", "/recherche", "/resultats/{id}", "/sante"]}

    return FileResponse(config.PAGE_WEB_DEMONSTRATION)


@application.get("/fond.jpg")
def afficher_l_image_de_fond():
    chemin = config.DOSSIER_PROJET / "fond.jpg"

    if not chemin.is_file():
        raise HTTPException(status_code=404, detail="fond.jpg absent")

    return FileResponse(chemin)


@application.get("/favicon.ico", include_in_schema=False)
def ignorer_l_icone():
    return Response(status_code=204)


@application.get("/sante")
def verifier_les_services():
    return diagnostic.diagnostiquer_services()


@application.get("/sante/rapide")
def verifier_rapidement():
    """Sans appel réseau : pour savoir si l'API répond (utilisé par l'application mobile avant d'écrire)."""
    return {"ok": True, "agent_ia": agent_ia.etat_des_fournisseurs()}


@application.post("/chat")
def discuter(message: MessageDeChat, requete: Request):
    """Route unique du site web et de l'application mobile : une discussion continue, avec mémoire.

    Réponse : le résultat complet (message, lieux avec images, suggestions...). Si `statut` vaut « en_cours »,
    relire GET /resultats/{id_resultat} toutes les 1 à 2 secondes jusqu'à un autre statut."""
    limiter_le_debit(requete)

    try:
        return conversation.traiter_message(message.message, message.session_id, message.requete_id)
    except ValueError as erreur:
        raise HTTPException(status_code=400, detail=str(erreur)) from erreur


@application.get("/chat/{session_id}/historique")
def lire_l_historique(session_id: str):
    messages = conversation.lire_historique(session_id)

    if messages is None:
        raise HTTPException(status_code=404, detail="Session inconnue ou expirée")

    return {"session_id": session_id, "messages": messages}


@application.delete("/chat/{session_id}")
def recommencer_la_conversation(session_id: str):
    return {"session_id": session_id, "supprimee": conversation.oublier_la_session(session_id)}


@application.post("/recherche")
def demander_une_recherche(demande: DemandeDeRecherche, requete: Request):
    limiter_le_debit(requete)

    return recherche.lancer_recherche(demande.requete)


@application.post("/recherche/preciser")
def preciser_une_recherche(reponse: ReponseDeClarification):
    try:
        return recherche.preciser_recherche(reponse.id_resultat, reponse.id_option, reponse.texte_libre)
    except ValueError as erreur:
        raise HTTPException(status_code=400, detail=str(erreur)) from erreur


@application.get("/resultats/{id_resultat}")
def lire_un_resultat(id_resultat: str):
    resultat = resultat_json.lire_resultat(id_resultat)

    if resultat is None:
        raise HTTPException(status_code=404, detail="Résultat inconnu")

    return resultat
