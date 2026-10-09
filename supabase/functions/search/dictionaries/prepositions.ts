export const LOCATION_PREPOSITIONS = [
  "a proximite de",
  "aux alentours de",
  "pres de",
  "proche de",
  "autour de",
  "dans",
  "sur",
  "a"
];

// ⚠️ L'ordre compte : les expressions longues doivent passer avant "a",
// sinon "hotel a proximite de analakely" donnerait "proximite de analakely".
export const LOCATION_PREPOSITION_PATTERNS = [
  /\ba proximite de\s+(.+)$/,
  /\baux alentours de\s+(.+)$/,
  /\bpres de\s+(.+)$/,
  /\bproche de\s+(.+)$/,
  /\bautour de\s+(.+)$/,
  /\bdans\s+(.+)$/,
  /\bsur\s+(.+)$/,
  /\ba\s+(.+)$/
];
