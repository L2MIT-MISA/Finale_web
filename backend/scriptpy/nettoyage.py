from __future__ import annotations

import argparse
import json
import logging
import re
from collections import Counter
from pathlib import Path

import pandas as pd

import config
from outils import (convertir_en_booleen, convertir_en_decimal, convertir_en_entier, corriger_coordonnees,
                    est_vide, extraire_numero_final, normaliser_code, normaliser_nom, normaliser_nom_colonne,
                    normaliser_texte_libre, trouver_meilleur_rapprochement)

journal = logging.getLogger("nettoyage")

# ------------------------------------------------------------------ Motifs des colonnes par feuille
# Format : nom_canonique -> expression régulière appliquée au titre normalisé (normaliser_nom_colonne).
MOTIFS_COLONNES_RALE = {
    "codereg": r"^CODE?REG$", "region": r"^REGION$", "codedist": r"^CODE?DIST$", "district": r"^DISTRICT$",
    "codecom": r"^CODE?COM$", "commune": r"^COMMUNE$", "codefkt": r"^CODE?FKT$", "fokontany": r"^FOKONTANY$",
    "codecv": r"^CODE?CV$", "cv": r"^CV$", "codebv": r"^CODEBV$", "bv": r"^BUREAUDEVOTE$",
    "electeurs": r"^NOMBRESELECTEURS$",
}
MOTIFS_COLONNES_DESSERTE = {
    "coder": r"^CODER$", "regions": r"^REGIONS$", "coded": r"^CODED$", "districts": r"^DISTRICTS$",
    "type_com": r"^TYPECOM$", "codec": r"^CODEC$", "communes": r"^COMMUNES$",
}
MOTIF_COLONNE_TECHNOLOGIE = r"^([2-5]G)([A-Z])(\d{4})$"   # ex. 2GT2023 = 2G, opérateur T, année 2023
MOTIF_COLONNE_CODE_COUVERTURE = r"^COUV([A-Z])$"           # ex. COUVT   = code de couverture brut de T
MOTIFS_COLONNES_INFRA = {
    "op": r"^OP$", "codecom": r"^CODECOMDSI$", "nomsite": r"^NOMSITE$", "codesite": r"^CODESITE$",
    "techno_brute": r"^TECHNOLOGIE", "t2g": r"^2G$", "t3g": r"^3G$", "t4g": r"^4G$", "t5g": r"^5G$",
    "autres": r"^AUTRES$", "profil": r"^TECHNO$", "typesite": r"^TYPESITE$", "energie": r"^SOURCEENERGIE$",
    "prop": r"^PROPSITE$", "mutualisation": r"^MUTUALISATION$", "colocation": r"^COLOCATION$",
    "longitude": r"^LONGITUDE$", "latitude": r"^LATITUDE$", "hauteur": r"^HAUTEUR",
    "annee": r"^ANNEEDEMISEENSERVICE$", "nouveau": r"^NOUVEAUSITE2023$",
}
MOTIFS_COLONNES_POPULATION = {
    "codedist": r"^CODEDIST$", "district": r"^DISTRICT$", "commune": r"^COMMUNE$", "fokontany": r"^FOKONTANY$",
    "nbfkt": r"^NBFKT$", "menages": r"^MENAGES$", "population": r"^POPULATION$",
}
POSITIONS_POPULATION_SANS_TITRE = {2: "codecom", 9: "milieu"}   # colonnes sans titre dans l'Excel
MOTIFS_COLONNES_ELECTRICITE = {
    "codereg": r"^CODE?REG$", "coddist": r"^CODE?DIST$", "codcom": r"^CODE?COM$",
    "commune": r"^COMMUNE(ARRONDISSEMENT)?$", "existence": r"^EXISTENCEDELELECTRICITE",
    "nb_fkt": r"^NOMBRETOTALDEFOKONTANY", "nb_fkt_acces": r"^NOMBREDEFOKONTANYAYANT",
    "taux_couv": r"^TAUXDECOUVERTUREENELECTRICITE", "taux_acces": r"^TAUXDACCESDESMENAGES",
}
MOTIFS_COLONNES_FDTIC = {
    "codreg": r"^CODE?REG$", "coddist": r"^CODE?DIST$", "codcom": r"^CODE?COM$", "name": r"^NAME$",
    "latitude": r"^LATITUDE$", "longitude": r"^LONGITUDE$", "lot": r"^LOT$",
}
MOTIFS_COLONNES_POPULATION_PAR_ZONE = {
    "codereg": r"^CODE?REG$", "code": r"^CODE$", "nom": r"^REGIONSDISTRICTS$",
    "population_totale": r"^EFFECTIFPOPULATION$", "proportion_pct": r"^PROPORTIONDELAPOPULATION",
    "population_rurale": r"^POPULATIONRURALE$", "pct_rurale": r"^PCTPOPULATIONRURALE$",
    "population_urbaine": r"^POPULATIONURBAINE$", "pct_urbaine": r"^PCTPOPULATIONURBAINE$",
    "hommes": r"^HOMMES$", "pct_hommes": r"^PCTHOMMES$", "femmes": r"^FEMMES$", "pct_femmes": r"^PCTFEMMES$",
}
# Un code enfant doit commencer par le code parent : (code_enfant, code_parent, longueur_du_code_parent)
HIERARCHIE_DES_CODES = [("codedist", "codereg", 2), ("codecom", "codedist", 4), ("codefkt", "codecom", 6),
                        ("codecv", "codefkt", 8), ("codebv", "codecv", 10)]
