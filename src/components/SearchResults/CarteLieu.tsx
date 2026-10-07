import type { ReactNode } from "react";

export type CarteId = "photos" | "infos" | "securite" | "transport" | "reseau";

interface Props {
  id: CarteId;
  titre: string;
  badge?: { texte: string; ton: string } | null;
  /** Carte actuellement développée (null = aucune). */
  ouvert: CarteId | null;
  large?: boolean;
  resume: ReactNode;
  /** Absent : carte d'information seule, sans « Voir plus ». */
  details?: ReactNode;
  /** Sans `details` : affiche quand même un « Voir plus » qui ne fait rien (pour l'instant). */
  voirPlusInactif?: boolean;
  onOuvrir: (id: CarteId) => void;
  onFermer: () => void;
}

// Une carte de la bande sous la carte : résumé + « Voir plus », ou détail seul + « Voir moins ».
// Quand une carte est développée, les autres se masquent pour lui laisser la place.
export default function CarteLieu({ id, titre, badge, ouvert, large = false, resume, details, voirPlusInactif = false, onOuvrir, onFermer }: Props) {
  const estOuverte = ouvert === id && details !== undefined;
  if (ouvert && ouvert !== id) return null;

  return (
    <article className={`sr-card${estOuverte ? " open" : ""}${large ? " wide" : ""}`}>
      <div className="sr-card-head">
        <h3>{titre}</h3>
        {badge && <span className={`sr-badge ${badge.ton}`}>{badge.texte}</span>}
        {estOuverte && <button type="button" className="sr-less" onClick={onFermer}>Voir moins ↑</button>}
      </div>
      {estOuverte ? details : resume}
      {!estOuverte && details !== undefined && <button type="button" className="sr-more" onClick={() => onOuvrir(id)}>Voir plus ↓</button>}
      {!estOuverte && details === undefined && voirPlusInactif && <button type="button" className="sr-more">Voir plus ↓</button>}
    </article>
  );
}
