import { supabase } from "./supabase";
import type { ParsedSearch } from "../pages/Search/searchTypes";

const FALLBACK_CATEGORIES: Array<[string, string[]]> = [
  ["restaurant", ["restaurant", "resto", "manger"]],
  ["hotel", ["hotel", "hebergement", "dormir"]],
  ["pharmacy", ["pharmacie", "medicament"]],
  ["hospital", ["hopital", "clinique", "soigner"]],
  ["bank", ["banque", "distributeur", "retirer"]],
  ["gas_station", ["station service", "station-service", "essence", "plein"]],
];

function normalize(text: string) {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

function parseLocally(query: string): ParsedSearch {
  const normalized = normalize(query);
  const category = FALLBACK_CATEGORIES.find(([, aliases]) => aliases.some((alias) => normalized.includes(alias)))?.[0] ?? null;
  const locationMatch = normalized.match(/(?:\ba|\bdans|\bsur|\bpres de|\bproche de)\s+(.+)$/);
  return {
    query,
    type: category ? "category" : locationMatch ? "place" : "unknown",
    category,
    intent: null,
    location: locationMatch?.[1]?.trim() ?? null,
    relation: null,
  };
}

// Meme logique que la page d'accueil : fonction serveur d'abord, analyse locale en secours
export async function parseSearchQuery(query: string): Promise<ParsedSearch> {
  const { data, error } = await supabase.functions.invoke<ParsedSearch>("search", { body: { query } });
  if (error || !data) return parseLocally(query);
  return { ...data, query };
}