MOTIF_LIGNE_DE_TOTAL = r"^\s*(total|source|note)\b"


class RapportNettoyage:

    def __init__(self):
        self.anomalies: dict[tuple[str, str], dict] = {}
        self.lignes_en_quarantaine: dict[str, list[pd.DataFrame]] = {}
        self.statistiques: dict[str, int] = {}

    def signaler_anomalie(self, nom_table: str, motif: str, nombre: int = 1, exemple=None):
        if nombre <= 0:
            return
        anomalie = self.anomalies.setdefault(
            (nom_table, motif), {"table": nom_table, "motif": motif, "nombre": 0, "exemple": exemple})
        anomalie["nombre"] += nombre

    def mettre_en_quarantaine(self, nom_table: str, lignes: pd.DataFrame, motif: str):
        if len(lignes) == 0:
            return
        lignes_marquees = lignes.copy()
        lignes_marquees["motif"] = motif
        self.lignes_en_quarantaine.setdefault(nom_table, []).append(lignes_marquees)
        premiere_ligne_excel = lignes_marquees.iloc[0].get("ligne_excel", "")
        self.signaler_anomalie(nom_table, f"quarantaine : {motif}", len(lignes_marquees),
                               f"ligne Excel {premiere_ligne_excel}")


# ------------------------------------------------------------------------------ Lecture dynamique
def trouver_nom_feuille(classeur: pd.ExcelFile, nom_feuille: str) -> str:
    nom_cherche = normaliser_nom_colonne(nom_feuille)

    for nom_existant in classeur.sheet_names:
        if normaliser_nom_colonne(nom_existant) == nom_cherche:
            return nom_existant
    raise KeyError(f"Feuille introuvable : {nom_feuille!r}. Feuilles présentes : {classeur.sheet_names}")


def lire_feuille_excel(classeur, nom_feuille, motifs_colonnes, positions_sans_titre=None,
                       motifs_colonnes_dynamiques=(), nb_lignes_scannees=30) -> pd.DataFrame:
    nom_reel = trouver_nom_feuille(classeur, nom_feuille)
    contenu_brut = classeur.parse(nom_reel, header=None, dtype=str)
    # La ligne de titres est celle qui reconnaît le plus de colonnes attendues
    motifs = {nom_canonique: re.compile(motif) for nom_canonique, motif in motifs_colonnes.items()}

    meilleur_essai = {"numero_ligne": -1, "correspondance": {}, "titres": []}

    for numero_ligne in range(min(nb_lignes_scannees, len(contenu_brut))):
        titres = [normaliser_nom_colonne(cellule) if isinstance(cellule, str) else ""
                  for cellule in contenu_brut.iloc[numero_ligne].tolist()]
        correspondance, positions_prises = {}, set()

        for nom_canonique, motif in motifs.items():
            for position, titre in enumerate(titres):
                if titre and position not in positions_prises and motif.match(titre):
                    correspondance[nom_canonique] = position
                    positions_prises.add(position)
                    break

        if len(correspondance) > len(meilleur_essai["correspondance"]):
            meilleur_essai = {"numero_ligne": numero_ligne, "correspondance": correspondance, "titres": titres}

    correspondance = meilleur_essai["correspondance"]

    if len(correspondance) < 2:
        raise ValueError(f"Titres introuvables dans la feuille {nom_reel!r} "
                         f"(colonnes reconnues : {len(correspondance)})")
    nb_colonnes_reconnues = len(correspondance)
    positions_prises = set(correspondance.values())

    for position, titre in enumerate(meilleur_essai["titres"]):      # colonnes découvertes par motif (ex. années)
        if titre and position not in positions_prises and any(re.match(motif, titre) for motif in motifs_colonnes_dynamiques):
            correspondance[titre] = position
            positions_prises.add(position)

    for position, nom_canonique in (positions_sans_titre or {}).items():
        correspondance.setdefault(nom_canonique, position)

    colonnes_manquantes = [nom for nom in motifs_colonnes if nom not in correspondance]

    if colonnes_manquantes:
        journal.warning("%s : colonnes non trouvées %s", nom_reel, colonnes_manquantes)
    lignes_de_donnees = contenu_brut.iloc[meilleur_essai["numero_ligne"] + 1:]
    tableau = pd.DataFrame({nom: lignes_de_donnees.iloc[:, position].values for nom, position in correspondance.items()},
                           index=lignes_de_donnees.index)

    for nom in colonnes_manquantes:
        tableau[nom] = None
    tableau["ligne_excel"] = tableau.index + 1
    colonnes_de_donnees = [nom for nom in tableau.columns if nom != "ligne_excel"]
    tableau = tableau.dropna(how="all", subset=colonnes_de_donnees).reset_index(drop=True)
    journal.info("%-24s titres en ligne %d, %d lignes, %d colonnes reconnues", nom_reel,
                 meilleur_essai["numero_ligne"] + 1, len(tableau), nb_colonnes_reconnues)

    return tableau


