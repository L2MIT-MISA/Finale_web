-- À exécuter UNE SEULE FOIS si la table collecte.fragment_lieu existe déjà avec des vecteurs bge-m3 (1024 dimensions).
-- nomic-embed-text produit des vecteurs de 768 dimensions : les anciens vecteurs ne sont plus utilisables.
-- Les fragments sont supprimés puis recréés automatiquement au prochain démarrage (indexation des fichiers JSON).
--   psql "$DATABASE_URL" -f migration_vecteurs_768.sql
BEGIN;
DROP INDEX IF EXISTS collecte.idx_fragment_vecteur;
TRUNCATE collecte.fragment_lieu RESTART IDENTITY;
ALTER TABLE collecte.fragment_lieu ALTER COLUMN vecteur TYPE vector(768);
CREATE INDEX idx_fragment_vecteur ON collecte.fragment_lieu USING hnsw (vecteur vector_cosine_ops);
COMMIT;
