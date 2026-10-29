/** Langues supportées : Malagasy, Français (défaut), English. */
export type Lang = "MG" | "FR" | "EN";

export interface SlideText {
  title: string;
  lead: string;
}

export interface StepText {
  title: string;
  text: string;
  /** Question pré-remplie quand on clique la box (le parseur comprend surtout le français). */
  example: string;
}

export interface GalleryCaption {
  title: string;
  place: string;
}

/** Dictionnaire complet d'une langue (référence = français). */
export interface Dict {
  nav: {
    home: string;
    discover: string;
    download: string;
    about: string;
    connect: string;
    account: string;
    signOut: string;
    signingOut: string;
    chooseLanguage: string;
    languageMenu: string;
    openMenu: string;
    mobileMenu: string;
  };
  hero: {
    slides: SlideText[];
    searchPlaceholder: string;
    searchLabel: string;
    searchSubmit: string;
    coverLabel: string;
    /** {q} = question tapée, {n} = numéro, {t} = titre */
    photoLabel: string;
    emptyQuery: string;
    searching: string;
    assistantDown: string;
    sosSent: string;
  };
  steps: {
    label: string;
    tryLabel: string;
    goLabel: string;
    items: StepText[];
  };
  gallery: {
    title: string;
    prev: string;
    next: string;
    carouselLabel: string;
    slides: GalleryCaption[];
  };
  downloadSection: {
    title: string;
    text: string;
    tags: string[];
    primary: string;
    secondary: string;
    platforms: string;
    phoneName: string;
    phoneSearch: string;
    phoneCardTitle: string;
    phoneCardSub: string;
    floatLeft: string;
    floatRight: string;
    phoneLabel: string;
  };
  footer: {
    backToTop: string;
    download: string;
    about: string;
    connect: string;
    secondaryNav: string;
    note: string;
  };
}

/**
 * Version partielle pour les traductions manuelles (MG / EN) :
 * chaque section — et chaque champ — est optionnel.
 * Tout ce qui manque retombe automatiquement sur le français.
 */
export interface PartialDict {
  nav?: Partial<Dict["nav"]>;
  hero?: {
    slides?: SlideText[];
    searchPlaceholder?: string;
    searchLabel?: string;
    searchSubmit?: string;
    coverLabel?: string;
    photoLabel?: string;
    emptyQuery?: string;
    searching?: string;
    assistantDown?: string;
    sosSent?: string;
  };
  steps?: {
    label?: string;
    tryLabel?: string;
    goLabel?: string;
    items?: StepText[];
  };
  gallery?: {
    title?: string;
    prev?: string;
    next?: string;
    carouselLabel?: string;
    slides?: GalleryCaption[];
  };
  downloadSection?: {
    title?: string;
    text?: string;
    tags?: string[];
    primary?: string;
    secondary?: string;
    platforms?: string;
    phoneName?: string;
    phoneSearch?: string;
    phoneCardTitle?: string;
    phoneCardSub?: string;
    floatLeft?: string;
    floatRight?: string;
    phoneLabel?: string;
  };
  footer?: Partial<Dict["footer"]>;
}