def nettoyer_texte_colonne(colonne: pd.Series) -> pd.Series:
    return colonne.map(lambda valeur: None if est_vide(valeur) else re.sub(r"\s+", " ", str(valeur)).strip()
                       ).astype("object")


def reperer_lignes_de_total(tableau: pd.DataFrame, colonnes_a_examiner) -> pd.Series:
    lignes_de_total = pd.Series(False, index=tableau.index)

    for colonne in colonnes_a_examiner:
        if colonne in tableau:
            lignes_de_total |= tableau[colonne].astype("string").str.match(MOTIF_LIGNE_DE_TOTAL, case=False, na=False)

    return lignes_de_total


def ajouter_nom_normalise(tableau: pd.DataFrame, colonne_nom: str = "nom") -> pd.DataFrame:
    tableau = tableau.copy()
    tableau["nom_norm"] = tableau[colonne_nom].map(normaliser_nom)

    return tableau


# ------------------------------------------------------------------------------ Une fonction par feuille
def nettoyer_referentiel_rale(classeur, rapport) -> dict[str, pd.DataFrame]:
    lignes = lire_feuille_excel(classeur, "Rale 2024", MOTIFS_COLONNES_RALE)

    for colonne_code in ("codereg", "codedist", "codecom", "codefkt", "codecv", "codebv"):
        lignes[colonne_code] = lignes[colonne_code].map(normaliser_code)

    for colonne_nom in ("region", "district", "commune", "fokontany", "cv", "bv"):
        lignes[colonne_nom] = nettoyer_texte_colonne(lignes[colonne_nom])
    lignes["electeurs"] = lignes["electeurs"].map(convertir_en_entier).astype("Int64")

    lignes_valides = lignes["codebv"].notna()

    for code_enfant, code_parent, longueur_code_parent in HIERARCHIE_DES_CODES:
        lignes_valides &= lignes[code_enfant].str[:longueur_code_parent] == lignes[code_parent]
    rapport.mettre_en_quarantaine("rale", lignes[~lignes_valides], "code manquant ou hiérarchie incohérente")
    lignes = lignes[lignes_valides].copy()

    def extraire_niveau(colonne_code, colonne_nom, colonne_parent=None, colonnes_en_plus=()):
        colonnes = [colonne_code, colonne_nom] + ([colonne_parent] if colonne_parent else []) + list(colonnes_en_plus)
        nb_codes_a_noms_multiples = int((lignes.groupby(colonne_code)[colonne_nom].nunique() > 1).sum())
        rapport.signaler_anomalie("rale", f"{colonne_code} : plusieurs noms pour un même code (premier gardé)",
                                  nb_codes_a_noms_multiples)

        return lignes[colonnes].drop_duplicates(colonne_code).reset_index(drop=True)

    tables = {}
    tables["region"] = ajouter_nom_normalise(extraire_niveau("codereg", "region").rename(columns={"region": "nom"}))
    tables["district"] = ajouter_nom_normalise(
        extraire_niveau("codedist", "district", "codereg").rename(columns={"district": "nom"}))
    tables["commune"] = ajouter_nom_normalise(
        extraire_niveau("codecom", "commune", "codedist").rename(columns={"commune": "nom"}))
    tables["fokontany"] = ajouter_nom_normalise(
        extraire_niveau("codefkt", "fokontany", "codecom").rename(columns={"codefkt": "code_fokontany", "fokontany": "nom"}))
    centres_de_vote = extraire_niveau("codecv", "cv", "codecom", colonnes_en_plus=("codefkt",))
    tables["centre_vote"] = centres_de_vote.rename(
        columns={"codecv": "code_cv", "cv": "nom", "codefkt": "code_fokontany"})
    bureaux_de_vote = lignes[["codebv", "codecv", "bv", "electeurs"]].drop_duplicates("codebv")
    tables["bureau_vote"] = bureaux_de_vote.rename(
        columns={"codebv": "code_bv", "codecv": "code_cv", "bv": "nom", "electeurs": "nombre_electeurs_2024"}
    ).reset_index(drop=True)
    rapport.statistiques["electeurs_total_2024"] = int(lignes["electeurs"].sum())

    return tables


