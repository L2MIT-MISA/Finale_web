export interface GallerySlide {
  id: number;
  src: string;
  alt: string;
  title: string;
  place: string;
}

export const GALLERY_SLIDES: GallerySlide[] = [
  {
    id: 0,
    src: "/images/accueil/slide-1.jpg",
    alt: "Allée des baobabs au lever du jour",
    title: "Allée des baobabs",
    place: "Région de Menabe",
  },
  {
    id: 1,
    src: "/images/accueil/slide-2.jpg",
    alt: "La Fenêtre d'Isalo au coucher du soleil",
    title: "La Fenêtre d'Isalo",
    place: "Parc national de l'Isalo",
  },
  {
    id: 2,
    src: "/images/accueil/slide-3.jpg",
    alt: "Les Tsingy du Bemaraha",
    title: "Les Tsingy",
    place: "Bemaraha",
  },
  {
    id: 3,
    src: "/images/accueil/slide-4.jpg",
    alt: "Forêt de pierre entre deux falaises de calcaire",
    title: "Forêt de pierre",
    place: "Entre deux falaises de calcaire",
  },
  {
    id: 4,
    src: "/images/accueil/slide-5.jpg",
    alt: "Parc national de Masoala",
    title: "Masoala",
    place: "Parc national, nord-est",
  },
  {
    id: 5,
    src: "/images/accueil/slide-6.jpg",
    alt: "Rivières et rochers moussus des forêts tropicales",
    title: "Forêts tropicales",
    place: "Rivières et rochers moussus",
  },
];

export const HERO_BACKGROUND = "/images/accueil/hero.jpg";

export interface HeroSlide {
  id: number;
  src: string;
  alt: string;
  title: string;
  lead: string;
}

/** Diaporama de la couverture : photo + titre + texte défilent ensemble. */
export const HERO_SLIDES: HeroSlide[] = [
  {
    id: 0,
    src: "/images/accueil/hero.jpg",
    alt: "Piste au milieu des baobabs au lever du jour",
    title: "Posez votre question",
    lead: "Trouvez rapidement le bon contact, le bon lieu ou la bonne démarche sur la carte de Madagascar.",
  },
  {
    id: 1,
    src: "/images/accueil/slide-1.jpg",
    alt: "Allée des baobabs",
    title: "Voyagez en toute sécurité et toujours connecté",
    lead: "Allée des Baobabs, Tsingy, Isalo… explorez les merveilles de Madagascar.",
  },
  {
    id: 2,
    src: "/images/accueil/slide-3.jpg",
    alt: "Les Tsingy du Bemaraha",
    title: "Restez connecté partout",
    lead: "Cartes et infos utiles 24h/24, même quand le réseau faiblit.",
  },
  {
    id: 3,
    src: "/images/accueil/slide-5.jpg",
    alt: "Parc national de Masoala",
    title: "Préparez votre itinéraire",
    lead: "Itinéraires, distances et points d'intérêt pour voyager serein.",
  },
];
