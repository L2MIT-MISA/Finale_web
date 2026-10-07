
import os
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USER = os.environ["NEO4J_USER"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]
NEO4J_DB = os.getenv("NEO4J_DB") or os.getenv("NEO4J_DATABASE", "neo4j")

LIMITE_LIEUX = 10
RAYON_RECHERCHE_PYLONES_METRES = 35000
TECHNOLOGIES = ("2G", "3G", "4G", "5G")

PORTEES_REALISTES_M = {
    "2G": 35000,
    "3G": 10000,
    "4G": 5000,
    "5G": 1000,
}

FICHIER_CLEANED = "data/cleaned_data.json"

# ============================================================
# 1. CHARGEMENT DES LIEUX NETTOYÉS
# ============================================================

def charger_lieux() -> list[dict]:
    with open(FICHIER_CLEANED, "r", encoding="utf-8") as file:
        data = json.load(file)

    lieux = []
    for index, lieu in enumerate(data["lieux"]):
        properties = lieu["properties"]
        latitude = properties.get("lat")
        longitude = properties.get("lon")

        if latitude is None or longitude is None:
            continue

        categories = properties.get("categories") or []
        lieux.append({
            "id": f"geo_{index + 1}",
            "name": properties.get("name", "Sans nom"),
            "address": properties.get("formatted", "Adresse inconnue"),
            "latitude": float(latitude),
            "longitude": float(longitude),
            "category": categories[0] if categories else None,
            "phone": properties.get("phone"),
            "website": properties.get("website"),
            "opening_hours": properties.get("opening_hours"),
        })

    return lieux

# ============================================================
# 2. NEO4J — REQUÊTE DE LECTURE SEULE
# ============================================================

REQUETE_PYLONES_PROCHES = """
UNWIND $lieux AS lieu
MATCH (p:Pylone)
WHERE p.lat IS NOT NULL
  AND p.lon IS NOT NULL
  AND p.portee_km IS NOT NULL
WITH lieu, p,
     point.distance(
       point({latitude: toFloat(lieu.latitude), longitude: toFloat(lieu.longitude)}),
       point({latitude: toFloat(p.lat), longitude: toFloat(p.lon)})
     ) AS distance_m
WHERE distance_m <= $rayon_max
RETURN lieu.id AS lieu_id,
       collect({
         nom_site: p.nom_site,
         operateur: p.code_operateur,
         portee_km: toFloat(p.portee_km),
         tech_2g: p.tech_2g,
         tech_3g: p.tech_3g,
         tech_4g: p.tech_4g,
         tech_5g: p.tech_5g,
         distance_m: distance_m
       }) AS pylones
"""

def recuperer_pylones(driver, lieux: list[dict]) -> dict:
    params_lieux = [
        {"id": lieu["id"], "latitude": lieu["latitude"], "longitude": lieu["longitude"]}
        for lieu in lieux
    ]

    with driver.session(database=NEO4J_DB) as session:
        result = session.run(
            REQUETE_PYLONES_PROCHES,
            lieux=params_lieux,
            rayon_max=RAYON_RECHERCHE_PYLONES_METRES,
        )
        return {record["lieu_id"]: record["pylones"] for record in result}

# ============================================================
# 3. UTILITAIRE — VALEUR TECHNOLOGIQUE
# ============================================================

def est_actif(valeur) -> bool:
    if isinstance(valeur, bool):
        return valeur
    if valeur is None:
        return False
    return str(valeur).strip().lower() in {"oui", "yes", "true", "1"}

# ============================================================
# 4. PORTÉE EFFECTIVE
# ============================================================

def portee_effective_m(pylone: dict, technologie: str) -> float | None:
    portee_site_km = pylone.get("portee_km")
    if portee_site_km is None:
        return None

    try:
        portee_site_m = float(portee_site_km) * 1000
    except (TypeError, ValueError):
        return None

    return min(portee_site_m, PORTEES_REALISTES_M[technologie])

def pylone_valide_pour_technologie(pylone: dict, technologie: str) -> bool:
    cle = f"tech_{technologie.lower()}"

    if not est_actif(pylone.get(cle)):
        return False

    distance = pylone.get("distance_m")
    portee = portee_effective_m(pylone, technologie)

    if distance is None or portee is None:
        return False

    return float(distance) <= portee

# ============================================================
# 5. ÉVALUATION DE LA CONNECTIVITÉ
# ============================================================