def formater_code_couverture(valeur) -> str | None:
    code = normaliser_code(valeur)

    return code.zfill(4) if code else None


def nettoyer_desserte(classeur, rapport, codes_communes_rale):
    lignes = lire_feuille_excel(classeur, "Desserte_des_Communes", MOTIFS_COLONNES_DESSERTE,
                                motifs_colonnes_dynamiques=(MOTIF_COLONNE_TECHNOLOGIE, MOTIF_COLONNE_CODE_COUVERTURE))
    lignes = lignes[~reperer_lignes_de_total(lignes, ["communes", "districts"])].copy()
    lignes["codecom"] = lignes["codec"].map(normaliser_code)
    rapport.mettre_en_quarantaine("desserte", lignes[lignes["codecom"].isna()], "commune sans code")
    lignes = lignes[lignes["codecom"].notna()]
    communes_inconnues = ~lignes["codecom"].isin(codes_communes_rale)
    rapport.mettre_en_quarantaine("desserte", lignes[communes_inconnues], "commune absente du référentiel Rale")
    lignes = lignes[~communes_inconnues].copy()
    lignes["milieu_source"] = lignes["type_com"].map(normaliser_nom)
    milieu_des_communes = lignes[["codecom"]].assign(
        milieu=lignes["milieu_source"].map({"RURALE": "RURAL", "URBAINE": "URBAIN"}))

    colonnes_technologie: dict[tuple[str, str], dict[str, str]] = {}   # (lettre, année) -> {"2G": colonne, ...}
    colonnes_code_couverture: dict[str, str] = {}                        # lettre -> colonne

    for nom_colonne in lignes.columns:
        if correspondance := re.match(MOTIF_COLONNE_TECHNOLOGIE, nom_colonne):
            technologie, lettre, annee = correspondance.groups()
            colonnes_technologie.setdefault((lettre, annee), {})[technologie] = nom_colonne
        elif correspondance := re.match(MOTIF_COLONNE_CODE_COUVERTURE, nom_colonne):
            colonnes_code_couverture[correspondance.group(1)] = nom_colonne

    if not colonnes_technologie:
        rapport.signaler_anomalie("desserte", "aucune colonne technologie/opérateur/année reconnue")
        return milieu_des_communes, pd.DataFrame()

    annee_la_plus_recente = max(annee for _, annee in colonnes_technologie)
    tableaux_par_operateur_et_annee = []

    for (lettre, annee), colonnes in sorted(colonnes_technologie.items()):
        operateur = config.OPERATEURS_PAR_LETTRE.get(lettre)

        if operateur is None:
            rapport.signaler_anomalie("desserte", f"lettre d'opérateur inconnue : {lettre}")
            continue
        codes_couverture = None

        if lettre in colonnes_code_couverture and annee == annee_la_plus_recente:
            codes_couverture = lignes[colonnes_code_couverture[lettre]].map(formater_code_couverture).values
        tableaux_par_operateur_et_annee.append(pd.DataFrame({
            "codecom": lignes["codecom"].values, "code_operateur": operateur, "annee_mesure": int(annee),
            "type_milieu": lignes["milieu_source"].map({"RURALE": "RURALE", "URBAINE": "URBAINE"}).values,
            "tech_2g": lignes[colonnes["2G"]].map(convertir_en_booleen).values if "2G" in colonnes else None,
            "tech_3g": lignes[colonnes["3G"]].map(convertir_en_booleen).values if "3G" in colonnes else None,
            "tech_4g": lignes[colonnes["4G"]].map(convertir_en_booleen).values if "4G" in colonnes else None,
            "code_couverture_brut": codes_couverture}))
    couverture = pd.concat(tableaux_par_operateur_et_annee, ignore_index=True)

    for colonne_technologie in ("tech_2g", "tech_3g", "tech_4g"):
        couverture[colonne_technologie] = couverture[colonne_technologie].astype("boolean")

    return milieu_des_communes, couverture


