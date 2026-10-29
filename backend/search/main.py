import asyncio
import json
import logging
import sys
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from dotenv import dotenv_values
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("connecteo")

app = FastAPI(title="Connecteo Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent


class SearchRequest(BaseModel):
    query: str
    type: str
    category: str | None = None
    intent: str | None = None
    location: str | None = None
    relation: str | None = None


# ============================================================
# Verrou global anti-collision (voir explication détaillée dans
# les échanges précédents) : le pipeline lit/écrit des fichiers à
# des chemins FIXES (src/data/*.json). Sans ce verrou, deux
# recherches simultanées pourraient mélanger leurs résultats.
# ============================================================
verrou_pipeline = asyncio.Lock()

TIMEOUT_SECONDES = 60

CATEGORIES_GEOAPIFY = {
    # Restauration
    "restaurant": "catering.restaurant",
    "fast_food": "catering.fast_food",
    "fast food": "catering.fast_food",
    "bar": "catering.bar",

    # Santé
    "pharmacie": "healthcare.pharmacy",
    "pharmacy": "healthcare.pharmacy",
    "hopital": "healthcare.hospital",
    "hôpital": "healthcare.hospital",
    "hospital": "healthcare.hospital",
    "clinique": "healthcare.clinic_or_praxis",
    "medecin": "healthcare.clinic_or_praxis",
    "médecin": "healthcare.clinic_or_praxis",
    "dentiste": "healthcare.dentist",

    # Hébergement
    "hotel": "accommodation.hotel",
    "hôtel": "accommodation.hotel",
    "hostel": "accommodation.hostel",
    "auberge": "accommodation.guest_house",
    "motel": "accommodation.motel",

    # Commerce
    "supermarche": "commercial.supermarket",
    "supermarché": "commercial.supermarket",
    "magasin": "commercial",
    "boutique": "commercial",
    "shopping": "commercial",
    "centre commercial": "commercial.shopping_mall",
    "boulangerie": "commercial.bakery",

    # Éducation
    "ecole": "education.school",
    "école": "education.school",
    "lycee": "education.school",
    "lycée": "education.school",
    "universite": "education.university",
    "université": "education.university",
    "college": "education.college",
    "collège": "education.college",

    # Services
    "banque": "service.financial.bank",
    "atm": "service.financial.atm",
    "distributeur": "service.financial.atm",
    "station essence": "service.vehicle.fuel",
    "station service": "service.vehicle.fuel",
    "garage": "service.vehicle.repair",

    # Transport
    "parking": "parking",
    "station de recharge": "service.vehicle.charging_station",
    "bus": "public_transport.bus",
    "gare": "public_transport.train",
    "aeroport": "airport",
    "aéroport": "airport",

    # Loisirs / culture
    "musee": "entertainment.museum",
    "musée": "entertainment.museum",
    "cinema": "entertainment.cinema",
    "cinéma": "entertainment.cinema",
    "parc": "leisure.park",
    "terrain de jeu": "leisure.playground",
    "salle de sport": "sport",
    "tourisme": "tourism",
}


def _executer_etape(commande: list[str], nom_etape: str) -> None:
    """
    Exécute une étape avec un timeout, et capture stdout/stderr pour
    les inclure dans une erreur HTTP claire — plus besoin d'aller
    chercher le message dans le terminal d'uvicorn : il revient
    directement dans la réponse de l'API.
    """
    try:
        resultat = subprocess.run(
            commande,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDES,
        )
    except subprocess.TimeoutExpired:
        logger.error(f"[{nom_etape}] dépassement du délai ({TIMEOUT_SECONDES}s)")
        raise HTTPException(
            status_code=504,
            detail=f"Étape « {nom_etape} » trop longue (> {TIMEOUT_SECONDES}s).",
        )

    if resultat.returncode != 0:
        logger.error(f"[{nom_etape}] échec :\n{resultat.stdout}\n{resultat.stderr}")
        raise HTTPException(
            status_code=502,
            detail={
                "message": f"Échec de l'étape « {nom_etape} »",
                "stdout": resultat.stdout.strip()[-2000:],
                "stderr": resultat.stderr.strip()[-2000:],
            },
        )

    logger.info(f"[{nom_etape}] terminé avec succès")


def _executer_pipeline(query: str, categorie: str) -> dict:
    _executer_etape(
        ["node", str(BASE_DIR / "scripts" / "main.js"), query, categorie],
        "recherche Geoapify",
    )
    _executer_etape(
        [sys.executable, str(BASE_DIR / "services" / "datacleaning.py")],
        "nettoyage des données",
    )
    _executer_etape(
        [sys.executable, str(BASE_DIR / "services" / "datafusion.py")],
        "fusion Neo4j",
    )

    fichier_final = BASE_DIR / "data" / "final_results.json"
    if not fichier_final.exists():
        raise HTTPException(
            status_code=500,
            detail="Le fichier final_results.json n'a pas été généré.",
        )

    with open(fichier_final, "r", encoding="utf-8") as file:
        return json.load(file)


PYLON_FIELDS = """
    p.nom AS nom, p.code_site AS code_site, p.type_site AS type_site,
    p.lat AS lat, p.lon AS lon, p.hauteur_m AS hauteur_m,
    p.nom_commune AS nom_commune, p.nom_district AS nom_district,
    p.nom_region AS nom_region, p.milieu AS milieu,
    p.proprietaire AS proprietaire, p.code_operateur AS code_operateur,
    p.mutualisation AS mutualisation, p.source_energie AS source_energie,
    p.portee_km AS portee_km, p.tech_2g AS tech_2g, p.tech_3g AS tech_3g,
    p.tech_4g AS tech_4g, p.tech_5g AS tech_5g
"""


def _database_driver():
    config = dotenv_values(BASE_DIR / ".env")
    return GraphDatabase.driver(
        config["NEO4J_URI"],
        auth=(config["NEO4J_USER"], config["NEO4J_PASSWORD"]),
    ), config.get("NEO4J_DATABASE") or config.get("NEO4J_DB") or "neo4j"


def _technology_active(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"oui", "yes", "true", "1"}


def _read_pylons(cypher: str, parameters: dict) -> list[dict]:
    driver, database = _database_driver()
    try:
        with driver.session(database=database) as session:
            pylons = [record.data() for record in session.run(cypher, **parameters)]
    finally:
        driver.close()
    for pylon in pylons:
        for technology in ("tech_2g", "tech_3g", "tech_4g", "tech_5g"):
            pylon[technology] = _technology_active(pylon.get(technology))
    return pylons


@app.get("/api/pylones/bbox")
async def pylons_in_bbox(minLat: float, minLng: float, maxLat: float, maxLng: float):
    cypher = f"""
        MATCH (p:Pylone)
        WHERE p.lat IS NOT NULL AND p.lon IS NOT NULL
          AND toFloat(p.lat) >= $min_lat AND toFloat(p.lat) <= $max_lat
          AND toFloat(p.lon) >= $min_lng AND toFloat(p.lon) <= $max_lng
        RETURN {PYLON_FIELDS}
        LIMIT 1000
    """
    return await run_in_threadpool(
        _read_pylons,
        cypher,
        {"min_lat": minLat, "min_lng": minLng, "max_lat": maxLat, "max_lng": maxLng},
    )


@app.get("/api/pylones")
async def all_pylons():
    cypher = f"""
        MATCH (p:Pylone)
        WHERE p.lat IS NOT NULL AND p.lon IS NOT NULL
        RETURN {PYLON_FIELDS}
        LIMIT 5000
    """
    return await run_in_threadpool(_read_pylons, cypher, {})


@app.get("/")
def root():
    return {"message": "Connecteo Backend fonctionne !"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(BASE_DIR / "backend" / "static" / "favicon.ico")


@app.post("/search")
async def search(data: SearchRequest):
    if not data.category:
        raise HTTPException(status_code=400, detail="La catégorie est obligatoire.")

    keyword_normalise = data.category.strip().lower()
    categorie = CATEGORIES_GEOAPIFY.get(keyword_normalise)

    if categorie is None:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Catégorie inconnue",
                "keyword": data.category,
                "categories_disponibles": sorted(CATEGORIES_GEOAPIFY.keys()),
            },
        )

    query = data.location or data.query

    async with verrou_pipeline:
        return await run_in_threadpool(_executer_pipeline, query, categorie)


@app.get("/health")
def health():
    return {"status": "ok"}