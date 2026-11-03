import logging

import uvicorn

import api
import config
import diagnostic
import resultat_json


def preparer_les_dossiers():
    for dossier in (config.DOSSIER_RESULTATS, config.DOSSIER_LIEUX_JSON, config.DOSSIER_PRODUITS_JSON,
                    config.DOSSIER_COMPLEMENTAIRES_JSON):
        dossier.mkdir(parents=True, exist_ok=True)


def supprimer_les_vieux_resultats():
    """Les fichiers donnees/resultats/ sont temporaires : le nettoyage continue ensuite toutes les heures (api.py)."""
    resultat_json.supprimer_les_resultats_anciens()


def afficher_diagnostic():
    for etat in diagnostic.diagnostiquer_services(appel_reel_ia=True):
        print(f"  {'OK' if etat['ok'] else '!!'}  {etat['service']:15s} {etat['message']}")

        if not etat["ok"]:
            print(f"      -> {etat['consequence_si_absent']}")

    print(f"\nAPI : http://{config.HOTE_API}:{config.PORT_API}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for bibliotheque in ("httpx", "httpcore", "google_genai", "groq", "openai", "ddgs", "primp"):
        logging.getLogger(bibliotheque).setLevel(logging.WARNING)   # sinon une clé peut apparaître dans les journaux
    preparer_les_dossiers()
    supprimer_les_vieux_resultats()
    afficher_diagnostic()
    uvicorn.run(api.app, host=config.HOTE_API, port=config.PORT_API)