def nettoyer_pylones(classeur, rapport, codes_communes_rale) -> pd.DataFrame:
    lignes = lire_feuille_excel(classeur, "Infra_2022", MOTIFS_COLONNES_INFRA)
    lignes["code_operateur"] = lignes["op"].map(normaliser_texte_libre)
    operateurs_inconnus = ~lignes["code_operateur"].isin(config.OPERATEURS_VALIDES)
    rapport.mettre_en_quarantaine("pylone", lignes[operateurs_inconnus], "opérateur inconnu")
    lignes = lignes[~operateurs_inconnus].copy()
    lignes["codecom"] = lignes["codecom"].map(normaliser_code)
    communes_inconnues = ~lignes["codecom"].isin(codes_communes_rale)
    rapport.mettre_en_quarantaine("pylone", lignes[communes_inconnues], "commune absente du référentiel Rale")
    lignes = lignes[~communes_inconnues].copy()

    rapport.statistiques["pylone_virgules_decimales_corrigees"] = int(
        lignes["latitude"].astype(str).str.contains(",").sum())
    coordonnees_corrigees = [corriger_coordonnees(latitude, longitude)
                             for latitude, longitude in zip(lignes["latitude"], lignes["longitude"])]
    lignes["latitude"] = [latitude for latitude, _, _ in coordonnees_corrigees]
    lignes["longitude"] = [longitude for _, longitude, _ in coordonnees_corrigees]

    for etat, nombre in Counter(etat for _, _, etat in coordonnees_corrigees).items():
        if etat != "ok":
            rapport.signaler_anomalie("pylone", f"coordonnées : {etat}", nombre)

    lignes["code_site"] = nettoyer_texte_colonne(lignes["codesite"])
    sans_code = lignes["code_site"].isna()

    if sans_code.any():
        lignes.loc[sans_code, "code_site"] = [
            f"{operateur}-SANSCODE-{numero_ligne}" for operateur, numero_ligne
            in zip(lignes.loc[sans_code, "code_operateur"], lignes.loc[sans_code, "ligne_excel"])]
        rapport.signaler_anomalie("pylone", "code_site absent ou '-' : code de remplacement généré", int(sans_code.sum()))
    doublons = lignes.duplicated(["code_operateur", "code_site"], keep="first")
    rapport.mettre_en_quarantaine("pylone", lignes[doublons], "doublon (code_operateur, code_site)")
    lignes = lignes[~doublons].copy()

    pylones = pd.DataFrame({
        "code_operateur": lignes["code_operateur"], "code_site": lignes["code_site"],
        "nom_site": nettoyer_texte_colonne(lignes["nomsite"]), "codecom": lignes["codecom"],
        "technologie_brute": nettoyer_texte_colonne(lignes["techno_brute"]),
        "profil_technologique": lignes["profil"].map(normaliser_texte_libre),
        "tech_2g": lignes["t2g"].notna(), "tech_3g": lignes["t3g"].notna(),
        "tech_4g": lignes["t4g"].notna(), "tech_5g": lignes["t5g"].notna(),
        "autres_equipements": nettoyer_texte_colonne(lignes["autres"]),
        "type_site": lignes["typesite"].map(normaliser_texte_libre),
        "source_energie": lignes["energie"].map(normaliser_texte_libre),
        "proprietaire": lignes["prop"].map(normaliser_texte_libre),
        "mutualisation": lignes["mutualisation"].map(normaliser_texte_libre),
        "colocation": lignes["colocation"].notna(),
        "colocation_operateur": lignes["colocation"].map(normaliser_texte_libre),
        "nouveau_site_2023": lignes["nouveau"].map(convertir_en_booleen).astype("boolean"),
        "hauteur_m": lignes["hauteur"].map(convertir_en_decimal),
        "annee_service": lignes["annee"].map(convertir_en_entier).map(
            lambda annee: annee if annee and 1990 <= annee <= 2030 else None).astype("Int64"),
        "latitude": lignes["latitude"], "longitude": lignes["longitude"],
        "audit_source_row_id": lignes["ligne_excel"]})

    return pylones.reset_index(drop=True)


def nettoyer_sites_fdtic(classeur, rapport, codes_communes_rale) -> pd.DataFrame:
    lignes = lire_feuille_excel(classeur, "SitFdtic", MOTIFS_COLONNES_FDTIC)
    lignes["codecom"] = lignes["codcom"].map(normaliser_code)
    communes_inconnues = ~lignes["codecom"].isin(codes_communes_rale)
    rapport.mettre_en_quarantaine("site_fdtic", lignes[communes_inconnues], "commune absente du référentiel Rale")
    lignes = lignes[~communes_inconnues].copy()
    coordonnees_corrigees = [corriger_coordonnees(latitude, longitude)
                             for latitude, longitude in zip(lignes["latitude"], lignes["longitude"])]

    for etat, nombre in Counter(etat for _, _, etat in coordonnees_corrigees).items():
        if etat != "ok":
            rapport.signaler_anomalie("site_fdtic", f"coordonnées : {etat}", nombre)

    return pd.DataFrame({
        "nom": nettoyer_texte_colonne(lignes["name"]), "lot": nettoyer_texte_colonne(lignes["lot"]),
        "codereg_brut": lignes["codreg"].map(convertir_en_entier).astype("Int64"),
        "codedist_brut": lignes["coddist"].map(convertir_en_entier).astype("Int64"),
        "codecom": lignes["codecom"],
        "latitude": [latitude for latitude, _, _ in coordonnees_corrigees],
        "longitude": [longitude for _, longitude, _ in coordonnees_corrigees]}).reset_index(drop=True)


