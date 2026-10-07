import type { Lieu } from "../../pages/Search/searchTypes";

export const fmt1 = (v: number) => v.toFixed(1).replace(".", ",");
export const distance = (m: number) => (m >= 1000 ? `${fmt1(m / 1000)} km` : `${Math.round(m)} m`);
export const plur = (n: number, un: string, plusieurs: string) => `${n} ${n > 1 ? plusieurs : un}`;

export function hueDe(texte: string) {
  return [...texte].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7) % 360;
}

export function typeDe(l: Lieu) {
  const brut = l.categorie ?? l.niveau;
  if (!brut) return null;
  const fin = brut.split(".").pop() ?? brut;
  const t = fin.replace(/_/g, " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
}

export function libellePrecision(l: Lieu) {
  return l.approximatif ? "Approximative (centre de la zone)" : "Précise";
}

export function urlHttp(u?: string | null) {
  return u && /^https?:\/\//i.test(u) ? u : null;
}
