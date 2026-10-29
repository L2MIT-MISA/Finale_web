import { supabase } from '../../services/supabase';

export type NomTech = '5g' | '4g' | '3g' | '2g' | 'none';

export interface Point
{
    lat: number;
    lng: number;
}

export interface Pylone extends Point
{
    tech: NomTech;
}

export interface SegmentReseau<T extends Point = Point>
{
    tech: NomTech;
    couleur: string;
    points: T[];
}

interface LignePylone
{
    lat: number | string;
    lon: number | string;
    tech?: string | null;
}

export const COULEUR_TECH: Record<NomTech, string> = {
    '5g': '#16a34a',
    '4g': '#16a34a',
    '3g': '#eab308',
    '2g': '#f97316',
    'none': '#e5484d'
};

export const LABEL_TECH: Record<NomTech, string> = {
    '5g': '5G',
    '4g': '4G',
    '3g': '3G',
    '2g': '2G',
    'none': 'Aucun réseau'
};

export const SEUIL_M = 8000;

let cacheReseau: Pylone[] | null = null;
let promesseReseau: Promise<Pylone[]> | null = null;

export function couleurTech(tech: string): string
{
    return(COULEUR_TECH[tech as NomTech] || COULEUR_TECH.none);
}

export function labelTech(tech: string): string
{
    return(LABEL_TECH[tech as NomTech] || 'Inconnu');
}

async function lirePylonesReseau(): Promise<Pylone[]>
{
    let reponse: { data: unknown; error: { message: string } | null };
    let lignes: LignePylone[];

    try
    {
        reponse = await supabase.rpc('pylones_reseau');
        if (reponse.error)
        {
            throw new Error(reponse.error.message);
        }
        lignes = (reponse.data ?? []) as LignePylone[];
        cacheReseau = lignes
            .map((ligne) => ({
                lat: Number(ligne.lat),
                lng: Number(ligne.lon),
                tech: (ligne.tech || 'none') as NomTech
            }))
            .filter((pylone) => Number.isFinite(pylone.lat) && Number.isFinite(pylone.lng));
        return(cacheReseau);
    }
    catch (erreur)
    {
        promesseReseau = null;
        throw(erreur);
    }
}

export function chargerPylonesReseau(): Promise<Pylone[]>
{
    if (cacheReseau)
    {
        return(Promise.resolve(cacheReseau));
    }
    if (!promesseReseau)
    {
        promesseReseau = lirePylonesReseau();
    }
    return(promesseReseau);
}

export function distanceM(a: Point, b: Point): number
{
    const rayon = 6371000;
    const dLat = ((b.lat - a.lat) * Math.PI) / 180;
    const dLng = ((b.lng - a.lng) * Math.PI) / 180;
    const lat1 = (a.lat * Math.PI) / 180;
    const lat2 = (b.lat * Math.PI) / 180;
    const x = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;

    return(2 * rayon * Math.asin(Math.sqrt(x)));
}

export function techDuPoint(point: Point, pylones: Pylone[] | null, seuilM: number = SEUIL_M): NomTech | null
{
    let meilleureTech: NomTech = 'none';
    let meilleureDistance = Infinity;
    let pylone: Pylone;
    let distance: number;

    if (!pylones)
    {
        return(null);
    }
    for (pylone of pylones)
    {
        distance = distanceM(point, pylone);
        if (distance < meilleureDistance)
        {
            meilleureDistance = distance;
            meilleureTech = pylone.tech;
        }
    }
    return(meilleureDistance <= seuilM ? meilleureTech : 'none');
}

export function decouperParReseau<T extends Point>(points: T[] | null | undefined, pylones: Pylone[] | null): SegmentReseau<T>[]
{
    let techs: NomTech[];
    let segments: { tech: NomTech; points: T[] }[] = [];
    let courant: { tech: NomTech; points: T[] };
    let indice: number;

    if (!points || points.length === 0)
    {
        return([]);
    }
    techs = points.map((pt) => techDuPoint(pt, pylones) || 'none');
    courant = { tech: techs[0], points: [points[0]] };
    for (indice = 1; indice < points.length; indice++)
    {
        courant.points.push(points[indice]);
        if (techs[indice] !== courant.tech)
        {
            segments.push(courant);
            courant = { tech: techs[indice], points: [points[indice]] };
        }
    }
    segments.push(courant);
    return(segments.map((segment) => ({
        tech: segment.tech,
        couleur: couleurTech(segment.tech),
        points: segment.points
    })));
}
