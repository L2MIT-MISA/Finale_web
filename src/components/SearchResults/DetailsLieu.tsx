import type { ReactNode } from "react";
import type { Connectivite, Lieu, Securite, SourceIA, Transport } from "../../pages/Search/searchTypes";
import { distance, fmt1, libellePrecision, plur, typeDe, urlHttp } from "./placeFormat";

// Contenu développé de chaque carte (« Voir plus »).

const TECHS = ["2G", "3G", "4G", "5G"] as const;

function lignesInfos(lieu: Lieu, sources: SourceIA[]): { k: string; v: ReactNode }[] {
  const lignes: { k: string; v: ReactNode }[] = [];
  const type = typeDe(lieu);
  if (type) lignes.push({ k: "Type", v: type });
  if (lieu.district) lignes.push({ k: "District", v: lieu.district });
  if (lieu.region) lignes.push({ k: "Région", v: lieu.region });
  if (lieu.codeOfficiel) lignes.push({ k: "Code officiel", v: lieu.codeOfficiel });
  lignes.push({ k: "Position", v: libellePrecision(lieu) });
  if (lieu.noteGoogle !== null) lignes.push({ k: "Note Google", v: `${fmt1(lieu.noteGoogle)} / 5` });
  if (lieu.nbAvis !== null) lignes.push({ k: "Avis", v: plur(lieu.nbAvis, "avis", "avis") });
  for (const a of lieu.avis) lignes.push({ k: "Avis", v: a });

  const citees = lieu.sourcesCitees.map((ref) => sources.find((s) => s.reference === ref) ?? { reference: ref });
  if (citees.length) {
    lignes.push({
      k: "Sources",
      v: citees.map((s, i) => {
        const href = "url" in s ? urlHttp(s.url) : null;
        const label = ("titre" in s && s.titre) || s.reference;
        return (
          <span key={s.reference}>
            {i > 0 && ", "}
            {href ? <a href={href} target="_blank" rel="noopener noreferrer">{label}</a> : label}
          </span>
        );
      }),
    });
  }
  return lignes;
}

export function DetailsInfos({ lieu, sources }: { lieu: Lieu; sources: SourceIA[] }) {
  return (
    <div className="sr-rows">
      {lieu.description && <p className="sr-desc">{lieu.description}</p>}
      {lignesInfos(lieu, sources).map((r, i) => (
        <div className="sr-row" key={i}><span>{r.k}</span><strong>{r.v}</strong></div>
      ))}
    </div>
  );
}

export function DetailsSecurite({ securite }: { securite: Securite }) {
  if (securite.details.length === 0) return <p className="sr-brief">{securite.resume}</p>;
  return (
    <div className="sr-rows">
      {securite.details.map((d, i) => (
        <div className="sr-row" key={i}><span>{d.label}</span><strong>{d.valeur}</strong></div>
      ))}
    </div>
  );
}

export function DetailsTransport({ transport, onItineraire }: { transport: Transport; onItineraire: () => void }) {
  return (
    <>
      {transport.options.length > 0 && (
        <div className="sr-rows">
          {transport.options.map((o, i) => (
            <div className="sr-tr" key={i}>
              <div>
                <strong>{o.mode}</strong>
                {o.detail && <span>{o.detail}</span>}
              </div>
              {o.duree && <span className="sr-pill">{o.duree}</span>}
            </div>
          ))}
        </div>
      )}
      <button type="button" className="sr-primary sr-itin" onClick={onItineraire}>Voir l'itinéraire</button>
    </>
  );
}

export function DetailsConnectivite({ connectivite }: { connectivite: Connectivite }) {
  return (
    <div className="sr-rows">
      {connectivite.operateurs.map((o) => (
        <div className="sr-op" key={o.nom}>
          <strong>{o.nom}</strong>
          <div className="sr-techs">
            {TECHS.map((t) => <span key={t} className={o.techs[t] ? "on" : "off"}>{t}</span>)}
          </div>
          <span className="sr-op-tw">
            {o.tour ? `Pylône ${o.tour.nom} à ${distance(o.tour.distance)}` : `Aucun pylône ${o.nom} à proximité`}
          </span>
        </div>
      ))}
    </div>
  );
}
