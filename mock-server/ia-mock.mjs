// Simule l'IA : mêmes champs que le JSON réel (voir 20261005-211430-marary-78f7.json)
// + `images` par lieu (photos ajoutées aux données Google).
// Comportement repris de Main.dc.html : toute requête renvoie 15 lieux de démo.

const norm = (t) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();

const QUARTIERS = {
  Analakely: { lat: -18.9065, lng: 47.5233, note: [4.4, 4.1] },
  Isoraka: { lat: -18.915, lng: 47.52, note: [4.6, 4.3] },
  Ankorondrano: { lat: -18.88, lng: 47.533, note: [4.5, null] },
  Behoririka: { lat: -18.899, lng: 47.526, note: [4.0, 3.8] },
  Ankatso: { lat: -18.917, lng: 47.55, note: [4.2, null] },
  Itaosy: { lat: -18.948, lng: 47.47, note: [null, null] },
  Mahitsy: { lat: -18.78, lng: 47.35, note: [3.9, null] },
  Ivato: { lat: -18.797, lng: 47.479, note: [4.1, 3.7] },
};

const TYPES = [
  ["Hôtel", "Analakely"], ["Résidence", "Isoraka"], ["Auberge", "Ankorondrano"], ["Maison d'hôtes", "Behoririka"],
  ["Gîte", "Ankatso"], ["Hôtel", "Itaosy"], ["Auberge", "Mahitsy"], ["Résidence", "Ivato"],
  ["Hôtel", "Isoraka"], ["Maison d'hôtes", "Analakely"], ["Gîte", "Ankorondrano"], ["Résidence", "Ankatso"],
  ["Hôtel", "Ivato"], ["Auberge", "Itaosy"], ["Maison d'hôtes", "Mahitsy"],
];
const CATEGORIES = { Hôtel: "accommodation.hotel", Résidence: "accommodation.apartment", Auberge: "accommodation.guest_house", "Maison d'hôtes": "accommodation.guest_house", Gîte: "accommodation.chalet" };
const NB_PHOTOS = [3, 0, 4, 1, 5, 2, 3, 0, 4, 1, 3, 2, 5, 0, 3];
const LEGENDES = ["Façade", "Chambre", "Salle commune", "Entrée", "Vue depuis le lieu"];
const AVIS = ["Accueil chaleureux, chambre propre.", "Bien situé, un peu bruyant le soir.", "Bon rapport qualité-prix."];

const maintenant = () => new Date().toISOString();

// Données de démo pour les cartes Sécurité / Transport / Connectivité de la fiche.
// `connectivite` reprend le format `connectivityDetails` du backend (datafusion.py).
function blocsDetails(i) {
  const tour = (name, d) => ({ name, distance_meters: d });
  const op = (techs, t) => ({
    technologies: Object.fromEntries(["2G", "3G", "4G", "5G"].map((g) => [g, techs.includes(g)])),
    technologies_actives: techs,
    nearest_towers_by_technology: Object.fromEntries(["2G", "3G", "4G", "5G"].map((g) => [g, techs.includes(g) ? t : null])),
  });
  const d = 120 + ((i * 97) % 380);
  return {
    securite: i % 5 === 4 ? null : {
      niveau: i % 3 === 2 ? "À surveiller le soir" : "Quartier calme",
      ton: i % 3 === 2 ? "warn" : "ok",
      resume: `Police à ${400 + i * 40} m. Affluence le soir : ${i % 3 === 2 ? "élevée" : "faible"}.`,
      details: [
        { label: "Éclairage public", valeur: "Oui, jusqu'à 22 h" },
        { label: "Poste de police", valeur: `À ${400 + i * 40} m` },
        { label: "Affluence le soir", valeur: i % 3 === 2 ? "Élevée" : "Faible" },
        { label: "Retour de nuit", valeur: i % 3 === 2 ? "Taxi conseillé" : "Sans souci" },
      ],
    },
    transport: i % 6 === 5 ? null : {
      options: [
        { mode: "Taxi-be", detail: `Arrêt à ${d} m du lieu`, duree_min: 18 },
        { mode: "Taxi", detail: "Course depuis le centre-ville", duree_min: 11 },
        { mode: "Taxi moto", detail: "Depuis le centre-ville", duree_min: 9 },
        { mode: "À pied", detail: "Depuis l'arrêt de taxi-be", duree_min: 3 },
      ],
    },
    connectivite: i % 7 === 6 ? null : {
      available: true,
      operators: {
        ORANGE: op(["2G", "3G", "4G", "5G"], tour("Orange 3", d + 140)),
        TELMA: op(["2G", "3G", "4G"], tour("Telma 4", d + 240)),
        AIRTEL: op(["2G", "3G", "4G"], tour("Airtel 5", d + 340)),
      },
    },
  };
}

