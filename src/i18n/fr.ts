import type { Dict } from "./types";

/** Français — langue de référence (dictionnaire complet). */
export const fr: Dict = {
  nav: {
    home: "Accueil",
    discover: "Découvrir",
    download: "Télécharger",
    about: "À propos",
    connect: "S'y connecter",
    account: "Mon compte",
    signOut: "Se déconnecter",
    signingOut: "Déconnexion…",
    chooseLanguage: "Choisir la langue",
    languageMenu: "Langues disponibles",
    openMenu: "Ouvrir le menu",
    mobileMenu: "Menu mobile",
  },
  hero: {
    slides: [
      {
        title: "Posez votre question",
        lead: "Trouvez rapidement le bon contact, le bon lieu ou la bonne démarche sur la carte de Madagascar.",
      },
      {
        title: "Voyagez en toute sécurité et toujours connecté",
        lead: "Allée des Baobabs, Tsingy, Isalo… explorez les merveilles de Madagascar.",
      },
      {
        title: "Restez connecté partout",
        lead: "Cartes et infos utiles 24h/24, même quand le réseau faiblit.",
      },
      {
        title: "Préparez votre itinéraire",
        lead: "Itinéraires, distances et points d'intérêt pour voyager serein.",
      },
    ],
    searchPlaceholder: "Où, que cherchez-vous ?",
    searchLabel: "Votre question",
    searchSubmit: "Rechercher",
    coverLabel: "Photos de couverture",
    photoLabel: "Photo {n} : {t}",
    emptyQuery: "Saisissez un lieu ou une question.",
    searching: "Recherche de « {q} »…",
    assistantDown: "L'assistant est indisponible. Réessayez dans un instant.",
    sosSent: "Alerte envoyée. Vos contacts ont été prévenus.",
  },
  steps: {
    label: "Comment ça marche",
    tryLabel: "essayer",
    goLabel: "aller à la section",
    items: [
      {
        title: "Posez votre question",
        text: "Dites-nous ce que vous cherchez : un service, un lieu, une démarche ou une aide locale.",
        example: "Une pharmacie à Antananarivo",
      },
      {
        title: "Explorer",
        text: "Explorer les destinations et la connectivité de Madagascar.",
        example: "Explorer les destinations de Madagascar",
      },
      {
        title: "Télécharger",
        text: "Utiliser l'application pour rester connecté 24h/24 n'importe où.",
        example: "Rester connecté partout",
      },
    ],
  },
  gallery: {
    title: "Découvrez Madagascar",
    prev: "Image précédente",
    next: "Image suivante",
    carouselLabel: "Carrousel de photos",
    slides: [
      { title: "Allée des baobabs", place: "Région de Menabe" },
      { title: "La Fenêtre d'Isalo", place: "Parc national de l'Isalo" },
      { title: "Les Tsingy", place: "Bemaraha" },
      { title: "Forêt de pierre", place: "Entre deux falaises de calcaire" },
      { title: "Masoala", place: "Parc national, nord-est" },
      { title: "Forêts tropicales", place: "Rivières et rochers moussus" },
    ],
  },
  downloadSection: {
    title: "Vos réponses vous accompagnent partout.",
    text: "Téléchargez l'application gratuite et accédez aux services essentiels, 24h/24 et partout à Madagascar, même lorsque votre connexion est limitée.",
    tags: ["Gratuite", "Hors ligne", "24h/24"],
    primary: "Télécharger l'application",
    secondary: "Voir les destinations",
    platforms: "Android • iOS • HarmonyOS — sans compte, sans connexion requise",
    phoneName: "Connectéo",
    phoneSearch: "Pharmacie à proximité",
    phoneCardTitle: "Centre de santé",
    phoneCardSub: "À 1,2 km · Ouvert",
    floatLeft: "Données locales",
    floatRight: "Accès hors ligne",
    phoneLabel: "Aperçu de l'application Connectéo",
  },
  footer: {
    backToTop: "Connectéo — retour en haut",
    download: "Télécharger",
    about: "À propos",
    connect: "Se connecter",
    secondaryNav: "Navigation secondaire",
    note: "Connectéo — la carte de Madagascar, même hors connexion.",
  },
};