def nettoyer_acces_electricite(classeur, rapport, codes_communes_rale) -> pd.DataFrame:
    lignes = lire_feuille_excel(classeur, "AccèsEelectricité", MOTIFS_COLONNES_ELECTRICITE)
    lignes = lignes[~reperer_lignes_de_total(lignes, ["codereg", "commune"])].copy()
    lignes["codecom"] = lignes["codcom"].map(normaliser_code)
    rapport.mettre_en_quarantaine("electricite", lignes[lignes["codecom"].isna()], "commune sans code")
    lignes = lignes[lignes["codecom"].notna()]
    codes_en_double = lignes.duplicated("codecom", keep=False)   # on garde AUCUN exemplaire : à trancher par un humain
    rapport.mettre_en_quarantaine("electricite", lignes[codes_en_double], "code commune en double")
    lignes = lignes[~codes_en_double]
    communes_inconnues = ~lignes["codecom"].isin(codes_communes_rale)
    rapport.mettre_en_quarantaine("electricite", lignes[communes_inconnues], "commune absente du référentiel Rale")
    lignes = lignes[~communes_inconnues]

    return pd.DataFrame({
        "codecom": lignes["codecom"],
        "existence_electricite": lignes["existence"].map(convertir_en_booleen).astype("boolean"),
        "nb_fokontany_total": lignes["nb_fkt"].map(convertir_en_entier).astype("Int64"),
        "nb_fokontany_avec_acces": lignes["nb_fkt_acces"].map(convertir_en_entier).astype("Int64"),
        "taux_couverture_pct": lignes["taux_couv"].map(convertir_en_decimal),
        "taux_acces_menages_pct": lignes["taux_acces"].map(convertir_en_decimal),
    }).reset_index(drop=True)


def nettoyer_population_fokontany(classeur, rapport, fokontany_rale, codes_communes_rale) -> pd.DataFrame:
    lignes = lire_feuille_excel(classeur, "Population", MOTIFS_COLONNES_POPULATION,
                                positions_sans_titre=POSITIONS_POPULATION_SANS_TITRE)
    lignes = lignes[~reperer_lignes_de_total(lignes, ["commune", "district"])].copy()
    lignes["codecom"] = lignes["codecom"].map(normaliser_code)
    lignes["nom_brut"] = nettoyer_texte_colonne(lignes["fokontany"])
    rapport.mettre_en_quarantaine("population", lignes[lignes["codecom"].isna() | lignes["nom_brut"].isna()],
                                  "code commune ou nom de fokontany manquant")
    lignes = lignes[lignes["codecom"].notna() & lignes["nom_brut"].notna()].copy()
    communes_inconnues = ~lignes["codecom"].isin(codes_communes_rale)
    rapport.mettre_en_quarantaine("population", lignes[communes_inconnues], "commune absente du référentiel Rale")
    lignes = lignes[~communes_inconnues].copy()
    lignes["nom_norm"] = lignes["nom_brut"].map(normaliser_nom)

    # Le code fokontany est absent de cette feuille : on le retrouve par le nom (exact, puis approché, sinon laissé vide)
    codes_fokontany_par_commune_et_nom = fokontany_rale.groupby(["codecom", "nom_norm"])["code_fokontany"].apply(list).to_dict()
    noms_fokontany_par_commune = fokontany_rale.groupby("codecom")[["code_fokontany", "nom_norm"]].apply(
        lambda groupe: dict(zip(groupe["code_fokontany"], groupe["nom_norm"]))).to_dict()
    nombre_de_lignes_par_commune_et_nom = lignes.groupby(["codecom", "nom_norm"]).size().to_dict()

    nombre_de_lignes = len(lignes)
    codes_trouves = [None] * nombre_de_lignes
    scores = [None] * nombre_de_lignes
    methodes = [""] * nombre_de_lignes
    codes_deja_attribues = set()
    couples_commune_nom = list(lignes[["codecom", "nom_norm"]].itertuples(index=False, name=None))

    for position, (code_commune, nom_normalise) in enumerate(couples_commune_nom):          # temps 1 : exact
        codes_candidats = codes_fokontany_par_commune_et_nom.get((code_commune, nom_normalise), [])

        if len(codes_candidats) == 1 and nombre_de_lignes_par_commune_et_nom[(code_commune, nom_normalise)] == 1:
            codes_trouves[position], scores[position], methodes[position] = codes_candidats[0], 1.0, "exact"
            codes_deja_attribues.add(codes_candidats[0])
        elif codes_candidats:
            methodes[position] = "ambigu"          # même nom plusieurs fois : on ne devine pas

    for position, (code_commune, nom_normalise) in enumerate(couples_commune_nom):          # temps 2 : approché
        if methodes[position]:
            continue
        candidats_libres = {code: nom for code, nom in noms_fokontany_par_commune.get(code_commune, {}).items()
                            if code not in codes_deja_attribues
                            and extraire_numero_final(nom) == extraire_numero_final(nom_normalise)}   # « X I » != « X II » != « X »
        code_trouve, score = trouver_meilleur_rapprochement(nom_normalise, candidats_libres, seuil=0.90, marge=0.03)

        if code_trouve:
            codes_trouves[position], scores[position], methodes[position] = code_trouve, round(score, 3), "approche"
            codes_deja_attribues.add(code_trouve)
        else:
            methodes[position] = "non_rapproche"

    for methode, nombre in Counter(methodes).items():
        rapport.statistiques[f"population_rapprochement_{methode}"] = nombre

    return pd.DataFrame({
        "code_fokontany": pd.array(codes_trouves, dtype="object"), "codecom_brut": lignes["codecom"].values,
        "nom_fokontany_brut": lignes["nom_brut"].values,
        "menages": lignes["menages"].map(convertir_en_entier).astype("Int64").values,
        "population": lignes["population"].map(convertir_en_entier).astype("Int64").values,
        "milieu": lignes["milieu"].map(normaliser_nom).map({"URBAIN": "URBAIN", "RURAL": "RURAL"}).values,
        "score_rapprochement": scores, "methode_rapprochement": methodes,
        "ligne_excel": lignes["ligne_excel"].values})


