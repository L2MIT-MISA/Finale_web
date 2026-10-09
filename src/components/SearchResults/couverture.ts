// Couverture réseau d'un lieu, calculée côté front à partir des pylônes (GET /api/pylones/bbox).

const API = `${import.meta.env.VITE_SEARCH_API_URL || "http://127.0.0.1:8000"}/api/pylones`;
const RAYON_KM = 12;
const TECHS = ["2G", "3G", "4G", "5G"] as const;
const PORTEE_M: Record<(typeof TECHS)[number], number> = { "2G": 35000, "3G": 10000, "4G": 5000, "5G": 1000 };
export const OPERATEURS = ["Orange", "Telma", "Airtel"] as const;

export type Operateur = (typeof OPERATEURS)[number];
export type Tech = (typeof TECHS)[number];

export interface CouvertureOperateur {
  nom: Operateur;
  techs: Record<Tech, boolean>;
  pylone: { nom: string; distance: number } | null;
}

export interface Couverture {
  operateurs: CouvertureOperateur[];
  label: string;
  brief: string;
  ok: boolean;
}

interface Pylone {
  nom?: string;
  code_site?: string;
  lat: number | string;
  lon: number | string;
  code_operateur?: string;
  proprietaire?: string;
  portee_km?: number | null;
  tech_2g?: boolean;
  tech_3g?: boolean;
  tech_4g?: boolean;
  tech_5g?: boolean;
}

function operateurDe(p: Pylone): Operateur | null {
  const code = String(p.code_operateur || p.proprietaire || "").toUpperCase();
  if (code.includes("TELMA") || code.includes("YAS")) return "Telma";
  if (code.includes("ORANGE")) return "Orange";
  if (code.includes("AIRTEL")) return "Airtel";
  return null;
}

function haversineM(lat1: number, lng1: number, lat2: number, lng2: number) {
  const r = (d: number) => (d * Math.PI) / 180;
  const a =
    Math.sin(r(lat2 - lat1) / 2) ** 2 + Math.cos(r(lat1)) * Math.cos(r(lat2)) * Math.sin(r(lng2 - lng1) / 2) ** 2;
  return 6371000 * 2 * Math.asin(Math.sqrt(a));
}

export async function chargerCouverture(lat: number, lng: number, signal?: AbortSignal): Promise<Couverture> {
  const dLat = RAYON_KM / 111;
  const dLng = RAYON_KM / (111 * Math.cos((lat * Math.PI) / 180));
  const url = `${API}/bbox?minLat=${lat - dLat}&minLng=${lng - dLng}&maxLat=${lat + dLat}&maxLng=${lng + dLng}`;
  const res = await fetch(url, { signal });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const pylones = (await res.json()) as Pylone[];

  const operateurs: CouvertureOperateur[] = OPERATEURS.map((nom) => ({
    nom,
    techs: { "2G": false, "3G": false, "4G": false, "5G": false },
    pylone: null,
  }));

  for (const p of pylones) {
    const nom = operateurDe(p);
    const plat = parseFloat(String(p.lat));
    const plon = parseFloat(String(p.lon));
    if (!nom || Number.isNaN(plat) || Number.isNaN(plon)) continue;
    const op = operateurs.find((o) => o.nom === nom)!;
    const d = haversineM(lat, lng, plat, plon);
    if (!op.pylone || d < op.pylone.distance) op.pylone = { nom: p.nom || p.code_site || "Pylône", distance: d };
    const portee = p.portee_km ? p.portee_km * 1000 : Infinity;
    for (const t of TECHS) {
      const actif = p[`tech_${t.toLowerCase()}` as keyof Pylone] === true;
      if (actif && d <= Math.min(PORTEE_M[t], portee)) op.techs[t] = true;
    }
  }

  const meilleure = (o: CouvertureOperateur) => TECHS.reduce((m, t, i) => (o.techs[t] ? i + 1 : m), 0);
  const best = Math.max(...operateurs.map(meilleure));
  const gen = best >= 4 ? "5G" : best === 3 ? "4G" : best === 2 ? "3G" : best === 1 ? "2G" : null;
  const label =
    gen === "5G" ? "5G disponible" : gen === "4G" ? "4G disponible" : gen === "3G" ? "3G maximum" : gen === "2G" ? "2G seulement" : "Aucun réseau";
  const noms = operateurs.filter((o) => meilleure(o) === best).map((o) => o.nom).join(", ");
  return {
    operateurs,
    label,
    brief: gen ? `${noms} en ${gen}.` : "Aucun pylône à proximité.",
    ok: best >= 3,
  };
}
