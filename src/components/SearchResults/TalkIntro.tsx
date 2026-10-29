import type { ReactNode } from "react";

// Panneau de gauche de l'écran de discussion (avant que des lieux soient trouvés) :
// rappel de ce que l'on obtient pour chaque lieu. Pas de carte « Transport ».
const CAPACITES: { titre: string; texte: string; icone: ReactNode }[] = [
  {
    titre: "Photos",
    texte: "Voir à quoi ressemble le lieu avant d'y aller.",
    icone: <><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="9" cy="10" r="1.6" /><path d="m21 16-5-5-8 8" /></>,
  },
  {
    titre: "Sécurité",
    texte: "Ambiance du quartier, éclairage, poste de police.",
    icone: <path d="M12 3 4 6v6c0 4.5 3.4 8 8 9 4.6-1 8-4.5 8-9V6l-8-3Z" />,
  },
  {
    titre: "Connectivité",
    texte: "Orange, Telma, Airtel : de la 2G à la 5G.",
    icone: <path d="M5 20v-4M10 20v-8M15 20V8M20 20V4" />,
  },
];

export default function TalkIntro() {
  return (
    <section className="sr-intro" aria-label="Présentation de l'assistant">
      <div className="sr-intro-inner">
        <div className="sr-intro-head">
          <h1>Où allons-nous ?</h1>
          <p>Écrivez ce que vous cherchez. L'assistant trouve les lieux et vous dit quel réseau mobile y trouver.</p>
        </div>
        <div className="sr-caps">
          <div className="sr-caps-title">POUR CHAQUE LIEU, VOUS OBTENEZ</div>
          <div className="sr-caps-grid">
            {CAPACITES.map((c) => (
              <div className="sr-cap" key={c.titre}>
                <div className="sr-cap-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{c.icone}</svg>
                </div>
                <div>
                  <div className="sr-cap-name">{c.titre}</div>
                  <div className="sr-cap-text">{c.texte}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
