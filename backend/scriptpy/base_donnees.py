from __future__ import annotations

from contextlib import contextmanager

import psycopg

import config
from modeles import FragmentConnaissance, Lieu

NIVEAUX_DU_REFERENTIEL = ("region", "district", "commune", "fokontany")
TABLES_DU_REFERENTIEL = (
    ("region", "referentiel.region", "codereg"),
    ("district", "referentiel.district", "codedist"),
    ("commune", "referentiel.commune", "codecom"),
    ("fokontany", "referentiel.fokontany", "code_fokontany"),
)
TABLES_ATTENDUES = ("referentiel.commune", "referentiel.hierarchie_complete", "infrastructure.pylone",
                    "collecte.fragment_lieu")
NOMS_COLONNES_FRAGMENT = (
    "id_fragment", "nom_lieu", "niveau_lieu", "code_lieu", "region", "district", "latitude", "longitude",
    "precision_coordonnees", "produit", "categorie", "note_google", "nombre_avis_google", "avis", "sources_citees", "texte",
    "mots_cles", "fichier_json", "source_url", "confiance",
)
COLONNES_FRAGMENT = ", ".join(NOMS_COLONNES_FRAGMENT)


class BaseIndisponible(Exception):
    pass


@contextmanager
def ouvrir_curseur():
    if not config.URL_BASE_DE_DONNEES:
        raise BaseIndisponible("variable d'environnement DATABASE_URL non définie")

    try:
        with psycopg.connect(config.URL_BASE_DE_DONNEES, connect_timeout=3) as connexion:
            with connexion.cursor() as curseur:
                yield curseur
    except psycopg.OperationalError as erreur:
        raise BaseIndisponible(str(erreur)) from erreur


def _expression_nom_normalise(colonne: str) -> str:
    return f"btrim(regexp_replace(unaccent(upper({colonne})), '[^A-Z0-9]+', ' ', 'g'))"


def _construire_sql_recherche_par_nom() -> str:
    selections = [
        f"SELECT '{niveau}' AS niveau, entite.{colonne_code}::bigint AS code, entite.nom AS nom, "
        f"similarity({_expression_nom_normalise('entite.nom')}, recherche.nom_cherche) AS similarite "
        f"FROM {table} entite CROSS JOIN unnest(%(noms)s::text[]) AS recherche(nom_cherche)"
        for niveau, table, colonne_code in TABLES_DU_REFERENTIEL]

    return ("SELECT niveau, code, nom, max(similarite) AS similarite FROM ("
            + " UNION ALL ".join(selections)
            + ") correspondances WHERE similarite >= %(seuil)s "
              "GROUP BY niveau, code, nom ORDER BY max(similarite) DESC, niveau LIMIT 8")


SQL_RECHERCHE_PAR_NOM = _construire_sql_recherche_par_nom()


