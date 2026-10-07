export type SearchType =
  | "place"
  | "category"
  | "intent"
  | "unknown";

export type SearchResult = {
  query: string;
  type: SearchType;
  category: string | null;
  intent: string | null;
  location: string | null;
  // true = lieu confirmé par l'API, false = pas un lieu, null = API indisponible
  location_verified: boolean | null;
  place: string | null; // nom du lieu confirmé par l'API
  relation: string | null;
};
