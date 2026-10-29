// Faux backend Connecteo : permet de développer le front sans IA, sans serveur ni base de données.
// Aucune dépendance (Node 18+). Pour tout enlever : supprimer ce dossier.
//
// Routes simulées :
//   POST /assistant             -> IA (voir ia-mock.mjs) : JSON { requete, reponse, lieux, carte, ... }
//   GET  /mock-images/:i-:k.svg -> photos de démo référencées par les lieux
//   GET  /api/pylones/bbox      -> backend Python + Neo4j (pylônes dans une zone)
//   GET  /api/pylones           -> backend Python + Neo4j (tous les pylônes)
//
// Options (variables d'environnement) :
//   PORT=8000        port d'écoute
//   DELAY_MS=600     délai artificiel avant chaque réponse (pour voir les loaders)

import http from "node:http";
import { imageDemo, simulerIA } from "./ia-mock.mjs";

const PORT = Number(process.env.PORT) || 8000;
const DELAY_MS = process.env.DELAY_MS !== undefined ? Number(process.env.DELAY_MS) : 600;

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

// Pylônes de fond autour d'Antananarivo et de quelques grandes villes
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

  // IA
  if (req.method === "POST" && url.pathname === "/assistant") {
    const body = await readJson(req);
    await sleep(DELAY_MS);
    if (!body || typeof body.texte !== "string" || !body.texte.trim()) {
      return send(res, 400, { detail: "Le champ 'texte' est obligatoire." });
    }
    return send(res, 200, simulerIA(body.texte.trim(), `http://${req.headers.host}`));
  }

  // Photos de démo
  const img = url.pathname.match(/^\/mock-images\/(\d+)-(\d+)\.svg$/);
  if (req.method === "GET" && img) {
    res.writeHead(200, { "Content-Type": "image/svg+xml", "Cache-Control": "max-age=3600" });
    return res.end(imageDemo(Number(img[1]), Number(img[2])));
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
  console.log(`  ${PYLONES.length} pylônes générés`);
  console.log("  Ctrl+C pour arrêter.");
});
