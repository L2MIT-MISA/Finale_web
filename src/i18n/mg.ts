import type { PartialDict } from "./types";

/* ==================================================================
 * MALAGASY — dikanteny voalohany (BROUILLON À RELIRE par un locuteur
 * natif avant mise en production). Tout est rempli pour que le
 * malagasy ne retombe jamais sur le français ; corrigez librement,
 * section par section. Structure identique à src/i18n/fr.ts.
 * ================================================================== */
export const mg: PartialDict = {
  nav: {
    home: "Fandraisana",
    discover: "Fantaro",
    download: "Misintona",
    about: "Mombamomba",
    connect: "Midira",
    account: "Kaontiko",
    signOut: "Hivoaka",
    signingOut: "Mivoaka…",
    chooseLanguage: "Misafidiana fiteny",
    languageMenu: "Fiteny azo isafidianana",
    openMenu: "Sokafy ny menu",
    mobileMenu: "Menu",
  },
  hero: {
    slides: [
      {
        title: "Apetraho ny fanontanianao",
        lead: "Hitadiavo haingana ny olona, ny toerana na ny dingana mety aminao eto Madagasikara.",
      },
      {
        title: "Mandehana am-pilaminana ary mifandray foana",
        lead: "Allée des Baobabs, Tsingy, Isalo… fantaro ny zava-mahatalanjona eto Madagasikara.",
      },
      {
        title: "Mijanòna mifandray na aiza na aiza",
        lead: "Sari-tany sy fampahalalana ilaina 24/24, na dia malemy aza ny tambajotra.",
      },
      {
        title: "Omano ny dianao",
        lead: "Lalana, halavirana ary toerana mahaliana mba handehanana am-pitoniana.",
      },
    ],
    searchPlaceholder: "Aiza, inona no tadiavinao ?",
    searchLabel: "Ny fanontanianao",
    searchSubmit: "Tadiavo",
    coverLabel: "Sary fototra",
    photoLabel: "Sary {n} : {t}",
    emptyQuery: "Ampidiro toerana na fanontaniana.",
    searching: "Mitady « {q} »…",
    assistantDown: "Tsy afaka vonjimaika ny mpanampy. Andramo indray afaka kelikely.",
    sosSent: "Lasa ny fanairana. Efa nampandrenesina ny olon-nao.",
  },
  steps: {
    label: "Ahoana ny fandehany",
    tryLabel: "andramo",
    goLabel: "mandeha any amin'ny fizarana",
    items: [
      {
        title: "Apetraho ny fanontanianao",
        text: "Lazao anay izay tadiavinao : tolotra, toerana, dingana na fanampiana eo an-toerana.",
        example: "Farmasia eto Antananarivo",
      },
      {
        title: "Diniho",
        text: "Diniho ny toerana sy ny tambajotra eto Madagasikara.",
        example: "Diniho ny toerana eto Madagasikara",
      },
      {
        title: "Sintomy",
        text: "Ampiasao ny fampiharana mba hijanonana mifandray 24 ora/24 na aiza na aiza.",
        example: "Hijanona mifandray hatrany",
      },
    ],
  },
  gallery: {
    title: "Fantaro i Madagasikara",
    prev: "Sary teo aloha",
    next: "Sary manaraka",
    carouselLabel: "Andian-tsarin'ny toerana",
    slides: [
      { title: "Allée des baobabs", place: "Faritra Menabe" },
      { title: "La Fenêtre d'Isalo", place: "Valan-javaboarin'i Isalo" },
      { title: "Les Tsingy", place: "Bemaraha" },
      { title: "Forêt de pierre", place: "Hantsana vatosokay" },
      { title: "Masoala", place: "Valan-javaboary, avaratra-atsinanana" },
      { title: "Forêts tropicales", place: "Renirano sy vatolampy maitso" },
    ],
  },
  downloadSection: {
    title: "Manaraka anao na aiza na aiza ny valiny.",
    text: "Sintomy maimaimpoana ny fampiharana ary midira amin'ny tolotra ilaina, 24 ora/24 manerana an'i Madagasikara, na dia voafetra aza ny fifandraisanao.",
    tags: ["Maimaimpoana", "Tsy mila internet", "24/24"],
    primary: "Sintomy ny fampiharana",
    secondary: "Hijery ny toerana",
    platforms: "Android • iOS • HarmonyOS — tsy mila kaonty, tsy mila internet",
    phoneName: "Connectéo",
    phoneSearch: "Farmasia akaiky",
    phoneCardTitle: "Foibe ara-pahasalamana",
    phoneCardSub: "1,2 km · Misokatra",
    floatLeft: "Angona eo an-toerana",
    floatRight: "Miasa ivelan'ny internet",
    phoneLabel: "Topimaso ny fampiharana Connectéo",
  },
  footer: {
    backToTop: "Connectéo — hiverina eny ambony",
    download: "Misintona",
    about: "Mombamomba",
    connect: "Midira",
    secondaryNav: "Fitetezana fanampiny",
    note: "Connectéo — ny saritanin'i Madagasikara, na dia ivelan'ny internet aza.",
  },
};
