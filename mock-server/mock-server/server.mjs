// Faux backend Connecteo : permet de développer le front sans serveur ni base de données.
// Aucune dépendance (Node 18+). Pour tout enlever : supprimer ce dossier.
//
// Routes simulées (mêmes chemins et mêmes formats que le vrai projet) :
//   POST /functions/v1/search   -> edge function Supabase "search" (analyse de la requête)
//   POST /search                -> backend Python (liste des lieux + connectivité)
//   GET  /api/pylones/bbox      -> backend Python + Neo4j (pylônes dans une zone)
//   GET  /api/pylones           -> backend Python + Neo4j (tous les pylônes)
//
// Options (variables d'environnement) :
//   PORT=8000        port d'écoute
//   DELAY_MS=300     délai artificiel avant chaque réponse (pour voir les loaders)
//   MOCK_STRICT=0    accepte toutes les catégories (par défaut, on imite le vrai backend,
//                    qui refuse certaines catégories avec une erreur 400)

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DIR = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT) || 8000;
const DELAY_MS = process.env.DELAY_MS !== undefined ? Number(process.env.DELAY_MS) : 300;
const STRICT = process.env.MOCK_STRICT !== "0";

// ---------------------------------------------------------------------------
// 1) Edge function "search" : le VRAI code de supabase/functions/search
//    (correction de fautes, catégories, intentions, lieu vérifié avec Nominatim),
//    empaqueté dans search-function.mjs.
// ---------------------------------------------------------------------------
import { analyze } from "./search-function.mjs";

// ---------------------------------------------------------------------------
// 2) POST /search : mêmes catégories acceptées que backend/search/main.py
// ---------------------------------------------------------------------------
const CATEGORIES_GEOAPIFY = {
  restaurant: "catering.restaurant", fast_food: "catering.fast_food", "fast food": "catering.fast_food",
  bar: "catering.bar",
  pharmacie: "healthcare.pharmacy", pharmacy: "healthcare.pharmacy",
  hopital: "healthcare.hospital", "hôpital": "healthcare.hospital", hospital: "healthcare.hospital",
  clinique: "healthcare.clinic_or_praxis", medecin: "healthcare.clinic_or_praxis",
  "médecin": "healthcare.clinic_or_praxis", dentiste: "healthcare.dentist",
  hotel: "accommodation.hotel", "hôtel": "accommodation.hotel", hostel: "accommodation.hostel",
  auberge: "accommodation.guest_house", motel: "accommodation.motel",
  supermarche: "commercial.supermarket", "supermarché": "commercial.supermarket",
  magasin: "commercial", boutique: "commercial", shopping: "commercial",
  "centre commercial": "commercial.shopping_mall", boulangerie: "commercial.bakery",
  ecole: "education.school", "école": "education.school", lycee: "education.school",
  "lycée": "education.school", universite: "education.university",
  "université": "education.university", college: "education.college", "collège": "education.college",
  banque: "service.financial.bank", atm: "service.financial.atm", distributeur: "service.financial.atm",
  "station essence": "service.vehicle.fuel", "station service": "service.vehicle.fuel",
  garage: "service.vehicle.repair",
  parking: "parking", "station de recharge": "service.vehicle.charging_station",
  bus: "public_transport.bus", gare: "public_transport.train",
  aeroport: "airport", "aéroport": "airport",
  musee: "entertainment.museum", "musée": "entertainment.museum",
  cinema: "entertainment.cinema", "cinéma": "entertainment.cinema",
  parc: "leisure.park", "terrain de jeu": "leisure.playground", "salle de sport": "sport", tourisme: "tourism",
};

const LABELS = {
  "catering.restaurant": "Restaurant", "catering.fast_food": "Fast-food", "catering.bar": "Bar",
  "healthcare.pharmacy": "Pharmacie", "healthcare.hospital": "Hôpital",
  "healthcare.clinic_or_praxis": "Clinique", "healthcare.dentist": "Dentiste",
  "accommodation.hostel": "Auberge", "accommodation.guest_house": "Maison d'hôtes",
  "accommodation.motel": "Motel", "commercial.supermarket": "Supermarché",
  "service.financial.bank": "Banque", "service.financial.atm": "Distributeur",
  "service.vehicle.fuel": "Station-service", "service.vehicle.repair": "Garage",
  "education.school": "École", "education.university": "Université",
};

// Les 15 hôtels réels de backend/search/data/final_results.json servent de base.
// Pour les autres catégories, on les réutilise sous un autre nom (marqué « démo »).
const HOTELS = JSON.parse(fs.readFileSync(path.join(DIR, "data", "final_results.json"), "utf-8")).results;

