CREATE OR REPLACE FUNCTION public.pylones_reseau()
RETURNS json
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT COALESCE(json_agg(json_build_object(
        'lat', ST_Y(p.geom::geometry),
        'lon', ST_X(p.geom::geometry),
        'tech', CASE
                    WHEN p.tech_5g THEN '5g'
                    WHEN p.tech_4g THEN '4g'
                    WHEN p.tech_3g THEN '3g'
                    WHEN p.tech_2g THEN '2g'
                    ELSE 'none'
                END)), '[]'::json)
    FROM infrastructure.pylone p
    WHERE p.geom IS NOT NULL;
$$;

CREATE OR REPLACE FUNCTION public.pylones_bbox(
    min_lat double precision,
    min_lng double precision,
    max_lat double precision,
    max_lng double precision)
RETURNS json
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT COALESCE(json_agg(zone_pylones), '[]'::json)
    FROM (
        SELECT p.nom_site AS nom,
               p.code_site,
               p.code_operateur,
               p.type_site,
               ST_Y(p.geom::geometry) AS lat,
               ST_X(p.geom::geometry) AS lon,
               p.hauteur_m,
               p.proprietaire,
               p.tech_2g,
               p.tech_3g,
               p.tech_4g,
               p.tech_5g
        FROM infrastructure.pylone p
        WHERE p.geom && ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)::geography
        LIMIT 1000
    ) AS zone_pylones;
$$;

CREATE OR REPLACE FUNCTION public.statistiques_about()
RETURNS json
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT json_build_object(
        'activeTelecomSites', (SELECT count(DISTINCT code_site)
                               FROM infrastructure.pylone
                               WHERE tech_2g OR tech_3g OR tech_4g OR tech_5g),
        'totalUsers', (SELECT count(*) FROM auth.users));
$$;

REVOKE ALL ON FUNCTION public.pylones_reseau() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.pylones_bbox(double precision, double precision, double precision, double precision) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.statistiques_about() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.pylones_reseau() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.pylones_bbox(double precision, double precision, double precision, double precision) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.statistiques_about() TO anon, authenticated;

DO $$
BEGIN
    ALTER TABLE public.spatial_ref_sys ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS lecture_seule ON public.spatial_ref_sys;
    CREATE POLICY lecture_seule ON public.spatial_ref_sys FOR SELECT USING (true);
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE 'spatial_ref_sys appartient a un autre role : etape ignoree';
END
$$;