def evaluer_connectivite(pylones_bruts: list[dict]) -> dict:
    if not pylones_bruts:
        return {
            "available": False,
            "operators": {},
            "summary": {
                "technologies_available": [],
                "operators_available": []
            },
        }

    par_operateur: dict[str, list[dict]] = {}

    for pylone in pylones_bruts:
        operateur = pylone.get("operateur") or "INCONNU"
        par_operateur.setdefault(operateur, []).append(pylone)

    operators_resultat = {}
    toutes_technologies = set()

    for operateur, pylones_operateur in par_operateur.items():
        technologies = {}
        pylones_par_technologie = {}

        for technologie in TECHNOLOGIES:
            candidats = [
                pylone for pylone in pylones_operateur
                if pylone_valide_pour_technologie(pylone, technologie)
            ]

            if not candidats:
                technologies[technologie] = False
                pylones_par_technologie[technologie] = None
                continue

            meilleur_pylone = min(candidats, key=lambda pylone: pylone["distance_m"])
            technologies[technologie] = True
            toutes_technologies.add(technologie)

            pylones_par_technologie[technologie] = {
                "name": meilleur_pylone.get("nom_site") or "Site inconnu",
                "distance_meters": round(meilleur_pylone["distance_m"]),
            }

        technologies_actives = [
            technologie for technologie in TECHNOLOGIES
            if technologies[technologie]
        ]

        operators_resultat[operateur] = {
            "technologies": technologies,
            "technologies_actives": technologies_actives,
            "nearest_towers_by_technology": pylones_par_technologie,
        }

    technologies_disponibles = [
        technologie for technologie in TECHNOLOGIES
        if technologie in toutes_technologies
    ]

    return {
        "available": bool(technologies_disponibles),
        "operators": operators_resultat,
        "summary": {
            "technologies_available": technologies_disponibles,
            "operators_available": list(operators_resultat.keys()),
        },
    }

# ============================================================
# 6. FUSION GEOAPIFY + NEO4J
# ============================================================

def resume_connectivite_texte(connectivite: dict) -> str:
    if not connectivite["available"]:
        return "Aucune couverture connue"

    return ", ".join(connectivite["summary"]["technologies_available"])

def fusionner(lieux: list[dict], pylones_par_lieu: dict) -> list[dict]:
    resultats = []

    for lieu in lieux:
        pylones = pylones_par_lieu.get(lieu["id"], [])
        connectivite = evaluer_connectivite(pylones)

        resultats.append({
            "id": lieu["id"],
            "name": lieu["name"],
            "type": lieu.get("category"),
            "address": lieu["address"],
            "location": {
                "latitude": lieu["latitude"],
                "longitude": lieu["longitude"]
            },
            "phone": lieu.get("phone"),
            "website": lieu.get("website"),
            "openingHours": lieu.get("opening_hours"),
            "connectivity": resume_connectivite_texte(connectivite),
            "connectivityDetails": connectivite,
        })

    return resultats

# ============================================================
# 7. PIPELINE COMPLET
# ============================================================

def pipeline_fusion() -> dict:
    print(" Chargement des données nettoyées...")
    lieux = charger_lieux()
    print(f"   → {len(lieux)} lieu(x)")

    if not lieux:
        return {"count": 0, "results": []}

    print(" Connexion Neo4j...")

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    try:
        driver.verify_connectivity()
        pylones_par_lieu = recuperer_pylones(driver, lieux)
    finally:
        driver.close()

    total_pylones = sum(
        len(pylones) for pylones in pylones_par_lieu.values()
    )

    print(f"   → {total_pylones} pylône(s) candidat(s)")
    print(" Fusion des données...")

    resultats = fusionner(lieux, pylones_par_lieu)

    return {
        "query": "données nettoyées",
        "count": len(resultats),
        "results": resultats
    }

FICHIER_FINAL = "data/final_results.json"

def sauvegarder_resultats(resultats: dict) -> None:
    with open(FICHIER_FINAL, "w", encoding="utf-8") as file:
        json.dump(resultats, file, ensure_ascii=False, indent=2)

    print(f"\nRésultats sauvegardés dans : {FICHIER_FINAL}")

# ============================================================
# 8. TEST
# ============================================================

if __name__ == "__main__":
    sortie = pipeline_fusion()
    sauvegarder_resultats(sortie)

    print("\n" + "=" * 70)
    print("RÉSULTATS")
    print("=" * 70)

    for lieu in sortie["results"]:
        print(f"\n {lieu['name']}")
        print(f"   Adresse : {lieu['address']}")

        latitude = lieu["location"]["latitude"]
        longitude = lieu["location"]["longitude"]
        print(f"   GPS : {latitude}, {longitude}")
        print(f"    {lieu['connectivity']}")

        details = lieu["connectivityDetails"]

        if not details["available"]:
            continue

        for operateur, donnees in details["operators"].items():
            actives = donnees["technologies_actives"]

            print(
                f"    {operateur} : "
                + (", ".join(actives) if actives else "aucune")
            )

            for tech, info in donnees["nearest_towers_by_technology"].items():
                if info:
                    print(
                        f"        {tech} : "
                        f"{info['name']} à "
                        f"{info['distance_meters']} m"
                    )