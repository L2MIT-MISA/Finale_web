import type { PartialDict } from "./types";

/* ==================================================================
 * ENGLISH — complete translation (review welcome).
 * Everything is filled, so English never falls back to French.
 * Structure must mirror src/i18n/fr.ts.
 * ================================================================== */
export const en: PartialDict = {
  nav: {
    home: "Home",
    discover: "Discover",
    download: "Download",
    about: "About",
    connect: "Sign in",
    account: "My account",
    signOut: "Sign out",
    signingOut: "Signing out…",
    chooseLanguage: "Choose language",
    languageMenu: "Available languages",
    openMenu: "Open menu",
    mobileMenu: "Mobile menu",
  },
  hero: {
    slides: [
      {
        title: "Ask your question",
        lead: "Quickly find the right contact, place or procedure on the map of Madagascar.",
      },
      {
        title: "Travel safely and stay connected",
        lead: "Avenue of the Baobabs, Tsingy, Isalo… explore the wonders of Madagascar.",
      },
      {
        title: "Stay connected everywhere",
        lead: "Maps and useful info 24/7, even when the network is weak.",
      },
      {
        title: "Plan your itinerary",
        lead: "Routes, distances and points of interest for stress-free travel.",
      },
    ],
    searchPlaceholder: "Where, what are you looking for?",
    searchLabel: "Your question",
    searchSubmit: "Search",
    coverLabel: "Cover photos",
    photoLabel: "Photo {n}: {t}",
    emptyQuery: "Enter a place or a question.",
    searching: "Searching for “{q}”…",
    assistantDown: "The assistant is unavailable. Please try again in a moment.",
    sosSent: "Alert sent. Your contacts have been notified.",
  },
  steps: {
    label: "How it works",
    tryLabel: "try",
    goLabel: "go to section",
    items: [
      {
        title: "Ask your question",
        text: "Tell us what you're looking for: a service, a place, a procedure or local help.",
        example: "A pharmacy in Antananarivo",
      },
      {
        title: "Explore",
        text: "Explore Madagascar's destinations and connectivity.",
        example: "Explore Madagascar's destinations",
      },
      {
        title: "Download",
        text: "Use the app to stay connected 24/7 anywhere.",
        example: "Stay connected everywhere",
      },
    ],
  },
  gallery: {
    title: "Discover Madagascar",
    prev: "Previous image",
    next: "Next image",
    carouselLabel: "Photo carousel",
    slides: [
      { title: "Avenue of the Baobabs", place: "Menabe Region" },
      { title: "Isalo Window", place: "Isalo National Park" },
      { title: "The Tsingy", place: "Bemaraha" },
      { title: "Stone forest", place: "Between two limestone cliffs" },
      { title: "Masoala", place: "National park, northeast" },
      { title: "Tropical forests", place: "Rivers and mossy rocks" },
    ],
  },
  downloadSection: {
    title: "Your answers go with you everywhere.",
    text: "Download the free app and access essential services 24/7 across Madagascar, even when your connection is limited.",
    tags: ["Free", "Offline", "24/7"],
    primary: "Download the app",
    secondary: "See destinations",
    platforms: "Android • iOS • HarmonyOS — no account, no connection required",
    phoneName: "Connectéo",
    phoneSearch: "Nearby pharmacy",
    phoneCardTitle: "Health center",
    phoneCardSub: "1.2 km away · Open",
    floatLeft: "Local data",
    floatRight: "Offline access",
    phoneLabel: "Preview of the Connectéo app",
  },
  footer: {
    backToTop: "Connectéo — back to top",
    download: "Download",
    about: "About",
    connect: "Sign in",
    secondaryNav: "Secondary navigation",
    note: "Connectéo — the map of Madagascar, even offline.",
  },
};
