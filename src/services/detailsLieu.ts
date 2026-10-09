import type {
  Connectivite,
  ConnectiviteIA,
  OperateurConnectivite,
  Securite,
  SecuriteIA,
  Techno,
  Transport,
  TransportIA,
} from "../pages/Search/searchTypes";

// Normalisation des blocs « sécurité », « transport » et « connectivité » d'un lieu.
// Chaque fonction renvoie null quand il n'y a rien à afficher : la carte correspondante est alors masquée.

const TECHS: Techno[] = ["2G", "3G", "4G", "5G"];
const ORDRE_OPERATEURS = ["Orange", "Telma", "Airtel"];

export function securiteDe(s?: SecuriteIA | null): Securite | null {
  if (!s) return null;
  const details = (s.details ?? []).filter((d) => d && d.label && d.valeur);
  if (!s.niveau && !s.resume && details.length === 0) return null;
  const resume = s.resume ?? (details.slice(0, 2).map((d) => `${d.label} : ${d.valeur}`).join(". ") || null);
  return { niveau: s.niveau ?? null, ton: s.ton ?? null, resume, details };
}

const minutes = (n?: number | null) => (typeof n === "number" && Number.isFinite(n) ? `${Math.round(n)} min` : null);

export function transportDe(t?: TransportIA | null): Transport | null {
  if (!t) return null;
  const options = (t.options ?? [])
    .filter((o) => o && o.mode)
    .map((o) => ({ mode: o.mode, detail: o.detail ?? null, duree: minutes(o.duree_min) }));
  if (options.length === 0 && !t.resume) return null;
  const resume = t.resume
    ? [t.resume]
    : options.slice(0, 2).map((o) => [o.mode, o.detail].filter(Boolean).join(" : ") + (o.duree ? ` (${o.duree})` : ""));
  return { resume, options };
}

// Le référentiel nomme TELMA ou YAS : même opérateur.
function nomOperateur(cle: string) {
  const c = cle.toUpperCase();
  if (c.includes("TELMA") || c.includes("YAS")) return "Telma";
  if (c.includes("ORANGE")) return "Orange";
  if (c.includes("AIRTEL")) return "Airtel";
  return cle.charAt(0).toUpperCase() + cle.slice(1).toLowerCase();
}

export function connectiviteDe(c?: ConnectiviteIA | null): Connectivite | null {
  const brut = Object.entries(c?.operators ?? {});
  if (brut.length === 0) return null;

  const parNom = new Map<string, OperateurConnectivite>();
  for (const [cle, op] of brut) {
    const nom = nomOperateur(cle);
    const cible = parNom.get(nom) ?? { nom, techs: { "2G": false, "3G": false, "4G": false, "5G": false }, tour: null };
    for (const t of TECHS) {
      if (op.technologies?.[t] === true || op.technologies_actives?.includes(t)) cible.techs[t] = true;
    }
    for (const tour of Object.values(op.nearest_towers_by_technology ?? {})) {
      const d = tour?.distance_meters;
      if (typeof d !== "number" || !Number.isFinite(d)) continue;
      if (!cible.tour || d < cible.tour.distance) cible.tour = { nom: tour?.name || "Site", distance: d };
    }
    parNom.set(nom, cible);
  }

  const rang = (n: string) => (ORDRE_OPERATEURS.includes(n) ? ORDRE_OPERATEURS.indexOf(n) : ORDRE_OPERATEURS.length);
  const operateurs = [...parNom.values()].sort((a, b) => rang(a.nom) - rang(b.nom) || a.nom.localeCompare(b.nom));

  const meilleure = (o: OperateurConnectivite) => TECHS.reduce((m, t, i) => (o.techs[t] ? i + 1 : m), 0);
  const best = Math.max(...operateurs.map(meilleure));
  const gen = best >= 4 ? "5G" : best === 3 ? "4G" : best === 2 ? "3G" : best === 1 ? "2G" : null;
  const label =
    gen === "5G" ? "5G disponible" : gen === "4G" ? "4G disponible" : gen === "3G" ? "3G maximum" : gen === "2G" ? "2G seulement" : "Aucun réseau";
  const noms = operateurs.filter((o) => meilleure(o) === best).map((o) => o.nom).join(", ");
  return { operateurs, label, brief: gen ? `${noms} en ${gen}.` : "Aucune couverture connue.", ok: best >= 3 };
}