def nettoyer_population_regions_districts(classeur, rapport, noms_regions_rale: dict, noms_districts_rale: dict,
                                          equivalences_manuelles: dict):
    lignes = lire_feuille_excel(classeur, "pop_dist", MOTIFS_COLONNES_POPULATION_PAR_ZONE)
    lignes["code"] = lignes["code"].map(normaliser_code)
    lignes = lignes[lignes["code"].notna()].copy()                       # supprime « Total général » et notes
    colonnes_chiffrees = ["population_totale", "proportion_pct", "population_rurale", "pct_rurale",
                          "population_urbaine", "pct_urbaine", "hommes", "pct_hommes", "femmes", "pct_femmes"]

    for colonne in colonnes_chiffrees:
        lignes[colonne] = lignes[colonne].map(convertir_en_decimal)

    for colonne_effectif in ("population_totale", "population_rurale", "population_urbaine", "hommes", "femmes"):
        lignes[colonne_effectif] = lignes[colonne_effectif].round().astype("Int64")

    equivalences, lignes_acceptees = [], {"region": [], "district": []}

    for ligne in lignes.itertuples():
        niveau = {2: "region", 4: "district"}.get(len(ligne.code))

        if niveau is None:
            rapport.mettre_en_quarantaine("pop_dist", lignes.loc[[ligne.Index]], "code ni région (2) ni district (4)")
            continue
        # Le nom fait foi, pas le code : 3501 désigne Ifanadiana dans cette feuille mais Ikongo dans Rale
        noms_du_referentiel = noms_regions_rale if niveau == "region" else noms_districts_rale

        if (niveau, ligne.code) in equivalences_manuelles:               # décision humaine (equivalences_manuelles.csv)
            code_rale, score, methode = equivalences_manuelles[(niveau, ligne.code)], 1.0, "manuel"
        else:
            code_rale, score = trouver_meilleur_rapprochement(ligne.nom, noms_du_referentiel, seuil=0.90)
            methode = "" if code_rale is None else ("code" if code_rale == ligne.code else "nom")
        equivalences.append({"niveau": niveau, "code_source": ligne.code, "nom_source": ligne.nom,
                             "code_rale": code_rale, "score": round(score, 3), "methode": methode})

        if code_rale is None:
            rapport.mettre_en_quarantaine("pop_dist", lignes.loc[[ligne.Index]],
                                          f"{niveau} non rapproché d'un nom du référentiel")
            continue
        valeurs = {colonne: getattr(ligne, colonne) for colonne in colonnes_chiffrees}
        valeurs["codereg" if niveau == "region" else "codedist"] = code_rale
        lignes_acceptees[niveau].append(valeurs)

    tableau_equivalences = pd.DataFrame(equivalences)

    for niveau in ("region", "district"):
        nombre_remappes = int(((tableau_equivalences["niveau"] == niveau)
                               & (tableau_equivalences["methode"] == "nom")).sum()) if len(tableau_equivalences) else 0
        rapport.signaler_anomalie("pop_dist", f"{niveau} dont le code source diffère du code Rale (remappé par nom)",
                                  nombre_remappes)

    return pd.DataFrame(lignes_acceptees["region"]), pd.DataFrame(lignes_acceptees["district"]), tableau_equivalences


# ------------------------------------------------------------------------------ Programme principal
def ecrire_csv(tableau: pd.DataFrame, dossier_sortie: Path, nom_table: str, nombres_de_lignes: dict):
    tableau.to_csv(dossier_sortie / f"{nom_table}.csv", index=False, encoding="utf-8")
    nombres_de_lignes[nom_table] = len(tableau)


