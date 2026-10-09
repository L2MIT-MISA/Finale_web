// ../p2/ConnecteoWEB/supabase/functions/search/normalize/normalizeText.ts
function normalizeText(text) {
  return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[’']/g, "'").replace(/\s+/g, " ").trim();
}

// ../p2/ConnecteoWEB/supabase/functions/search/dictionaries/categories.ts
var CATEGORIES = {
  restaurant: [
    "restaurant",
    "resto",
    "restauration",
    "snack",
    "fast food",
    "cafe"
  ],
  hotel: [
    "hotel",
    "hebergement"
  ],
  bank: [
    "banque"
  ],
  pharmacy: [
    "pharmacie"
  ],
  hospital: [
    "hopital"
  ],
  gas_station: [
    "station service",
    "station-service"
  ]
};

// ../p2/ConnecteoWEB/supabase/functions/search/dictionaries/intents.ts
var INTENTS = {
  eat: [
    "manger",
    "ou manger",
    "me restaurer",
    "chercher a manger"
  ],
  withdraw_money: [
    "retirer de l'argent",
    "retirer argent",
    "distributeur",
    "retirer des especes"
  ],
  sleep: [
    "dormir",
    "ou dormir",
    "se loger",
    "me loger"
  ]
};

// ../p2/ConnecteoWEB/supabase/functions/search/correction/similarity.ts
function levenshtein(a, b) {
  const matrix = [];
  for (let i = 0; i <= b.length; i++) {
    matrix[i] = [i];
  }
  for (let j = 0; j <= a.length; j++) {
    matrix[0][j] = j;
  }
  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      if (b[i - 1] === a[j - 1]) {
        matrix[i][j] = matrix[i - 1][j - 1];
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j] + 1,
          matrix[i][j - 1] + 1,
          matrix[i - 1][j - 1] + 1
        );
      }
    }
  }
  return matrix[b.length][a.length];
}
function similarity(a, b) {
  const maxLength = Math.max(a.length, b.length);
  if (maxLength === 0) {
    return 1;
  }
  return 1 - levenshtein(a, b) / maxLength;
}

// ../p2/ConnecteoWEB/supabase/functions/search/correction/correctTypos.ts
var THRESHOLD = 0.75;
var MIN_LENGTH_FOR_FUZZY = 6;
function getKnownTerms() {
  const terms = /* @__PURE__ */ new Set();
  for (const aliases of Object.values(CATEGORIES)) {
    for (const alias of aliases) {
      terms.add(alias);
    }
  }
  for (const phrases of Object.values(INTENTS)) {
    for (const phrase of phrases) {
      terms.add(phrase);
    }
  }
  return [...terms];
}
function findCorrection(word, terms) {
  if (word.length < MIN_LENGTH_FOR_FUZZY) {
    return null;
  }
  let bestMatch = null;
  let bestScore = 0;
  for (const term of terms) {
    if (term.includes(" ")) {
      continue;
    }
    const score = similarity(word, term);
    if (score > bestScore) {
      bestScore = score;
      bestMatch = term;
    }
  }
  return bestScore >= THRESHOLD ? bestMatch : null;
}
function correctTypos(text) {
  const terms = getKnownTerms();
  return text.split(" ").map((word) => findCorrection(word, terms) ?? word).join(" ");
}

// ../p2/ConnecteoWEB/supabase/functions/search/dictionaries/actions.ts
var ACTIONS = {
  restaurant: [
    "manger",
    "mange",
    "mang\xE9",
    "manger \xE0",
    "o\xF9 manger",
    "pour manger"
  ],
  hotel: [
    "dormir",
    "dors",
    "dormir \xE0",
    "se loger",
    "loger"
  ],
  pharmacy: [
    "acheter des m\xE9dicaments",
    "acheter m\xE9dicament",
    "m\xE9dicaments",
    "medicaments"
  ],
  hospital: [
    "se soigner",
    "soigner",
    "\xEAtre soign\xE9",
    "me soigner"
  ],
  bank: [
    "retirer de l'argent",
    "retirer argent",
    "faire un retrait",
    "retirer"
  ],
  gas_station: [
    "faire le plein",
    "acheter de l'essence",
    "acheter essence",
    "mettre de l'essence",
    "mettre essence"
  ]
};

// ../p2/ConnecteoWEB/supabase/functions/search/parser/parseCategory.ts
function parseCategory(text) {
  for (const [category, aliases] of Object.entries(CATEGORIES)) {
    for (const alias of aliases) {
      if (text.includes(alias)) {
        return category;
      }
    }
  }
  for (const [category, actions] of Object.entries(ACTIONS)) {
    for (const action of actions) {
      if (text.includes(action)) {
        return category;
      }
    }
  }
  return null;
}

// ../p2/ConnecteoWEB/supabase/functions/search/parser/parseIntent.ts
function parseIntent(text) {
  for (const [intent, phrases] of Object.entries(INTENTS)) {
    for (const phrase of phrases) {
      if (text.includes(phrase)) {
        return intent;
      }
    }
  }
  return null;
}

// ../p2/ConnecteoWEB/supabase/functions/search/dictionaries/prepositions.ts
var LOCATION_PREPOSITION_PATTERNS = [
  /\ba proximite de\s+(.+)$/,
  /\baux alentours de\s+(.+)$/,
  /\bpres de\s+(.+)$/,
  /\bproche de\s+(.+)$/,
  /\bautour de\s+(.+)$/,
  /\bdans\s+(.+)$/,
  /\bsur\s+(.+)$/,
  /\ba\s+(.+)$/
];

