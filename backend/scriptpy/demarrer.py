import logging
import time

import uvicorn

import api
import config
import diagnostic


def preparer_les_dossiers():
    for dossier in (config.DOSSIER_RESULTATS, config.DOSSIER_LIEUX_JSON, config.DOSSIER_PRODUITS_JSON,
                    config.DOSSIER_COMPLEMENTAIRES_JSON):
        dossier.mkdir(parents=True, exist_ok=True)


def supprimer_les_vieux_resultats(jours: int = 7):
    """Les fichiers donnees/resultats/ sont temporaires (relus pendant quelques secondes par le site) : on évite qu'ils s'accumulent."""
    limite = time.time() - jours * 86400

    for fichier in config.DOSSIER_RESULTATS.glob("*.json"):
        try:
            if fichier.stat().st_mtime < limite:
                fichier.unlink()
        except OSError:
            pass


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