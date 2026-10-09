import { parseCategory } from "./parseCategory.ts";
import { parseIntent } from "./parseIntent.ts";
import { parseLocation } from "./parseLocation.ts";
import { parseRelation } from "./parseRelation.ts";
import type { SearchType } from "../types/search.ts";

export function determineType(
  category: string | null,
  intent: string | null,
  location: string | null
): SearchType {
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

export function parseQuery(text: string) {
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