function lieuxDemo(base) {
  const sources = [];
  const lieux = TYPES.map(([type, quartier], i) => {
    const q = QUARTIERS[quartier];
    const note = q.note[i % 2];
    const nom = `${type} ${quartier} (démo)`;
    const images = Array.from({ length: NB_PHOTOS[i] }, (_, k) => ({
      url: `${base}/mock-images/${i}-${k}.svg`,
      legende: LEGENDES[k % LEGENDES.length],
    }));
    const ref = note ? `R${sources.length + 1}` : null;
    if (ref) {
      sources.push({
        reference: ref, origine: "google", titre: `Fiche Google : ${nom}`,
        url: `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(nom + " Antananarivo")}`,
        fichier: null,
      });
    }
    return {
      nom,
      niveau: "etablissement",
      code_officiel: null,
      region: "Analamanga",
      district: quartier,
      produit: null,
      categorie: CATEGORIES[type],
      description: `${type} du quartier ${quartier}, à Antananarivo (données de démonstration).`,
      coordonnees: {
        latitude: Number((q.lat + (((i * 7) % 9) - 4) * 0.0012).toFixed(5)),
        longitude: Number((q.lng + (((i * 5) % 7) - 3) * 0.0015).toFixed(5)),
        precision: "exacte",
      },
      note_google: note,
      avis: note ? AVIS.slice(0, 1 + (i % 3)) : null,
      sources_citees: ref ? [ref] : null,
      mots_cles: [type.toLowerCase(), quartier.toLowerCase()],
      pertinence: Number((0.95 - i * 0.02).toFixed(2)),
      confiance: 0.8,
      origine: "google",
      source: "google",
      image_source: images[0]?.url ?? null,
      images,
      ...blocsDetails(i),
    };
  });
  return { lieux, sources };
}

function emprise(lieux) {
  const lats = lieux.map((l) => l.coordonnees.latitude);
  const lngs = lieux.map((l) => l.coordonnees.longitude);
  return { sud: Math.min(...lats), nord: Math.max(...lats), ouest: Math.min(...lngs), est: Math.max(...lngs) };
}

// Cas « référentiel seul » : même forme que l'exemple réel (Google indisponible, aucune image)
function reponseReferentiel(texte) {
  const lieu = {
    nom: "MAROARY", niveau: "fokontany", code_officiel: "11130917", region: "ANALAMANGA", district: "MANJAKANDRIANA",
    produit: null, categorie: null, description: "Fokontany du référentiel officiel.",
    coordonnees: { latitude: -18.69833, longitude: 47.68853, precision: "repli_hierarchique" },
    note_google: null, avis: null, sources_citees: null, mots_cles: [], pertinence: 0.5, confiance: 0.5,
    origine: "referentiel", source: "referentiel", image_source: null, images: [],
  };
  return {
    id_resultat: `${Date.now()}-marary-mock`, statut: "termine", date_creation: maintenant(), date_fin: maintenant(),
    requete: { texte_original: texte, intention: "lieu", mots_cles: [norm(texte)] },
    reponse: { texte: `1 lieu(x) trouvé(s) pour « ${texte} » : MAROARY.`, source_principale: "referentiel", recherche_google: "indisponible" },
    lieux: [lieu], lieux_approximative: [lieu],
    carte: { centre: { latitude: -18.69833, longitude: 47.68853 }, emprise: { sud: -18.69833, nord: -18.69833, ouest: 47.68853, est: 47.68853 }, zoom_suggere: 11 },
    sources: [{ reference: "R1", origine: "referentiel", titre: null, url: null, fichier: null }],
    clarification: null, urgence: null,
    avertissements: ["Recherche Google impossible : API « Custom Search » non activée pour cette clé, ou quota dépassé."],
    erreur: null,
  };
}

export function simulerIA(texte, base) {
  const t = norm(texte);

  if (/ma?roary/.test(t)) return reponseReferentiel(texte);

  if (t.length < 3) {
    return {
      id_resultat: `${Date.now()}-clarification-mock`, statut: "clarification_necessaire",
      date_creation: maintenant(), date_fin: maintenant(),
      requete: { texte_original: texte, intention: null, mots_cles: [] },
      reponse: null, lieux: [], lieux_approximative: [], carte: null, sources: [],
      clarification: { question: "Pouvez-vous préciser votre besoin ?" },
      urgence: null, avertissements: [], erreur: null,
    };
  }

  const { lieux, sources } = lieuxDemo(base);
  return {
    id_resultat: `${Date.now()}-${t.replace(/\W+/g, "-").slice(0, 12)}-mock`,
    statut: "termine", date_creation: maintenant(), date_fin: maintenant(),
    requete: { texte_original: texte, intention: "lieu", mots_cles: t.split(/\s+/).filter(Boolean) },
    reponse: { texte: `Voici les résultats pour « ${texte} ».`, source_principale: "google", recherche_google: "disponible" },
    lieux, lieux_approximative: [],
    carte: {
      centre: { latitude: -18.8792, longitude: 47.5079 },
      emprise: emprise(lieux),
      zoom_suggere: 12,
    },
    sources, clarification: null, urgence: null, avertissements: [], erreur: null,
  };
}

// Photo de démo (SVG dégradé, même teinte que le design)
export function imageDemo(i, k) {
  const hue = (i * 37 + 150) % 360 + k * 16;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 400">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="hsl(${hue},42%,38%)"/><stop offset="1" stop-color="hsl(${hue + 34},48%,26%)"/></linearGradient></defs>
<rect width="640" height="400" fill="url(#g)"/>
<g fill="none" stroke="#fff" stroke-opacity=".85" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"><rect x="250" y="150" width="140" height="110" rx="12"/><circle cx="292" cy="190" r="10"/><path d="m390 245-32-32-52 52"/></g>
</svg>`;
}