// ../p2/ConnecteoWEB/supabase/functions/search/parser/parseLocation.ts
var STOPWORDS = /* @__PURE__ */ new Set([
  "a",
  "au",
  "aux",
  "dans",
  "sur",
  "de",
  "du",
  "des",
  "le",
  "la",
  "les",
  "l",
  "un",
  "une",
  "pour",
  "ou",
  "et",
  "en",
  "je",
  "veux",
  "cherche",
  "chercher",
  "trouver",
  "endroit",
  "lieu",
  "quartier",
  "pres",
  "proche",
  "proximite",
  "alentours",
  "autour",
  "me",
  "se",
  "y",
  "il",
  "existe",
  "est",
  "ya"
]);
function removeKnownTerms(text) {
  const terms = [];
  for (const list of Object.values(CATEGORIES)) terms.push(...list);
  for (const list of Object.values(ACTIONS)) terms.push(...list);
  for (const list of Object.values(INTENTS)) terms.push(...list);
  const sorted = terms.map((t) => normalizeText(t)).filter((t) => t.length > 0).sort((a, b) => b.length - a.length);
  let result = ` ${text} `;
  for (const term of sorted) {
    const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    result = result.replace(
      new RegExp(`(?<![a-z0-9])${escaped}(?![a-z0-9])`, "g"),
      " "
    );
  }
  return result;
}
function parseLocationFromPreposition(text) {
  for (const pattern of LOCATION_PREPOSITION_PATTERNS) {
    const match = text.match(pattern);
    if (match?.[1]) {
      return match[1].trim();
    }
  }
  return null;
}
function parseLocationFromRemainder(text) {
  const words = removeKnownTerms(text).replace(/[^a-z0-9'\- ]/g, " ").split(/[\s']+/).filter(Boolean);
  while (words.length > 0 && STOPWORDS.has(words[0])) words.shift();
  while (words.length > 0 && STOPWORDS.has(words[words.length - 1])) words.pop();
  const remainder = words.join(" ").trim();
  return remainder || null;
}
function parseLocation(text) {
  return parseLocationFromPreposition(text) ?? parseLocationFromRemainder(text);
}

// ../p2/ConnecteoWEB/supabase/functions/search/parser/parseRelation.ts
function parseRelation(text) {
  if (text.includes("pres de") || text.includes("proche de") || text.includes("a proximite de") || text.includes("aux alentours de") || text.includes("autour de")) {
    return "near";
  }
  return null;
}

// ../p2/ConnecteoWEB/supabase/functions/search/parser/parseQuery.ts
function determineType(category, intent, location) {
  if (intent) {
    return "intent";
  }
  if (category) {
    return "category";
  }
  if (location) {
    return "place";
  }
  return "unknown";
}
function parseQuery(text) {
  const category = parseCategory(text);
  const intent = parseIntent(text);
  const location = parseLocation(text);
  const relation = parseRelation(text);
  const type = determineType(
    category,
    intent,
    location
  );
  return {
    type,
    category,
    intent,
    location,
    relation
  };
}

// ../p2/ConnecteoWEB/supabase/functions/search/geocoding/geocode.ts
function env(name, fallback) {
  try {
    return globalThis.Deno?.env.get(name) ?? fallback;
  } catch {
    return fallback;
  }
}
var BASE_URL = () => env("GEOCODER_URL", "https://nominatim.openstreetmap.org");
var USER_AGENT = () => env("GEOCODER_USER_AGENT", "connecteo-search/1.0");
var COUNTRY_CODES = () => env("GEOCODER_COUNTRY_CODES", "mg");
var TIMEOUT_MS = () => Number(env("GEOCODER_TIMEOUT_MS", "3000"));
var CACHE = /* @__PURE__ */ new Map();
var CACHE_MAX = 500;
function matchesQuery(candidate, result) {
  const q = normalizeText(candidate);
  const names = [
    result.name,
    ...result.namedetails ? Object.values(result.namedetails) : []
  ].filter((n) => typeof n === "string").map((n) => normalizeText(n));
  if (names.some((n) => n === q || n.includes(q) || similarity(n, q) >= 0.8)) {
    return true;
  }
  const display = normalizeText(String(result.display_name ?? ""));
  return display.split(",").some((part) => similarity(part.trim(), q) >= 0.8);
}
async function searchNominatim(candidate, countryCodes) {
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
      return r.name || candidate;
    }
  }
  return null;
}
async function geocode(candidate) {
  const key = normalizeText(candidate);
  if (key.length < 2) {
    return null;
  }
  if (CACHE.has(key)) {
    return CACHE.get(key);
  }
  try {
    const priority = COUNTRY_CODES();
    let place = priority ? await searchNominatim(candidate, priority) : null;
    if (!place) {
      place = await searchNominatim(candidate);
    }
    if (CACHE.size >= CACHE_MAX) {
      CACHE.delete(CACHE.keys().next().value);
    }
    CACHE.set(key, place);
    return place;
  } catch (error) {
    console.error("geocode error:", error);
    return void 0;
  }
}

// ../p2/ConnecteoWEB/supabase/functions/search/_mock_entry.ts
async function analyze(query) {
  const normalizedQuery = normalizeText(query);
  const correctedQuery = correctTypos(normalizedQuery);
  const parsed = parseQuery(correctedQuery);
  let location = parsed.location;
  let locationVerified = null;
  let place = null;
  if (parsed.location) {
    const found = await geocode(parsed.location);
    if (found) {
      locationVerified = true;
      place = found;
    } else if (found === null) {
      locationVerified = false;
      location = null;
    }
  }
  return {
    query: query.trim(),
    type: determineType(parsed.category, parsed.intent, location),
    category: parsed.category,
    intent: parsed.intent,
    location,
    location_verified: locationVerified,
    place,
    relation: parsed.relation
  };
}
export {
  analyze
};
