import { LOCATION_PREPOSITION_PATTERNS } from "../dictionaries/prepositions.ts";
import { CATEGORIES } from "../dictionaries/categories.ts";
import { ACTIONS } from "../dictionaries/actions.ts";
import { INTENTS } from "../dictionaries/intents.ts";
import { normalizeText } from "../normalize/normalizeText.ts";

// Mots "vides" qui ne font jamais partie d'un nom de lieu
const STOPWORDS = new Set([
  "a", "au", "aux", "dans", "sur", "de", "du", "des", "le", "la", "les", "l",
  "un", "une", "pour", "ou", "et", "en", "je", "veux", "cherche", "chercher",
  "trouver", "endroit", "lieu", "quartier", "pres", "proche", "proximite",
  "alentours", "autour", "me", "se", "y", "il", "existe", "est", "ya"
]);

// Retire de la requête tout ce qui est catégorie / action / intention
// (les plus longues expressions d'abord pour éviter les retraits partiels)
function removeKnownTerms(text: string): string {
  const terms: string[] = [];

  for (const list of Object.values(CATEGORIES)) terms.push(...list);
  for (const list of Object.values(ACTIONS)) terms.push(...list);
  for (const list of Object.values(INTENTS)) terms.push(...list);

  const sorted = terms
    .map((t) => normalizeText(t))
    .filter((t) => t.length > 0)
    .sort((a, b) => b.length - a.length);

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

// Cas 1 : lieu introduit par une préposition ("restaurant à analakely")
function parseLocationFromPreposition(text: string): string | null {
  for (const pattern of LOCATION_PREPOSITION_PATTERNS) {
    const match = text.match(pattern);

    if (match?.[1]) {
      return match[1].trim();
    }
  }

  return null;
}

// Cas 2 : pas de préposition ("analakely", "restaurant analakely")
// → ce qui reste après avoir retiré catégories, actions et mots vides
function parseLocationFromRemainder(text: string): string | null {
  const words = removeKnownTerms(text)
    .replace(/[^a-z0-9'\- ]/g, " ")
    .split(/[\s']+/)
    .filter(Boolean);

  // On ne retire les mots vides qu'aux extrémités : ceux du milieu font
  // partie du nom ("cap de bonne esperance").
  while (words.length > 0 && STOPWORDS.has(words[0])) words.shift();
  while (words.length > 0 && STOPWORDS.has(words[words.length - 1])) words.pop();

  const remainder = words.join(" ").trim();
  return remainder || null;
}

export function parseLocation(text: string): string | null {
  return parseLocationFromPreposition(text) ?? parseLocationFromRemainder(text);
}