function placesFor(type) {
  if (type === "accommodation.hotel") return HOTELS;
  const label = LABELS[type] ?? "Lieu";
  return HOTELS.map((h, i) => ({ ...h, id: `mock_${i + 1}`, type, name: `${label} ${h.name} (démo)` }));
}

// ---------------------------------------------------------------------------
// 3) Pylônes : générés (pas de vraies données ici), mêmes champs que PYLON_FIELDS
// ---------------------------------------------------------------------------
function rng(seed) {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rand = rng(42);
const pick = (list) => list[Math.floor(rand() * list.length)];
const hash = (s) => [...s].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);

const OWNERS = { TELMA: "Telma", ORANGE: "Orange Madagascar", AIRTEL: "Airtel Madagascar", GULFSAT: "Gulfsat Madagascar" };
const ZONES = [
  { commune: "Antananarivo Renivohitra", district: "Antananarivo Renivohitra", lat: -18.8792, lng: 47.5079, n: 320, spread: 0.12 },
  { commune: "Toamasina I", district: "Toamasina I", region: "Atsinanana", lat: -18.1492, lng: 49.4023, n: 70, spread: 0.06 },
  { commune: "Antsirabe I", district: "Antsirabe I", region: "Vakinankaratra", lat: -19.8659, lng: 47.0333, n: 70, spread: 0.06 },
  { commune: "Mahajanga I", district: "Mahajanga I", region: "Boeny", lat: -15.7167, lng: 46.3167, n: 70, spread: 0.06 },
  { commune: "Fianarantsoa I", district: "Fianarantsoa I", region: "Haute Matsiatra", lat: -21.4536, lng: 47.0857, n: 70, spread: 0.06 },
  { commune: "Toliara I", district: "Toliara I", region: "Atsimo-Andrefana", lat: -23.35, lng: 43.6667, n: 70, spread: 0.06 },
  { commune: "Antsiranana I", district: "Antsiranana I", region: "Diana", lat: -12.2787, lng: 49.2917, n: 70, spread: 0.06 },
];

let counter = 0;
function makePylone({ code, lat, lon, techs, nom, zone }) {
  counter += 1;
  const urbain = rand() > 0.3;
  return {
    nom: nom ?? `Site ${String(counter).padStart(4, "0")}`,
    code_site: `${code.slice(0, 3)}-${String(counter).padStart(4, "0")}`,
    type_site: pick(["Pylône", "Rooftop", "Mât"]),
    lat: Number(lat.toFixed(6)),
    lon: Number(lon.toFixed(6)),
    hauteur_m: 18 + Math.floor(rand() * 28),
    nom_commune: zone.commune,
    nom_district: zone.district,
    nom_region: zone.region ?? "Analamanga",
    milieu: urbain ? "Urbain" : "Rural",
    proprietaire: OWNERS[code] ?? code,
    code_operateur: code,
    mutualisation: rand() > 0.6 ? "Oui" : "Non",
    source_energie: pick(["Réseau électrique", "Groupe électrogène", "Solaire"]),
    portee_km: Number((urbain ? 1 + rand() * 3 : 3 + rand() * 6).toFixed(1)),
    tech_2g: techs.has("2G"),
    tech_3g: techs.has("3G"),
    tech_4g: techs.has("4G"),
    tech_5g: techs.has("5G"),
  };
}

const PYLONES = [];

// a) Les pylônes cités dans la connectivité des 15 hôtels (cohérence liste <-> carte)
const nearby = new Map();
for (const hotel of HOTELS) {
  const { latitude, longitude } = hotel.location;
  for (const [op, info] of Object.entries(hotel.connectivityDetails?.operators ?? {})) {
    for (const [tech, tower] of Object.entries(info.nearest_towers_by_technology ?? {})) {
      if (!tower) continue;
      const key = `${op}|${tower.name}`;
      if (!nearby.has(key)) {
        const angle = ((hash(key) % 360) * Math.PI) / 180;
        const dLat = (tower.distance_meters * Math.cos(angle)) / 111320;
        const dLon = (tower.distance_meters * Math.sin(angle)) / (111320 * Math.cos((latitude * Math.PI) / 180));
        nearby.set(key, { op, nom: tower.name, lat: latitude + dLat, lon: longitude + dLon, techs: new Set() });
      }
      nearby.get(key).techs.add(tech);
    }
  }
}
for (const t of nearby.values()) {
  PYLONES.push(makePylone({ code: t.op, lat: t.lat, lon: t.lon, techs: t.techs, nom: t.nom, zone: ZONES[0] }));
}

