export const API_URL = 'http://localhost:3001';

// Couleurs des technologies réseau
export const COULEUR_TECH = {
    '5g': '#16a34a', // vert
    '4g': '#16a34a', // vert
    '3g': '#eab308', // jaune
    '2g': '#f97316', // orange
    'none': '#e5484d'  // rouge
};

export const LABEL_TECH = {
    '5g': '5G',
    '4g': '4G',
    '3g': '3G',
    '2g': '2G',
    'none': 'Aucun réseau'
};

export function couleurTech(tech) {
    return COULEUR_TECH[tech] || COULEUR_TECH.none;
}

export function labelTech(tech) {
    return LABEL_TECH[tech] || 'Inconnu';
}

let _cacheReseau = null;
let _cachePromise = null;

export async function chargerPylonesReseau() {
    if (_cacheReseau) return _cacheReseau;
    if (_cachePromise) return _cachePromise;

    _cachePromise = (async () => {
        const res = await fetch(`${API_URL}/api/pylones/network`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        _cacheReseau = data
            .map((p) => ({
                lat: Number(p.lat),
                lng: Number(p.lon),
                tech: p.tech || 'none'
            }))
            .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng));
        return _cacheReseau;
    })();

    return _cachePromise;
}

// Distance approx (Haversine) en mètres
export function distanceM(a, b) {
    const R = 6371000;
    const dLat = (b.lat - a.lat) * Math.PI / 180;
    const dLng = (b.lng - a.lng) * Math.PI / 180;
    const lat1 = a.lat * Math.PI / 180;
    const lat2 = b.lat * Math.PI / 180;
    const x = Math.sin(dLat / 2) ** 2 +
        Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x));
}

// Seuil : si le pylône le plus proche est plus loin que SEUIL_M, on renvoie 'none'
export const SEUIL_M = 8000; // 8 km

// Renvoie la tech du pylône le plus proche du point, ou null si pylônes non chargés.
export function techDuPoint(point, pylones, seuilM = SEUIL_M) {
    if (!pylones) return null; // pas encore prêt
    let bestTech = 'none';
    let bestD = Infinity;
    for (const p of pylones) {
        const d = distanceM(point, p);
        if (d < bestD) {
            bestD = d;
            bestTech = p.tech;
        }
    }
    return bestD <= seuilM ? bestTech : 'none';
}

// Découpe une polyligne en segments de même couleur
export function decouperParReseau(points, pylones) {
    if (!points || points.length === 0) return [];

    const techs = points.map((pt) => techDuPoint(pt, pylones) || 'none');

    const segments = [];
    let courant = { tech: techs[0], points: [points[0]] };

    for (let i = 1; i < points.length; i++) {
        if (techs[i] === courant.tech) {
            courant.points.push(points[i]);
        } else {
            courant.points.push(points[i]); // point charnière dupliqué
            segments.push(courant);
            courant = { tech: techs[i], points: [points[i]] };
        }
    }
    segments.push(courant);

    return segments.map((s) => ({
        tech: s.tech,
        couleur: couleurTech(s.tech),
        points: s.points
    }));
}