import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

const LIMITE_LIEUX = 15;

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.resolve(__dirname, '../.env') });

const apiKey = process.env.GEOAPIFY_API_KEY;

async function attendre(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function requeteAvecRetry(url, tentatives = 3) {
  for (let i = 0; i < tentatives; i++) {
    const reponse = await fetch(url);
    if (reponse.ok) return reponse.json();
    if (reponse.status === 429) {
      console.log("Quota atteint, pause 5s...");
      await attendre(5000);
      continue;
    }
    throw new Error(`Erreur HTTP: ${reponse.status}`);
  }
  throw new Error("Échec après plusieurs tentatives");
}

// Recherche les zones dont le nom ressemble à nomZone (nom partiel accepté)
async function chercherZonesSimilaires(nomZone, limit = 10) {
  const texteEncode = encodeURIComponent(nomZone);
  const url = `https://api.geoapify.com/v1/geocode/autocomplete?text=${texteEncode}&filter=countrycode:mg&limit=${limit}&apiKey=${apiKey}`;

  const data = await requeteAvecRetry(url);
  const resultats = data.features || [];

  return resultats.map(r => ({
    nom: r.properties.formatted,
    placeId: r.properties.place_id || null,
    type: r.properties.result_type
  }));
}

// Récupère tous les lieux (pour les catégories données) dans une zone précise (par place_id)
async function recupererLieuxDansZone(placeId, categories) {
  const lieuxUniques = new Map();

  for (const categorie of categories) {
    let offset = 0;
    const limit = 500;

    while (true) {
      const url = `https://api.geoapify.com/v2/places?categories=${categorie}&filter=place:${placeId}&limit=${limit}&offset=${offset}&apiKey=${apiKey}`;

      const data = await requeteAvecRetry(url);
      const features = data.features || [];

      for (const f of features) {
        const id = f.properties.place_id;
        if (!lieuxUniques.has(id)) {
          lieuxUniques.set(id, f);
        }
      }

      if (features.length > 0) {
        console.log(`  [${categorie}] offset=${offset}: ${features.length} résultats`);
      }

      if (features.length < limit) break;
      offset += limit;

      await attendre(150);
    }
  }

  return Array.from(lieuxUniques.values());
}

// nomZone: obligatoire. categories: optionnel
async function recherche(nomZone, categories = null) {
  if (!nomZone || typeof nomZone !== 'string' || nomZone.trim() === '') {
    console.error("Erreur: le nom de la zone est obligatoire.");
    return null;
  }


  // Repli sans clé : Nominatim reçoit uniquement la catégorie et la zone saisies.
  if (!apiKey) {
    if (!categories || categories.length === 0) {
      throw new Error("Une catégorie est obligatoire.");
    }

    const labels = {
      "catering.restaurant": "restaurant",
      "healthcare.pharmacy": "pharmacie",
      "healthcare.hospital": "hôpital",
      "accommodation.hotel": "hôtel",
      "commercial.supermarket": "supermarché",
      "education.school": "école",
      "education.university": "université",
      "service.financial.bank": "banque",
      "service.vehicle.fuel": "station-service",
      "entertainment.museum": "musée",
      "entertainment.cinema": "cinéma",
      "leisure.park": "parc"
    };
    const categorie = categories[0];
    const libelle = labels[categorie] || categorie.split(".").at(-1).replaceAll("_", " ");
    const params = new URLSearchParams({
      q: `${libelle} à ${nomZone}, Madagascar`,
      format: "jsonv2",
      addressdetails: "1",
      extratags: "1",
      namedetails: "1",
      countrycodes: "mg",
      limit: String(LIMITE_LIEUX)
    });
    const response = await fetch(`https://nominatim.openstreetmap.org/search?${params}`, {
      headers: {
        "Accept-Language": "fr",
        "User-Agent": "Connecteo/1.0 (local-search-backend)"
      }
    });
    if (!response.ok) throw new Error(`Nominatim HTTP ${response.status}`);
    const places = await response.json();
    const lieux = places.map((place) => ({
      type: "Feature",
      properties: {
        name: place.namedetails?.name || place.name || place.display_name.split(",")[0],
        country: place.address?.country || "Madagascar",
        region: place.address?.state || null,
        district: place.address?.county || null,
        suburb: place.address?.suburb || null,
        street: place.address?.road || null,
        lon: Number(place.lon),
        lat: Number(place.lat),
        formatted: place.display_name,
        categories: [categorie],
        phone: place.extratags?.phone || null,
        website: place.extratags?.website || null,
        opening_hours: place.extratags?.opening_hours || null
      },
      geometry: { type: "Point", coordinates: [Number(place.lon), Number(place.lat)] }
    }));
    const resultat = { zone: nomZone, categories, nombre_lieux: lieux.length, lieux };
    const monfichier = path.resolve(__dirname, "../data/donnees_brutes.json");
    fs.writeFileSync(monfichier, JSON.stringify(resultat, null, 2), "utf8");
    console.log(`${lieux.length} lieu(x) trouvé(s) via OpenStreetMap/Nominatim.`);
    return resultat;
  }

  console.log(`Recherche de zones correspondant à: "${nomZone}"...`);
  const zones = await chercherZonesSimilaires(nomZone);

  if (zones.length === 0) {
    console.error(`Aucune zone trouvée pour "${nomZone}".`);
    return null;
  }

  // Cas 1: pas de catégorie -> on retourne juste la liste des zones trouvées
  if (!categories || categories.length === 0) {
    console.log(`${zones.length} zone(s) trouvée(s):`);
    zones.forEach((z, i) => console.log(`  ${i + 1}. ${z.nom} (${z.type})`));

    const monfichier = path.resolve(__dirname,"../data/donnees_brutes.json");
    fs.writeFileSync(monfichier, JSON.stringify({ recherche: nomZone, zones }, null, 2), 'utf8');
    console.log(`Résultats enregistrés dans ${monfichier}`);

    return { zones };
  }

  // Cas 2: catégorie(s) fournie(s) -> on prend la meilleure zone et on cherche les lieux dedans
  const meilleureZone = zones.find(z => z.placeId) || zones[0];

  if (!meilleureZone.placeId) {
    console.error(`La zone trouvée ("${meilleureZone.nom}") n'a pas de délimitation exploitable pour la recherche de lieux.`);
    return null;
  }

  console.log(`Zone retenue: ${meilleureZone.nom} (${meilleureZone.type})`);
  console.log(`Catégories recherchées: ${categories.join(', ')}`);
  console.log(`Récupération des lieux dans cette zone...`);

  const lieux = await recupererLieuxDansZone(meilleureZone.placeId, categories);

  const lieuxLimites = lieux.slice(0, LIMITE_LIEUX);

  const resultat = {
    zone: meilleureZone.nom,
    categories,
    nombre_lieux: lieuxLimites.length,
    lieux: lieuxLimites
  };

  const monfichier = path.resolve(__dirname,"../src/data/donnees_brutes.json");
  fs.writeFileSync(monfichier, JSON.stringify(resultat, null, 2), 'utf8');

  console.log(`Succès: ${lieuxLimites.length} lieux retenus sur ${lieux.length} trouvés dans "${meilleureZone.nom}", enregistrés dans ${monfichier}`);

  return resultat;
}

export { recherche, chercherZonesSimilaires, recupererLieuxDansZone };