def _chercher_coordonnees(curseur, niveau: str, code: int):
    """Retourne (latitude, longitude, precision) ou None : position enregistrée, sinon repli sur la commune
    (fokontany), sinon centre des pylônes et sites FDTIC de la zone."""
    table_et_colonne = {"region": ("referentiel.region", "codereg"),
                        "commune": ("referentiel.commune", "codecom"),
                        "fokontany": ("referentiel.fokontany", "code_fokontany")}.get(niveau)

    if table_et_colonne:
        table, colonne_code = table_et_colonne
        curseur.execute(f"SELECT ST_Y(geom::geometry), ST_X(geom::geometry) FROM {table} "
                        f"WHERE {colonne_code} = %s AND geom IS NOT NULL", (code,))
        position = curseur.fetchone()

        if position:
            return position[0], position[1], ("precis" if niveau == "fokontany" else "centroide")

    if niveau == "fokontany":
        coordonnees_commune = _chercher_coordonnees(curseur, "commune", code // 100)

        if coordonnees_commune:
            return coordonnees_commune[0], coordonnees_commune[1], "repli_hierarchique"

        return None

    condition_de_zone = {"region": "le_district.codereg = %s", "district": "la_commune.codedist = %s",
                         "commune": "la_commune.codecom = %s"}.get(niveau)

    if condition_de_zone is None:
        return None

    for table_des_points in ("infrastructure.pylone", "infrastructure.site_fdtic"):
        curseur.execute(f"""
            SELECT ST_Y(centre), ST_X(centre) FROM (
                SELECT ST_Centroid(ST_Collect(equipement.geom::geometry)) AS centre
                FROM {table_des_points} equipement
                JOIN referentiel.commune la_commune ON la_commune.codecom = equipement.codecom
                JOIN referentiel.district le_district ON le_district.codedist = la_commune.codedist
                WHERE equipement.geom IS NOT NULL AND {condition_de_zone}) calcul
            WHERE centre IS NOT NULL""", (code,))
        centre = curseur.fetchone()

        if centre:
            return centre[0], centre[1], "centroide"

    return None


def _chercher_noms_parents(curseur, niveau: str, code: int) -> tuple[str | None, str | None]:
    colonne_code = {"region": "codereg", "district": "codedist", "commune": "codecom", "fokontany": "codecom"}.get(niveau)

    if colonne_code is None:
        return None, None

    valeur = code // 100 if niveau == "fokontany" else code
    curseur.execute(f"SELECT region, district FROM referentiel.hierarchie_complete WHERE {colonne_code} = %s LIMIT 1",
                    (valeur,))
    ligne = curseur.fetchone()

    if ligne is None:
        return None, None

    nom_region, nom_district = ligne

    return nom_region, (None if niveau == "region" else nom_district)


def chercher_lieux_du_referentiel(noms_recherches: list[str],
                                  seuil_similarite: float = config.SEUIL_SIMILARITE_NOM_LIEU) -> list[Lieu]:
    with ouvrir_curseur() as curseur:
        curseur.execute(SQL_RECHERCHE_PAR_NOM, {"noms": noms_recherches, "seuil": seuil_similarite})
        correspondances = curseur.fetchall()
        lieux = []

        for niveau, code, nom, similarite in correspondances:
            nom_region, nom_district = _chercher_noms_parents(curseur, niveau, code)
            lieu = Lieu(nom=nom, niveau=niveau, code_officiel=str(code), region=nom_region, district=nom_district,
                        description=f"{niveau.capitalize()} du référentiel officiel.",
                        pertinence=float(similarite), confiance=float(similarite),
                        origine="referentiel", source="referentiel")
            coordonnees = _chercher_coordonnees(curseur, niveau, code)

            if coordonnees:
                lieu.definir_coordonnees(*coordonnees)

            lieux.append(lieu)

        return lieux


def trouver_coordonnees_officielles(niveau: str, code_officiel: str):
    if niveau not in NIVEAUX_DU_REFERENTIEL or not code_officiel.isdigit():
        return None

    with ouvrir_curseur() as curseur:
        return _chercher_coordonnees(curseur, niveau, int(code_officiel))


def trouver_noms_parents(niveau: str, code_officiel: str) -> tuple[str | None, str | None]:
    if niveau not in NIVEAUX_DU_REFERENTIEL or not code_officiel.isdigit():
        return None, None

    with ouvrir_curseur() as curseur:
        return _chercher_noms_parents(curseur, niveau, int(code_officiel))


def _en_nombre_decimal(valeur) -> float | None:
    return None if valeur is None else float(valeur)


def _construire_fragment(ligne) -> FragmentConnaissance:
    valeurs = dict(zip(NOMS_COLONNES_FRAGMENT, ligne))
    code_lieu = valeurs["code_lieu"]

    return FragmentConnaissance(
        nom_lieu=valeurs["nom_lieu"], niveau_lieu=valeurs["niveau_lieu"], texte=valeurs["texte"],
        fichier_json=valeurs["fichier_json"], code_lieu=None if code_lieu is None else str(code_lieu),
        region=valeurs["region"], district=valeurs["district"],
        latitude=_en_nombre_decimal(valeurs["latitude"]), longitude=_en_nombre_decimal(valeurs["longitude"]),
        precision_coordonnees=valeurs["precision_coordonnees"], produit=valeurs["produit"],
        categorie=valeurs["categorie"], note_google=_en_nombre_decimal(valeurs["note_google"]),
        nombre_avis_google=valeurs["nombre_avis_google"], avis=valeurs["avis"], sources_citees=valeurs["sources_citees"],
        mots_cles=list(valeurs["mots_cles"]), source_url=valeurs["source_url"],
        confiance=float(valeurs["confiance"]), similarite=float(ligne[-1]))


def _convertir_vecteur_en_texte(vecteur: list[float]) -> str:
    return "[" + ",".join(f"{valeur:.6f}" for valeur in vecteur) + "]"


def chercher_fragments(vecteur_requete: list[float] | None, mots_cles: list[str],
                       limite: int) -> list[FragmentConnaissance]:
    """Recherche hybride : proximité de sens (pgvector) et présence d'un mot-clé (index GIN).
    Sans vecteur, seule la recherche par mots-clés est faite."""
    similarite_sql = "1 - (vecteur <=> %(vecteur)s::vector)" if vecteur_requete is not None else "0.0"
    parametres = {"vecteur": None if vecteur_requete is None else _convertir_vecteur_en_texte(vecteur_requete),
                  "mots_cles": mots_cles, "limite": limite}
    requetes_sql = []

    if vecteur_requete is not None:
        requetes_sql.append(f"SELECT {COLONNES_FRAGMENT}, {similarite_sql} AS similarite FROM collecte.fragment_lieu "
                            f"ORDER BY vecteur <=> %(vecteur)s::vector LIMIT %(limite)s")

    if mots_cles:
        ordre_sql = f"{similarite_sql} DESC" if vecteur_requete is not None else "id_fragment"
        requetes_sql.append(f"SELECT {COLONNES_FRAGMENT}, {similarite_sql} AS similarite FROM collecte.fragment_lieu "
                            f"WHERE mots_cles && %(mots_cles)s::text[] ORDER BY {ordre_sql} LIMIT %(limite)s")

    fragments_par_identifiant: dict[int, FragmentConnaissance] = {}

    with ouvrir_curseur() as curseur:
        for requete_sql in requetes_sql:
            curseur.execute(requete_sql, parametres)

            for ligne in curseur.fetchall():
                fragments_par_identifiant.setdefault(ligne[0], _construire_fragment(ligne))

    return list(fragments_par_identifiant.values())


SQL_ENREGISTRER_FRAGMENT = """
INSERT INTO collecte.fragment_lieu
    (nom_lieu, niveau_lieu, code_lieu, region, district, latitude, longitude, precision_coordonnees,
     produit, categorie, note_google, nombre_avis_google, avis, sources_citees, texte, mots_cles, fichier_json, source_url,
     confiance, empreinte_texte, vecteur)
VALUES
    (%(nom_lieu)s, %(niveau_lieu)s, %(code_lieu)s, %(region)s, %(district)s, %(latitude)s, %(longitude)s,
     %(precision_coordonnees)s, %(produit)s, %(categorie)s, %(note_google)s, %(nombre_avis_google)s, %(avis)s, %(sources_citees)s,
     %(texte)s, %(mots_cles)s, %(fichier_json)s, %(source_url)s, %(confiance)s, %(empreinte_texte)s,
     %(vecteur)s::vector)
ON CONFLICT (fichier_json, empreinte_texte) DO NOTHING"""


def enregistrer_fragments(fragments: list[FragmentConnaissance], vecteurs: list[list[float]]) -> int:
    lignes = [{
        "nom_lieu": fragment.nom_lieu, "niveau_lieu": fragment.niveau_lieu,
        "code_lieu": int(fragment.code_lieu) if fragment.code_lieu and fragment.code_lieu.isdigit() else None,
        "region": fragment.region, "district": fragment.district,
        "latitude": fragment.latitude, "longitude": fragment.longitude,
        "precision_coordonnees": fragment.precision_coordonnees, "produit": fragment.produit,
        "categorie": fragment.categorie, "note_google": fragment.note_google,
        "nombre_avis_google": fragment.nombre_avis_google, "avis": fragment.avis,
        "sources_citees": fragment.sources_citees, "texte": fragment.texte,
        "mots_cles": fragment.mots_cles, "fichier_json": fragment.fichier_json, "source_url": fragment.source_url,
        "confiance": fragment.confiance, "empreinte_texte": fragment.calculer_empreinte(),
        "vecteur": _convertir_vecteur_en_texte(vecteur),
    } for fragment, vecteur in zip(fragments, vecteurs, strict=True)]

    with ouvrir_curseur() as curseur:
        curseur.executemany(SQL_ENREGISTRER_FRAGMENT, lignes)

    return len(lignes)


def lister_empreintes_du_fichier(nom_fichier: str) -> set[str]:
    with ouvrir_curseur() as curseur:
        curseur.execute("SELECT empreinte_texte FROM collecte.fragment_lieu WHERE fichier_json = %s", (nom_fichier,))
        return {ligne[0] for ligne in curseur.fetchall()}


def supprimer_fragments_obsoletes(nom_fichier: str, empreintes_a_garder: set[str]) -> int:
    with ouvrir_curseur() as curseur:
        curseur.execute("DELETE FROM collecte.fragment_lieu "
                        "WHERE fichier_json = %s AND empreinte_texte <> ALL(%s::text[])",
                        (nom_fichier, list(empreintes_a_garder)))
        return curseur.rowcount


def supprimer_fragments_des_fichiers_absents(noms_fichiers_presents: list[str]) -> int:
    with ouvrir_curseur() as curseur:
        curseur.execute("DELETE FROM collecte.fragment_lieu WHERE fichier_json <> ALL(%s::text[])",
                        (noms_fichiers_presents,))
        return curseur.rowcount


def compter_fragments() -> int:
    with ouvrir_curseur() as curseur:
        curseur.execute("SELECT count(*) FROM collecte.fragment_lieu")
        return curseur.fetchone()[0]


def lister_tables_manquantes() -> list[str]:
    tables_manquantes = []

    with ouvrir_curseur() as curseur:
        for table in TABLES_ATTENDUES:
            curseur.execute("SELECT to_regclass(%s)::text", (table,))

            if curseur.fetchone()[0] is None:
                tables_manquantes.append(table)

    return tables_manquantes
