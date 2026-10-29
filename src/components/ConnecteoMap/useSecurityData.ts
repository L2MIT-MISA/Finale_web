import { useEffect, useState } from 'react';
import type { Lieu, SecurityData, ServiceProche } from './types';

const RAYON_M = 5000; // on cherche dans 5 km autour du lieu

interface OverpassElement {
    lat?: number;
    lon?: number;
    center?: { lat: number; lon: number };
    tags?: Record<string, string>;
}

interface OverpassResponse {
    elements: OverpassElement[];
}

interface Resultat {
    lieu: Lieu | null;
    data: SecurityData | null;
    erreur: string | null;
}

// Distance entre deux points GPS (formule de haversine)
function distanceM(lat1: number, lng1: number, lat2: number, lng2: number): number {
    const R = 6371000; // rayon moyen de la Terre en m
    const rad = (x: number) => (x * Math.PI) / 180;
    const dLat = rad(lat2 - lat1);
    const dLng = rad(lng2 - lng1);
    const a =
        Math.sin(dLat / 2) ** 2 +
        Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
}

// 100 si distance = 0, 0 si distance >= max (interpolation linéaire)
const scoreDistance = (d: number | null, max: number): number =>
    d == null ? 0 : Math.max(0, Math.round(100 * (1 - d / max)));

function resumer(elements: OverpassElement[], type: string, lat: number, lng: number): ServiceProche {
    const distances = elements
        .filter((e) => e.tags?.amenity === type)
        .map((e) => {
            const eLat = e.lat ?? e.center?.lat;
            const eLng = e.lon ?? e.center?.lon;
            if (eLat === undefined || eLng === undefined) return NaN;
            return distanceM(lat, lng, eLat, eLng);
        })
        .filter((d) => Number.isFinite(d))
        .sort((a, b) => a - b);
    return { count: distances.length, nearestDistance: distances[0] ?? null };
}

export interface UseSecurityDataResult {
    data: SecurityData | null;
    chargement: boolean;
    erreur: string | null;
}

export function useSecurityData(lieu: Lieu | null): UseSecurityDataResult {
    // Le résultat est associé au lieu qui l'a produit : on n'affiche jamais
    // les données d'un ancien lieu pendant le chargement du nouveau.
    const [resultat, setResultat] = useState<Resultat>({ lieu: null, data: null, erreur: null });

    useEffect(() => {
        if (!lieu) return undefined;
        const ctrl = new AbortController();

        const { lat, lng } = lieu;
        const around = `(around:${RAYON_M},${lat},${lng})`;
        const requete =
            `[out:json][timeout:25];(` +
            `nwr["amenity"="police"]${around};` +
            `nwr["amenity"="hospital"]${around};` +
            `nwr["amenity"="pharmacy"]${around};` +
            `);out center;`;

        fetch('https://overpass-api.de/api/interpreter', {
            method: 'POST',
            body: 'data=' + encodeURIComponent(requete),
            signal: ctrl.signal
        })
            .then((r) => {
                if (!r.ok) throw new Error('Service de données indisponible, réessayez.');
                return r.json() as Promise<OverpassResponse>;
            })
            .then((json) => {
                const police = resumer(json.elements, 'police', lat, lng);
                const hospitals = resumer(json.elements, 'hospital', lat, lng);
                const pharmacies = resumer(json.elements, 'pharmacy', lat, lng);

                // Score = moyenne des 3 sous-scores de proximité (heuristique)
                const score = Math.round(
                    (scoreDistance(police.nearestDistance, RAYON_M) +
                        scoreDistance(hospitals.nearestDistance, RAYON_M) +
                        scoreDistance(pharmacies.nearestDistance, RAYON_M)) / 3
                );

                setResultat({
                    lieu,
                    data: { isDemo: false, score, police, hospitals, pharmacies },
                    erreur: null
                });
            })
            .catch((e: unknown) => {
                if (e instanceof Error && e.name === 'AbortError') return;
                setResultat({
                    lieu,
                    data: null,
                    erreur:
                        e instanceof TypeError
                            ? 'Connexion impossible au service de données.'
                            : e instanceof Error
                              ? e.message
                              : 'Erreur inconnue.'
                });
            });

        return () => ctrl.abort(); // annule si on change de lieu
    }, [lieu]);

    // Dérivé : vrai dès qu'un lieu existe et qu'aucun résultat n'est arrivé,
    // y compris pendant le rendu qui précède l'effet (évite un flash de démo).
    const courant = lieu && resultat.lieu === lieu ? resultat : null;
    const data = courant?.data ?? null;
    const erreur = courant?.erreur ?? null;
    const chargement = Boolean(lieu) && !data && !erreur;

    return { data, chargement, erreur };
}
