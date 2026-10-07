import type { Image, Lieu, LieuIA, ReponseIA } from "../pages/Search/searchTypes";
import { connectiviteDe, securiteDe, transportDe } from "./detailsLieu";

const AI_URL = import.meta.env.VITE_AI_API_URL || "http://127.0.0.1:8000";

export async function demanderIA(texte: string, signal?: AbortSignal): Promise<ReponseIA> {
  const response = await fetch(`${AI_URL}/assistant`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texte }),
    signal,
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return (await response.json()) as ReponseIA;
}

const urlOk = (s: string) => /^(https?:\/\/|data:image\/|\/)/i.test(s);

// Le référentiel renvoie des noms en MAJUSCULES : on les remet en casse titre.
function aTitre(s?: string | null) {
  if (!s) return "";
  if (s !== s.toUpperCase()) return s;
  return s.toLowerCase().replace(/(^|[\s'’-])(\p{L})/gu, (_, sep: string, c: string) => sep + c.toUpperCase());
}

function texteAvis(a: unknown): string | null {
  if (typeof a === "string") return a;
  if (a && typeof a === "object") {
    const o = a as Record<string, unknown>;
    const t = o.texte ?? o.text ?? o.commentaire;
    return typeof t === "string" ? t : null;
  }
  return null;
}

function normaliser(l: LieuIA, index: number, approximatif: boolean): Lieu | null {
  const c = l.coordonnees;
  if (!c || !Number.isFinite(c.latitude) || !Number.isFinite(c.longitude)) return null;

  const images: Image[] = (l.images ?? [])
    .map((i) => (typeof i === "string" ? { url: i, legende: null } : { url: i.url, legende: i.legende ?? null }))
    .filter((i) => typeof i.url === "string" && urlOk(i.url));
  if (l.image_source && urlOk(l.image_source) && !images.some((i) => i.url === l.image_source)) {
    images.push({ url: l.image_source, legende: null });
  }

  const avisListe = Array.isArray(l.avis) ? l.avis.map(texteAvis).filter((t): t is string => !!t) : [];
  const district = aTitre(l.district);
  const region = aTitre(l.region);

  return {
    id: `${l.code_officiel ?? l.nom}-${index}`,
    nom: aTitre(l.nom),
    sousTitre: [district, region].filter(Boolean).join(", "),
    niveau: l.niveau ?? null,
    categorie: l.categorie ?? null,
    region: region || null,
    district: district || null,
    codeOfficiel: l.code_officiel ?? null,
    description: l.description ?? null,
    position: { lat: c.latitude, lng: c.longitude },
    precision: c.precision ?? null,
    approximatif: approximatif || /repli|approx/i.test(c.precision ?? ""),
    noteGoogle: typeof l.note_google === "number" ? l.note_google : null,
    avis: avisListe,
    nbAvis: typeof l.avis === "number" ? l.avis : null,
    sourcesCitees: l.sources_citees ?? [],
    images,
    securite: securiteDe(l.securite),
    transport: transportDe(l.transport),
    connectivite: connectiviteDe(l.connectivite ?? l.connectivityDetails),
  };
}

// lieux (triés par pertinence) puis lieux_approximative sans les doublons
export function lieuxDe(rep: ReponseIA): Lieu[] {
  const principaux = [...(rep.lieux ?? [])].sort((a, b) => (b.pertinence ?? 0) - (a.pertinence ?? 0));
  const vus = new Set<string>();
  const sortie: Lieu[] = [];
  const ajouter = (liste: LieuIA[], approx: boolean) => {
    for (const l of liste) {
      const cle = `${l.code_officiel ?? ""}|${l.nom}|${l.coordonnees?.latitude}|${l.coordonnees?.longitude}`;
      if (vus.has(cle)) continue;
      vus.add(cle);
      const lieu = normaliser(l, sortie.length, approx);
      if (lieu) sortie.push(lieu);
    }
  };
  ajouter(principaux, false);
  ajouter(rep.lieux_approximative ?? [], true);
  return sortie;
}

// clarification / urgence / erreur : formes non figées, on cherche un texte lisible
function texteDe(v: unknown): string | null {
  if (!v) return null;
  if (typeof v === "string") return v;
  if (typeof v === "object") {
    const o = v as Record<string, unknown>;
    for (const k of ["message", "texte", "question"]) if (typeof o[k] === "string") return o[k] as string;
  }
  return null;
}

export function messagesDe(rep: ReponseIA): string[] {
  const liste = [texteDe(rep.urgence), texteDe(rep.clarification), rep.reponse?.texte ?? null].filter(
    (t): t is string => !!t,
  );
  if (liste.length === 0) {
    const erreur = texteDe(rep.erreur);
    liste.push(erreur ? `L'assistant a rencontré un problème : ${erreur}` : "Je n'ai pas trouvé de réponse pour cette demande.");
  }
  return liste;
}
