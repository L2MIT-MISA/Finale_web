import { normalizeText } from "../normalize/normalizeText.ts";
import { similarity } from "../correction/similarity.ts";


// ---------------------------------------------------------------------------
// Configuration (variables d'environnement, toutes facultatives)
//   GEOCODER_URL             défaut : https://nominatim.openstreetmap.org
//   GEOCODER_USER_AGENT      défaut : connecteo-search/1.0  (mettez votre email !)
//   GEOCODER_COUNTRY_CODES   défaut : mg  (pays prioritaire, avant recherche mondiale)
//   GEOCODER_TIMEOUT_MS      défaut : 3000
// ---------------------------------------------------------------------------
function env(name: string, fallback: string): string {
  try {
    return (globalThis as any).Deno?.env.get(name) ?? fallback;
  } catch {
    return fallback;
  }
}

const BASE_URL = () => env("GEOCODER_URL", "https://nominatim.openstreetmap.org");
const USER_AGENT = () => env("GEOCODER_USER_AGENT", "connecteo-search/1.0");
const COUNTRY_CODES = () => env("GEOCODER_COUNTRY_CODES", "mg");
const TIMEOUT_MS = () => Number(env("GEOCODER_TIMEOUT_MS", "3000"));

// Cache mémoire (la politique de Nominatim demande de mettre les résultats en cache)
const CACHE = new Map<string, string | null>();
const CACHE_MAX = 500;

// Le résultat renvoyé doit vraiment ressembler à ce que l'utilisateur a tapé,
// sinon "blablabla" pourrait tomber sur un commerce au hasard.
function matchesQuery(candidate: string, result: any): boolean {
  const q = normalizeText(candidate);
  const names = [
    result.name,
    ...(result.namedetails ? Object.values(result.namedetails) : [])
  ]
    .filter((n) => typeof n === "string")
    .map((n: string) => normalizeText(n));

  if (names.some((n) => n === q || n.includes(q) || similarity(n, q) >= 0.8)) {
    return true;
  }

  const display = normalizeText(String(result.display_name ?? ""));
  return display.split(",").some((part) => similarity(part.trim(), q) >= 0.8);
}

async function searchNominatim(
  candidate: string,
  countryCodes?: string
): Promise<string | null> {
  const params = new URLSearchParams({
    q: candidate,
    format: "jsonv2",
    limit: "5",
    namedetails: "1"
  });

  if (countryCodes) {
    params.set("countrycodes", countryCodes);
  }

  const response = await fetch(`${BASE_URL()}/search?${params}`, {
    headers: {
      "User-Agent": USER_AGENT(),
      "Accept-Language": "fr"
    },
    signal: AbortSignal.timeout(TIMEOUT_MS())
  });

  if (!response.ok) {
    throw new Error(`Geocoder HTTP ${response.status}`);
  }

  const results = await response.json();

  for (const r of results) {
    if (matchesQuery(candidate, r)) {
      // On ne garde que le nom du lieu
      return r.name || candidate;
    }
  }

  return null;
}

/**
 * Vérifie qu'un texte est un lieu réel.
 *  - string    : le lieu existe (son nom)
 *  - null          : l'API répond, mais ce n'est pas un lieu connu
 *  - undefined     : l'API est indisponible (erreur / timeout) → on ne sait pas
 */
export async function geocode(
  candidate: string
): Promise<string | null | undefined> {
  const key = normalizeText(candidate);

  if (key.length < 2) {
    return null;
  }

  if (CACHE.has(key)) {
    return CACHE.get(key);
  }

  try {
    // 1) pays prioritaire (Madagascar par défaut), 2) monde entier
    const priority = COUNTRY_CODES();
    let place = priority ? await searchNominatim(candidate, priority) : null;

    if (!place) {
      place = await searchNominatim(candidate);
    }

    if (CACHE.size >= CACHE_MAX) {
      CACHE.delete(CACHE.keys().next().value as string);
    }
    CACHE.set(key, place);

    return place;
  } catch (error) {
    console.error("geocode error:", error);
    return undefined;
  }
}