def charger_equivalences_manuelles() -> dict:
    chemin = config.DOSSIER_DONNEES / "equivalences_manuelles.csv"

    if not chemin.exists():
        return {}
    equivalences = pd.read_csv(chemin, dtype=str)
    journal.info("%d équivalences manuelles chargées", len(equivalences))

    return {(ligne.niveau, ligne.code_source): ligne.code_rale for ligne in equivalences.itertuples()}


def executer_nettoyage(chemin_excel: Path, dossier_sortie: Path) -> dict:
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    classeur = pd.ExcelFile(chemin_excel, engine="openpyxl")
    rapport = RapportNettoyage()
    nombres_de_lignes: dict[str, int] = {}

    referentiel = nettoyer_referentiel_rale(classeur, rapport)
    codes_communes_rale = set(referentiel["commune"]["codecom"])
    milieu_des_communes, couverture = nettoyer_desserte(classeur, rapport, codes_communes_rale)
    referentiel["commune"] = referentiel["commune"].merge(
        milieu_des_communes.drop_duplicates("codecom"), on="codecom", how="left")

    for nom_table in ("region", "district", "commune", "fokontany", "centre_vote", "bureau_vote"):
        ecrire_csv(referentiel[nom_table], dossier_sortie, nom_table, nombres_de_lignes)
    ecrire_csv(couverture, dossier_sortie, "couverture_operateur_commune", nombres_de_lignes)
    ecrire_csv(nettoyer_pylones(classeur, rapport, codes_communes_rale), dossier_sortie, "pylone", nombres_de_lignes)
    ecrire_csv(nettoyer_sites_fdtic(classeur, rapport, codes_communes_rale), dossier_sortie, "site_fdtic", nombres_de_lignes)
    ecrire_csv(nettoyer_acces_electricite(classeur, rapport, codes_communes_rale), dossier_sortie,
               "acces_electricite_commune", nombres_de_lignes)
    population_fokontany = nettoyer_population_fokontany(classeur, rapport, referentiel["fokontany"], codes_communes_rale)
    ecrire_csv(population_fokontany, dossier_sortie, "population_fokontany", nombres_de_lignes)

    noms_regions = dict(zip(referentiel["region"]["codereg"], referentiel["region"]["nom"]))
    noms_districts = dict(zip(referentiel["district"]["codedist"], referentiel["district"]["nom"]))
    population_regions, population_districts, equivalences = nettoyer_population_regions_districts(
        classeur, rapport, noms_regions, noms_districts, charger_equivalences_manuelles())
    ecrire_csv(population_regions, dossier_sortie, "population_region", nombres_de_lignes)
    ecrire_csv(population_districts, dossier_sortie, "population_district", nombres_de_lignes)
    ecrire_csv(equivalences, dossier_sortie, "equivalence_district", nombres_de_lignes)
    rapport.statistiques["population_totale_population_fokontany"] = int(population_fokontany["population"].sum())
    rapport.statistiques["population_totale_pop_dist"] = (
        int(population_regions["population_totale"].sum()) if len(population_regions) else 0)

    for nom_table, morceaux in rapport.lignes_en_quarantaine.items():
        ecrire_csv(pd.concat(morceaux, ignore_index=True), dossier_sortie, f"quarantaine_{nom_table}", nombres_de_lignes)
    contenu_rapport = {"tables": nombres_de_lignes, "statistiques": rapport.statistiques,
                       "anomalies": sorted(rapport.anomalies.values(), key=lambda anomalie: -anomalie["nombre"])}
    (dossier_sortie / "rapport.json").write_text(
        json.dumps(contenu_rapport, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    return contenu_rapport


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    lecteur_arguments = argparse.ArgumentParser(description="Nettoyage dynamique de l'Excel Madagascar")
    lecteur_arguments.add_argument("--excel", type=Path, default=config.CHEMIN_EXCEL)
    lecteur_arguments.add_argument("--sortie", type=Path, default=config.DOSSIER_CSV_PROPRES)
    arguments = lecteur_arguments.parse_args()
    contenu = executer_nettoyage(arguments.excel, arguments.sortie)
    print("\n=== TABLES ÉCRITES ===")

    for nom_table, nombre in contenu["tables"].items():
        print(f"  {nom_table:36s} {nombre:>7d} lignes")
    print("\n=== STATISTIQUES ===")

    for nom_statistique, valeur in contenu["statistiques"].items():
        print(f"  {nom_statistique}: {valeur}")
    print("\n=== ANOMALIES (détail dans rapport.json) ===")

    for anomalie in contenu["anomalies"]:
        print(f"  [{anomalie['table']}] {anomalie['motif']} : {anomalie['nombre']}")
