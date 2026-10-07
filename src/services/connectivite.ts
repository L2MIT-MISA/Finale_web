import type { ConnectiviteIA, OperateurIA, Techno, TourIA } from "../pages/Search/searchTypes";
import { connectiviteDe } from "./detailsLieu";
import type { Connectivite } from "../pages/Search/searchTypes";

// Connectivité d'un lieu quand l'IA ne l'a pas fournie : calculée à partir des pylônes
// proches (GET /api/pylones/bbox du backend), puis convertie au même format que `connectivityDetails`.

const API = `${import.meta.env.VITE_SEARCH_API_URL || "http://127.0.0.1:8000"}/api/pylones`;
const RAYON_KM = 12;
const TECHS: Techno[] = ["2G", "3G", "4G", "5G"];
const PORTEE_M: Record<Techno, number> = { "2G": 35000, "3G": 10000, "4G": 5000, "5G": 1000 };

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

function haversineM(lat1: number, lng1: number, lat2: number, lng2: number) {
  const r = (d: number) => (d * Math.PI) / 180;
  const a = Math.sin(r(lat2 - lat1) / 2) ** 2 + Math.cos(r(lat1)) * Math.cos(r(lat2)) * Math.sin(r(lng2 - lng1) / 2) ** 2;
  return 6371000 * 2 * Math.asin(Math.sqrt(a));
}

export async function chargerConnectivite(lat: number, lng: number, signal?: AbortSignal): Promise<Connectivite | null> {
  const dLat = RAYON_KM / 111;
  const dLng = RAYON_KM / (111 * Math.cos((lat * Math.PI) / 180));
  const url = `${API}/bbox?minLat=${lat - dLat}&minLng=${lng - dLng}&maxLat=${lat + dLat}&maxLng=${lng + dLng}`;
  const res = await fetch(url, { signal });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const pylones = (await res.json()) as Pylone[];

  const operators: Record<string, OperateurIA> = {};
  for (const p of pylones) {
    const cle = String(p.code_operateur || p.proprietaire || "").trim();
    const plat = parseFloat(String(p.lat));
    const plon = parseFloat(String(p.lon));
    if (!cle || Number.isNaN(plat) || Number.isNaN(plon)) continue;

    const op = (operators[cle] ??= { technologies: {}, technologies_actives: [], nearest_towers_by_technology: {} });
    const d = haversineM(lat, lng, plat, plon);
    const portee = p.portee_km ? p.portee_km * 1000 : Infinity;
    for (const t of TECHS) {
      const actif = p[`tech_${t.toLowerCase()}` as keyof Pylone] === true;
      if (!actif || d > Math.min(PORTEE_M[t], portee)) continue;
      op.technologies![t] = true;
      const proche: TourIA | null | undefined = op.nearest_towers_by_technology![t];
      if (!proche || d < (proche.distance_meters ?? Infinity)) {
        op.nearest_towers_by_technology![t] = { name: p.nom || p.code_site || "Site", distance_meters: Math.round(d) };
      }
    }
  }
  for (const op of Object.values(operators)) op.technologies_actives = TECHS.filter((t) => op.technologies![t]);

  const brut: ConnectiviteIA = { available: Object.keys(operators).length > 0, operators };
  return connectiviteDe(brut);
}
