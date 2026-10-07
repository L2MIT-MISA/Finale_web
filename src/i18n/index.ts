import { en } from "./en";
import { fr } from "./fr";
import { mg } from "./mg";
import type { Dict, Lang, PartialDict } from "./types";

export type { Dict, Lang };
export { fr };

export const LANGS: Array<{ code: Lang; label: string }> = [
  { code: "MG", label: "Malagasy" },
  { code: "FR", label: "Français" },
  { code: "EN", label: "English" },
];

const PARTIALS: Record<Lang, PartialDict> = { MG: mg, FR: {}, EN: en };

const STORAGE_KEY = "connecteo-lang";

export function getInitialLang(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "MG" || saved === "EN" || saved === "FR") return saved;
  } catch {
    /* stockage indisponible */
  }
  return "FR";
}

export function persistLang(lang: Lang) {
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* stockage indisponible */
  }
}

/** Fusionne une traduction partielle sur le français (section par section). */
export function getDict(lang: Lang): Dict {
  if (lang === "FR") return fr;
  const p = PARTIALS[lang];
  return {
    nav: { ...fr.nav, ...p.nav },
    hero: {
      searchPlaceholder: p.hero?.searchPlaceholder ?? fr.hero.searchPlaceholder,
      searchLabel: p.hero?.searchLabel ?? fr.hero.searchLabel,
      searchSubmit: p.hero?.searchSubmit ?? fr.hero.searchSubmit,
      coverLabel: p.hero?.coverLabel ?? fr.hero.coverLabel,
      photoLabel: p.hero?.photoLabel ?? fr.hero.photoLabel,
      emptyQuery: p.hero?.emptyQuery ?? fr.hero.emptyQuery,
      searching: p.hero?.searching ?? fr.hero.searching,
      assistantDown: p.hero?.assistantDown ?? fr.hero.assistantDown,
      sosSent: p.hero?.sosSent ?? fr.hero.sosSent,
      slides: p.hero?.slides ?? fr.hero.slides,
    },
    steps: {
      label: p.steps?.label ?? fr.steps.label,
      tryLabel: p.steps?.tryLabel ?? fr.steps.tryLabel,
      goLabel: p.steps?.goLabel ?? fr.steps.goLabel,
      items: p.steps?.items ?? fr.steps.items,
    },
    gallery: {
      title: p.gallery?.title ?? fr.gallery.title,
      prev: p.gallery?.prev ?? fr.gallery.prev,
      next: p.gallery?.next ?? fr.gallery.next,
      carouselLabel: p.gallery?.carouselLabel ?? fr.gallery.carouselLabel,
      slides: p.gallery?.slides ?? fr.gallery.slides,
    },
    downloadSection: {
      title: p.downloadSection?.title ?? fr.downloadSection.title,
      text: p.downloadSection?.text ?? fr.downloadSection.text,
      tags: p.downloadSection?.tags ?? fr.downloadSection.tags,
      primary: p.downloadSection?.primary ?? fr.downloadSection.primary,
      secondary: p.downloadSection?.secondary ?? fr.downloadSection.secondary,
      platforms: p.downloadSection?.platforms ?? fr.downloadSection.platforms,
      phoneName: p.downloadSection?.phoneName ?? fr.downloadSection.phoneName,
      phoneSearch: p.downloadSection?.phoneSearch ?? fr.downloadSection.phoneSearch,
      phoneCardTitle: p.downloadSection?.phoneCardTitle ?? fr.downloadSection.phoneCardTitle,
      phoneCardSub: p.downloadSection?.phoneCardSub ?? fr.downloadSection.phoneCardSub,
      floatLeft: p.downloadSection?.floatLeft ?? fr.downloadSection.floatLeft,
      floatRight: p.downloadSection?.floatRight ?? fr.downloadSection.floatRight,
      phoneLabel: p.downloadSection?.phoneLabel ?? fr.downloadSection.phoneLabel,
    },
    footer: { ...fr.footer, ...p.footer },
  };
}

/** Remplace {q} / {n} / {t} dans les gabarits de message. */
export function fill(template: string, vars: Record<string, string>): string {
  let out = template;
  for (const [key, value] of Object.entries(vars)) {
    out = out.split(`{${key}}`).join(value);
  }
  return out;
}
