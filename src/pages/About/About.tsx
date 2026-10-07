import { useEffect, useState } from "react";
import "./About.css";
import heroImage from "../assets/hero.jpg";
import missionImage from "../assets/mission.jpg";

interface NavigationLink {
  label: string;
  isActive: boolean;
}

interface ValueCard {
  icon: string;
  title: string;
  description: string;
}

interface FooterColumn {
  title: string;
  links: string[];
}

const navigationLinks: NavigationLink[] = [
  { label: "Accueil", isActive: false },
  { label: "Télécharger", isActive: false },
  { label: "À propos", isActive: true },
];

const valueCards: ValueCard[] = [
  {
    icon: "↗",
    title: "Accessible à tous",
    description:
      "Une interface simple et chaleureuse, facile à prendre en main dès la première visite.",
  },
  {
    icon: "◔",
    title: "Fiable par nature",
    description:
      "Chaque information est vérifiée et mise à jour pour que vous décidiez en toute confiance.",
  },
  {
    icon: "◉",
    title: "Ancré localement",
    description:
      "Conçu avec et pour les communautés malgaches, au plus près des réalités du terrain.",
  },
];

const footerColumns: FooterColumn[] = [
  {
    title: "Navigation",
    links: ["Accueil", "Télécharger", "À propos", "Se connecter"],
  },
  {
    title: "Ressources",
    links: ["Recherche", "Aide", "Contact"],
  },
  {
    title: "Contact",
    links: ["Email", "Téléphone", "Adresse", "Facebook"],
  },
];

function About() {
  const [activeTelecomSites, setActiveTelecomSites] = useState<number | null>(
    null
  );

  const [totalUsers, setTotalUsers] = useState<number | null>(null);

  useEffect(() => {
    fetch("http://localhost:3001/api/statistics")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Impossible de récupérer les statistiques");
        }

        return response.json();
      })
      .then((data) => {
        setActiveTelecomSites(data.activeTelecomSites);
        setTotalUsers(data.totalUsers);
      })
      .catch((error) => {
        console.error("Erreur statistiques:", error);
      });
  }, []);

  return (
    <div className="about-page">
      {/* ---------- Barre de navigation ---------- */}

      {/* ---------- Hero ---------- */}
      <section className="about-hero">
        <img className="about-hero__background" src={heroImage} alt="" />
        <div className="about-hero__overlay" />

        <div className="about-hero__content">
          <span className="about-eyebrow about-eyebrow--light">
            À propos de Connectéo
          </span>

          <h1 className="about-hero__title">
            L'information utile
            <br />
            rapproche les citoyens.
          </h1>

          <p className="about-hero__text">
            Connectéo met l'essentiel à portée de main : trouvez en quelques
            secondes le bon service, le bon lieu et la bonne démarche, où que
            vous soyez à Madagascar.
          </p>
        </div>

        <span className="about-hero__caption">
          Pensé à Madagascar, utile à chaque citoyen.
        </span>
      </section>

      {/* ---------- Mission ---------- */}
      <section className="about-mission">
        <div className="about-mission__media">
          <img
            src={missionImage}
            alt="Une conseillère accompagne une famille"
          />
        </div>

        <div className="about-mission__content">
          <span className="about-eyebrow">Notre mission</span>

          <h2 className="about-mission__title">
            Transformer une question en prochaine étape.
          </h2>

          <p className="about-mission__text">
            Derrière chaque recherche, il y a un besoin bien réel : une
            démarche à faire, un service à trouver, une décision à prendre.
            Connectéo transforme ces questions en réponses claires et en
            étapes concrètes, pour que personne n'avance seul.
          </p>

          <div className="about-mission__note">
            <span className="about-mission__note-icon">›</span>

            <span>
              Des réponses claires, des étapes concrètes,
              <br />
              un seul endroit.
            </span>
          </div>
        </div>
      </section>

      {/* ---------- Chiffres ---------- */}
      <section className="about-stats">
        <span className="about-eyebrow about-eyebrow--light">
          Nos chiffres
        </span>

        <h2 className="about-stats__title">
          Des résultats qui comptent.
        </h2>

        <div className="about-stats__grid">
          {/* 1 — Citoyens dynamiques */}
          <div className="about-stats__card">
            <strong className="about-stats__value">
              {totalUsers !== null
                ? totalUsers.toLocaleString("fr-FR")
                : "..."}
            </strong>

            <span className="about-stats__label">
              Citoyens qui nous font confiance
            </span>
          </div>

          {/* 2 — Sites télécom dynamiques */}
          <div className="about-stats__card">
            <strong className="about-stats__value">
              {activeTelecomSites !== null
                ? activeTelecomSites.toLocaleString("fr-FR")
                : "..."}
            </strong>

            <span className="about-stats__label">
              Sites télécom actifs
            </span>
          </div>

          {/* 3 — Régions */}
          <div className="about-stats__card">
            <strong className="about-stats__value">23</strong>

            <span className="about-stats__label">
              Régions couvertes à Madagascar
            </span>
          </div>

          {/* 4 — Satisfaction */}
          <div className="about-stats__card">
            <strong className="about-stats__value">94 %</strong>

            <span className="about-stats__label">
              D'utilisateurs satisfaits
            </span>
          </div>
        </div>
      </section>

      {/* ---------- Valeurs ---------- */}
      <section className="about-values">
        <span className="about-eyebrow about-eyebrow--centered">
          Nos valeurs
        </span>

        <h2 className="about-values__title">
          Des valeurs vécues au quotidien.
        </h2>

        <div className="about-values__grid">
          {valueCards.map((card) => (
            <article key={card.title} className="about-values__card">
              <span className="about-values__icon">{card.icon}</span>

              <h3 className="about-values__card-title">
                {card.title}
              </h3>

              <p className="about-values__text">
                {card.description}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* ---------- Appel à l'action ---------- */}
      <section className="about-cta">
        <div className="about-cta__content">
          <h2 className="about-cta__title">
            Construisons un service plus proche.
          </h2>

          <p className="about-cta__text">
            Votre avis façonne Connectéo. Dites-nous ce qui vous aiderait le
            plus : nous construisons ce service avec vous, jamais à votre
            place.
          </p>
        </div>

        <div className="about-cta__actions">
          <button
            type="button"
            className="about-button about-button--light"
          >
            Télécharger
          </button>

          <button
            type="button"
            className="about-button about-button--dark"
          >
            Nous contacter
          </button>
        </div>
      </section>

      {/* ---------- Pied de page ---------- */}
      <footer className="about-footer">
        <div className="about-footer__top">
          <div className="about-footer__brand">
            <div className="about-brand">
              <span className="about-logo">C</span>
              <span className="about-brand__name">Connectéo</span>
            </div>

            <p className="about-footer__tagline">
              Connectéo rapproche chaque citoyen de l'information utile,
              simplement et près de chez lui.
            </p>
          </div>

          {footerColumns.map((column) => (
            <div
              key={column.title}
              className="about-footer__column"
            >
              <h4 className="about-footer__column-title">
                {column.title}
              </h4>

              {column.links.map((link) => (
                <a
                  key={link}
                  href="#"
                  className="about-footer__link"
                >
                  {link}
                </a>
              ))}
            </div>
          ))}
        </div>

        <div className="about-footer__bottom">
          <span>© 2026 Connectéo. Tous droits réservés.</span>
          <span>Fait avec soin à Madagascar</span>
        </div>
      </footer>
    </div>
  );
}

export default About;