import { CATEGORIES } from "../dictionaries/categories.ts";
import { INTENTS } from "../dictionaries/intents.ts";
import { similarity } from "./similarity.ts";

const THRESHOLD = 0.75;

// Les mots courts (< 6 lettres) ne sont corrigés que s'ils sont exacts :
// sinon de vrais noms de lieux ("reste", "stack"...) seraient transformés
// en "resto", "snack", etc.
const MIN_LENGTH_FOR_FUZZY = 6;

function getKnownTerms(): string[] {
  const terms = new Set<string>();

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

function findCorrection(word: string, terms: string[]): string | null {
  if (word.length < MIN_LENGTH_FOR_FUZZY) {
    return null;
  }

  let bestMatch: string | null = null;
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

export function correctTypos(text: string): string {
  const terms = getKnownTerms();

  return text
    .split(" ")
    .map((word) => findCorrection(word, terms) ?? word)
    .join(" ");
}