// b) Pylônes de fond autour d'Antananarivo et de quelques grandes villes
for (const zone of ZONES) {
  for (let i = 0; i < zone.n; i++) {
    const code = pick(Object.keys(OWNERS));
    const techs = new Set(["2G"]);
    if (rand() < 0.9) techs.add("3G");
    if (rand() < 0.7) techs.add("4G");
    if (code === "ORANGE" && rand() < 0.15) techs.add("5G");
    const lat = zone.lat + (rand() + rand() - 1) * zone.spread;
    const lon = zone.lng + (rand() + rand() - 1) * zone.spread;
    PYLONES.push(makePylone({ code, lat, lon, techs, zone }));
  }
}

// ---------------------------------------------------------------------------
// Serveur HTTP
// ---------------------------------------------------------------------------
function send(res, status, body) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(body));
}

function readJson(req) {
  return new Promise((resolve) => {
    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
      try { resolve(JSON.parse(raw || "{}")); } catch { resolve(null); }
    });
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const started = Date.now();

  // CORS ouvert : le front tourne sur un autre port (5173)
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", req.headers["access-control-request-headers"] || "*");
  res.on("finish", () => console.log(`${req.method} ${url.pathname} -> ${res.statusCode} (${Date.now() - started} ms)`));

  if (req.method === "OPTIONS") { res.writeHead(204); return res.end(); }

  // Edge function Supabase "search"
  if (req.method === "POST" && url.pathname === "/functions/v1/search") {
    const body = await readJson(req);
    if (!body || typeof body.query !== "string" || body.query.trim() === "") {
      return send(res, 400, { error: "Le champ query est obligatoire." });
    }
    return send(res, 200, await analyze(body.query));
  }

  // Backend : recherche de lieux
  if (req.method === "POST" && url.pathname === "/search") {
    const data = await readJson(req);
    // Comme FastAPI/pydantic : "query" et "type" sont obligatoires
    if (!data || typeof data.query !== "string" || typeof data.type !== "string") {
      return send(res, 422, { detail: "Corps invalide : 'query' et 'type' sont obligatoires." });
    }
    if (!data.category) return send(res, 400, { detail: "La catégorie est obligatoire." });
    await sleep(DELAY_MS);

    const keyword = data.category.trim().toLowerCase();
    const type = CATEGORIES_GEOAPIFY[keyword] ?? (STRICT ? null : "commercial");
    if (!type) {
      return send(res, 400, {
        detail: { message: "Catégorie inconnue", keyword: data.category, categories_disponibles: Object.keys(CATEGORIES_GEOAPIFY).sort() },
      });
    }
    const results = placesFor(type);
    return send(res, 200, { query: data.location || data.query, count: results.length, results });
  }

  // Backend : pylônes dans une zone
  if (req.method === "GET" && url.pathname === "/api/pylones/bbox") {
    const [minLat, minLng, maxLat, maxLng] = ["minLat", "minLng", "maxLat", "maxLng"].map((k) => parseFloat(url.searchParams.get(k)));
    if ([minLat, minLng, maxLat, maxLng].some(Number.isNaN)) {
      return send(res, 422, { detail: "minLat, minLng, maxLat et maxLng sont obligatoires." });
    }
    await sleep(DELAY_MS);
    const inside = PYLONES.filter((p) => p.lat >= minLat && p.lat <= maxLat && p.lon >= minLng && p.lon <= maxLng);
    return send(res, 200, inside.slice(0, 1000));
  }

  // Backend : tous les pylônes
  if (req.method === "GET" && url.pathname === "/api/pylones") {
    await sleep(DELAY_MS);
    return send(res, 200, PYLONES.slice(0, 5000));
  }

  if (req.method === "GET" && url.pathname === "/") return send(res, 200, { message: "Faux backend Connecteo (mock-server)" });
  if (req.method === "GET" && url.pathname === "/health") return send(res, 200, { status: "ok" });

  send(res, 404, { detail: "Not Found" });
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`Faux backend Connecteo sur http://127.0.0.1:${PORT}`);
  console.log(`  ${HOTELS.length} lieux de base, ${PYLONES.length} pylônes générés`);
  console.log(`  Mode strict : ${STRICT ? "oui (imite le vrai backend)" : "non (toutes catégories acceptées)"}`);
  console.log("  Ctrl+C pour arrêter.");
});
