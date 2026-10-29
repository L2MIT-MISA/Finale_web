import argparse
import json

import pandas as pd

import config

NOM_DU_FICHIER = "communes_infos.json"
SOURCE_DES_DONNEES = ("Carte_Infra_Opér_Début_2024_VFin.xlsx : feuilles Population, AccèsEelectricité, "
                      "Desserte_des_Communes, Infra_2022")
TECHNOLOGIES_PAR_QUALITE = ("4G", "3G", "2G")
# La lettre E de la feuille Desserte n'est pas confirmée : on n'attribue pas de couverture à cet opérateur
OPERATEURS_NON_CONFIRMES = {"GULFSAT"}


def lire_csv(nom_table: str, colonnes_en_texte: list[str]) -> pd.DataFrame:
    return pd.read_csv(config.DOSSIER_CSV_PROPRES / f"{nom_table}.csv", dtype={colonne: str for colonne in colonnes_en_texte})


def formater_nombre(nombre) -> str:
    return f"{int(nombre):,}".replace(",", " ")


def decrire_population(population: pd.Series | None) -> str | None:
    if population is None:
        return None

    return (f"Population recensée : {formater_nombre(population['habitants'])} habitants "
            f"({formater_nombre(population['menages'])} ménages) dans {int(population['nombre_fokontany'])} fokontany.")


def decrire_electricite(acces: pd.Series | None) -> str | None:
    if acces is None:
        return None

    if not acces["existence_electricite"]:
        return "Aucune électricité signalée dans la commune."

    return (f"Électricité : {int(acces['nb_fokontany_avec_acces'])} fokontany sur {int(acces['nb_fokontany_total'])} "
            f"desservis ({acces['taux_couverture_pct']:.0f} %), {acces['taux_acces_menages_pct']:.1f} % des ménages avec accès.")


def trouver_meilleure_technologie(ligne: pd.Series) -> str:
    for technologie in TECHNOLOGIES_PAR_QUALITE:
        if ligne[f"tech_{technologie.lower()}"]:
            return technologie

    return "aucune"


def decrire_couverture(couverture_commune: pd.DataFrame | None) -> str | None:
    if couverture_commune is None:
        return None

    operateurs_par_technologie: dict[str, list[str]] = {}

    for _, ligne in couverture_commune.iterrows():
        operateurs_par_technologie.setdefault(trouver_meilleure_technologie(ligne), []).append(ligne["code_operateur"].capitalize())

    morceaux = [f"{technologie} : {', '.join(sorted(operateurs_par_technologie[technologie]))}"
                for technologie in (*TECHNOLOGIES_PAR_QUALITE, "aucune") if technologie in operateurs_par_technologie]
    annee = int(couverture_commune["annee_mesure"].iloc[0])

    return f"Couverture mobile {annee} (meilleure technologie par opérateur) — " + " ; ".join(morceaux) + "."


def construire_enregistrement(commune: pd.Series, pylones: pd.Series, population, acces, couverture_commune) -> dict:
    type_de_commune = "urbaine" if commune["milieu"] == "URBAIN" else "rurale"
    morceaux = [f"Commune {type_de_commune} du district {commune['nom_district']} (région {commune['nom_region']}).",
                decrire_population(population), decrire_electricite(acces), decrire_couverture(couverture_commune),
                f"{int(pylones['nombre'])} pylône(s) de télécommunication."]

    return {
        "Produit": None,
        "Zone": commune["nom_region"],
        "District": commune["nom_district"],
        "Lieu": commune["nom"],
        "Catégorie": f"Commune {type_de_commune}",
        "Code": commune["codecom"],
        "Niveau": "commune",
        "Latitude": round(float(pylones["latitude"]), 6),
        "Longitude": round(float(pylones["longitude"]), 6),
        "Precision": "centroide",
        "Note_Google": None,
        "Nb_avis_Google": None,
        "Description": " ".join(morceau for morceau in morceaux if morceau),
        "Avis": None,
        "Sources": SOURCE_DES_DONNEES,
    }


def generer_fichier_complementaire() -> tuple[int, int]:
    communes = (lire_csv("commune", ["codecom", "codedist"])
                .merge(lire_csv("district", ["codedist", "codereg"]).rename(columns={"nom": "nom_district"})[["codedist", "codereg", "nom_district"]], on="codedist")
                .merge(lire_csv("region", ["codereg"]).rename(columns={"nom": "nom_region"})[["codereg", "nom_region"]], on="codereg"))

    populations = (lire_csv("population_fokontany", ["codecom_brut"]).groupby("codecom_brut")
                   .agg(habitants=("population", "sum"), menages=("menages", "sum"), nombre_fokontany=("population", "size")))
    acces_electricite = lire_csv("acces_electricite_commune", ["codecom"]).set_index("codecom")

    couverture = lire_csv("couverture_operateur_commune", ["codecom"])
    couverture = couverture[(couverture["annee_mesure"] == couverture["annee_mesure"].max())
                            & ~couverture["code_operateur"].isin(OPERATEURS_NON_CONFIRMES)]
    couvertures_par_commune = {code: groupe for code, groupe in couverture.groupby("codecom")}

    pylones = lire_csv("pylone", ["codecom"]).dropna(subset=["latitude", "longitude"])
    pylones_par_commune = pylones.groupby("codecom").agg(latitude=("latitude", "mean"), longitude=("longitude", "mean"),
                                                         nombre=("code_site", "size"))

    enregistrements = []

    for _, commune in communes.iterrows():
        code = commune["codecom"]

        if code not in pylones_par_commune.index:
            continue

        enregistrements.append(construire_enregistrement(
            commune, pylones_par_commune.loc[code],
            populations.loc[code] if code in populations.index else None,
            acces_electricite.loc[code] if code in acces_electricite.index else None,
            couvertures_par_commune.get(code)))

    dossier = config.DOSSIER_COMPLEMENTAIRES_JSON
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / NOM_DU_FICHIER).write_text(json.dumps(enregistrements, ensure_ascii=False, indent=1), encoding="utf-8")

    return len(enregistrements), len(communes) - len(enregistrements)


if __name__ == "__main__":
    argparse.ArgumentParser(description="Génère donnees/complementaires/communes_infos.json depuis les CSV nettoyés").parse_args()
    nombre_ecrites, nombre_sans_coordonnees = generer_fichier_complementaire()
    print(f"{nombre_ecrites} communes écrites ; {nombre_sans_coordonnees} communes ignorées (aucun pylône, donc aucune coordonnée)")
