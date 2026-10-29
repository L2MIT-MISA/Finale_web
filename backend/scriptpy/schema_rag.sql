CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE SCHEMA IF NOT EXISTS collecte;

CREATE TABLE IF NOT EXISTS collecte.fragment_lieu (
    id_fragment            BIGSERIAL PRIMARY KEY,
    nom_lieu               TEXT NOT NULL,
    niveau_lieu            TEXT NOT NULL
        CHECK (niveau_lieu IN ('province','region','district','commune','fokontany','site','autre')),
    code_lieu              BIGINT,
    region                 TEXT,
    district               TEXT,
    latitude               NUMERIC(10,7),
    longitude              NUMERIC(10,7),
    precision_coordonnees  TEXT NOT NULL DEFAULT 'absent'
        CHECK (precision_coordonnees IN ('precis','centroide','repli_hierarchique','absent')),
    texte                  TEXT NOT NULL,
    mots_cles              TEXT[] NOT NULL DEFAULT '{}',
    fichier_json           TEXT NOT NULL,
    source_url             TEXT,
    confiance              NUMERIC(3,2) NOT NULL DEFAULT 0.5,
    empreinte_texte        TEXT NOT NULL,
    vecteur                vector(768) NOT NULL,
    date_creation          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (fichier_json, empreinte_texte),
    CHECK ((latitude IS NULL) = (longitude IS NULL))
);

-- Colonnes du format « produits » (sans effet si elles existent déjà)
ALTER TABLE collecte.fragment_lieu
    ADD COLUMN IF NOT EXISTS produit TEXT,
    ADD COLUMN IF NOT EXISTS categorie TEXT,
    ADD COLUMN IF NOT EXISTS note_google NUMERIC(2,1) CHECK (note_google BETWEEN 0 AND 5),
    ADD COLUMN IF NOT EXISTS nombre_avis_google INTEGER CHECK (nombre_avis_google >= 0),
    ADD COLUMN IF NOT EXISTS avis TEXT,
    ADD COLUMN IF NOT EXISTS sources_citees TEXT;

CREATE INDEX IF NOT EXISTS idx_fragment_vecteur ON collecte.fragment_lieu USING hnsw (vecteur vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_fragment_mots_cles ON collecte.fragment_lieu USING gin (mots_cles);
CREATE INDEX IF NOT EXISTS idx_fragment_code_lieu ON collecte.fragment_lieu (code_lieu);
