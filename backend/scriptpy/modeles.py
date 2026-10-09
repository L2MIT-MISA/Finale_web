from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Literal, get_args

from pydantic import BaseModel, Field, field_validator, model_validator

from outils import convertir_en_decimal, coordonnees_valides, retirer_accents

NiveauLieu = Literal["province", "region", "district", "commune", "fokontany", "site", "autre"]
PrecisionCoordonnees = Literal["precis", "centroide", "repli_hierarchique", "absent"]
OrigineLieu = Literal["referentiel", "base_connaissances", "google", "osm"]
NIVEAUX_VALIDES = get_args(NiveauLieu)
PRECISIONS_VALIDES = get_args(PrecisionCoordonnees)


def convertir_en_niveau_valide(valeur) -> str:
    niveau = retirer_accents(str(valeur or "")).strip().lower()

    return niveau if niveau in NIVEAUX_VALIDES else "autre"


def convertir_en_precision_valide(valeur, precision_par_defaut: str) -> str:
    precision = retirer_accents(str(valeur or "")).strip().lower()
    return precision if precision in PRECISIONS_VALIDES else precision_par_defaut


class Lieu(BaseModel):
    nom: str
    niveau: NiveauLieu = "autre"
    code_officiel: str | None = None          # code du référentiel (ex. "210101") ; None si lieu hors référentiel
    region: str | None = None
    district: str | None = None
    produit: str | None = None                # format « produits » : ex. "Vanille"
    categorie: str | None = None              # format « produits » : ex. "Site agro-touristique"
    description: str = ""
    latitude: float | None = None
    longitude: float | None = None
    precision_coordonnees: PrecisionCoordonnees = "absent"
    note_google: float | None = None          # de 0 à 5
    nombre_avis_google: int | None = None
    avis: str | None = None
    sources_citees: str | None = None
    mots_cles: list[str] = Field(default_factory=list)
    pertinence: float = 0.0                   # de 0 à 1 : lien avec la requête (sert au classement)
    confiance: float = 0.5                    # de 0 (incertain) à 1 (très sûr)
    origine: OrigineLieu
    source: str | None = None                 # fichier JSON ou adresse web d'où vient l'information
    images: list[str] = Field(default_factory=list)   # URL d'images d'aperçu (http/https uniquement)
    adresse: str | None = None
    telephone: str | None = None
    site_web: str | None = None
    horaires: str | None = None

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def convertir_en_nombre(cls, valeur):
        return convertir_en_decimal(valeur)

    @field_validator("confiance", "pertinence")
    @classmethod
    def borner_entre_zero_et_un(cls, valeur: float) -> float:
        return min(1.0, max(0.0, valeur))

    @field_validator("note_google")
    @classmethod
    def refuser_une_note_hors_echelle(cls, valeur: float | None) -> float | None:
        return valeur if valeur is not None and 0 <= valeur <= 5 else None

    @model_validator(mode="after")
    def verifier_les_coordonnees(self):

        if not coordonnees_valides(self.latitude, self.longitude):
            self.latitude = self.longitude = None
            self.precision_coordonnees = "absent"

        return self

    def a_des_coordonnees(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def definir_coordonnees(self, latitude: float, longitude: float, precision: str):
        self.latitude, self.longitude, self.precision_coordonnees = latitude, longitude, precision

    def vers_dictionnaire_sortie(self) -> dict:
        return {
            "nom": self.nom,
            "niveau": self.niveau,
            "code_officiel": self.code_officiel,
            "region": self.region,
            "district": self.district,
            "produit": self.produit,
            "categorie": self.categorie,
            "description": self.description,
            "coordonnees": {"latitude": self.latitude, "longitude": self.longitude,
                            "precision": self.precision_coordonnees},
            "note_google": (None if self.note_google is None
                            else {"note": self.note_google, "nombre_avis": self.nombre_avis_google}),
            "avis": self.avis,
            "sources_citees": self.sources_citees,
            "mots_cles": self.mots_cles,
            "pertinence": round(self.pertinence, 2),
            "confiance": round(self.confiance, 2),
            "origine": self.origine,
            "source": self.source,
            "images": self.images,
            "image": self.images[0] if self.images else None,
            "adresse": self.adresse,
            "telephone": self.telephone,
            "site_web": self.site_web,
            "horaires": self.horaires,
        }


class LieuProposeParLeModele(BaseModel):
    nom: str
    niveau: NiveauLieu
    region: str | None = None
    district: str | None = None
    description: str = ""
    latitude: float | None = None
    longitude: float | None = None
    reference_source: str | None = None       # R1, W1... : le bloc de source qui justifie ce lieu
    confiance: float = 0.5


class ReponseDuModele(BaseModel):
    intention: Literal["lieu", "theme"]       # lieu : l'utilisateur cherche un endroit ; theme : un produit, une activité
    reponse: str                              # 2 phrases maximum, en français
    mots_cles: list[str]
    lieux: list[LieuProposeParLeModele]


class ResumeDuModele(BaseModel):
    intention: Literal["lieu", "theme"]
    reponse: str
    mots_cles: list[str]


@dataclass
class SourceDisponible:
    reference: str                            # "R1" référentiel, "F1" connaissances, "W1" page Google
    origine: str                              # referentiel | base_connaissances | google
    texte: str = ""                           # ce que le modèle lit
    lieu: Lieu | None = None                  # sources R : lieu aux coordonnées sûres (None pour W)
    titre: str | None = None
    url: str | None = None
    fichier_json: str | None = None


@dataclass
class FragmentConnaissance:
    nom_lieu: str
    niveau_lieu: str
    texte: str
    fichier_json: str                         # chemin relatif à donnees/, ex. "produits/vanille.json"
    code_lieu: str | None = None
    region: str | None = None
    district: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    precision_coordonnees: str = "absent"
    produit: str | None = None
    categorie: str | None = None
    note_google: float | None = None
    nombre_avis_google: int | None = None
    avis: str | None = None
    sources_citees: str | None = None
    mots_cles: list[str] = field(default_factory=list)
    source_url: str | None = None
    confiance: float = 0.5
    similarite: float = 0.0                   # remplie à la recherche : 1 = même sens, 0 = aucun rapport

    def calculer_empreinte(self) -> str:
        contenu = [self.nom_lieu, self.niveau_lieu, self.texte, self.code_lieu, self.region, self.district,
                   self.latitude, self.longitude, self.precision_coordonnees, self.produit, self.categorie,
                   self.note_google, self.nombre_avis_google, self.avis, self.sources_citees, sorted(self.mots_cles),
                   self.source_url, self.confiance]

        return hashlib.sha1(json.dumps(contenu, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


class AnalyseTour(BaseModel):
    """Ce que l'IA comprend du dernier message de l'utilisateur (voir PROMPT_ANALYSE)."""
    action: Literal["chercher", "discuter", "carte", "preciser"]
    type_recherche: Literal["etablissement", "lieu", "theme"] | None = None
    categorie: str | None = None
    lieu: str | None = None
    requete: str = ""
    question: str | None = None

    @field_validator("type_recherche", "categorie", "lieu", "question", mode="before")
    @classmethod
    def convertir_les_valeurs_vides(cls, valeur):
        """Les petits modèles écrivent souvent "null" ou "none" en texte au lieu de null : c'est une absence de valeur."""
        if isinstance(valeur, str) and valeur.strip().lower() in {"", "null", "none", "aucun", "aucune", "n/a", "-"}:
            return None

        return valeur


class ReponseChat(BaseModel):
    """Réponse conversationnelle rédigée par l'IA (voir PROMPT_CHAT)."""
    message: str
    suggestions: list[str] = Field(default_factory=list)
