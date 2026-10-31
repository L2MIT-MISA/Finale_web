BEGIN;
DROP INDEX IF EXISTS collecte.idx_fragment_vecteur;
TRUNCATE collecte.fragment_lieu RESTART IDENTITY;
ALTER TABLE collecte.fragment_lieu ALTER COLUMN vecteur TYPE vector(768);
CREATE INDEX idx_fragment_vecteur ON collecte.fragment_lieu USING hnsw (vecteur vector_cosine_ops);
COMMIT;
