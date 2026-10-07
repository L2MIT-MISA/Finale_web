import { useEffect, useState } from "react";
import type { Connectivite, Lieu, SourceIA } from "../../pages/Search/searchTypes";
import { chargerConnectivite } from "../../services/connectivite";
import CarteLieu, { type CarteId } from "./CarteLieu";
import { DetailsConnectivite, DetailsInfos, DetailsSecurite, DetailsTransport } from "./DetailsLieu";
import GaleriePhotos from "./GaleriePhotos";
import { fmt1, hueDe, typeDe } from "./placeFormat";

interface Props {
  lieu: Lieu;
  sources: SourceIA[];
  /** « Voir l'itinéraire » (carte Transport) : demande à la carte de tracer la route vers ce lieu. */
  onItineraire: () => void;
}

const INDISPONIBLE = <p className="sr-brief sr-vide">Information non disponible pour ce lieu.</p>;

// Bande sous la carte : photos, infos, sécurité, transport, connectivité.
// Sécurité, transport et connectivité sont toujours affichés comme dans la maquette ;
// sans données, la carte indique « non disponible ».
// Rendu avec key={lieu.id} côté parent : l'état repart à zéro à chaque lieu.
export default function PlaceInfo({ lieu, sources, onItineraire }: Props) {
  const [ouvert, setOuvert] = useState<CarteId | null>(null);
  // undefined = chargement en cours, null = aucune donnée
  const [calculee, setCalculee] = useState<Connectivite | null | undefined>(undefined);
  const commun = { ouvert, onOuvrir: setOuvert, onFermer: () => setOuvert(null) };
  const { securite, transport } = lieu;
  const hue = hueDe(lieu.id);

  // Si l'IA n'a pas fourni la connectivité, on la calcule depuis les pylônes proches (backend).
  const { lat, lng } = lieu.position;
  const dejaFournie = lieu.connectivite !== null;
  useEffect(() => {
    if (dejaFournie) return;
    const ctrl = new AbortController();
    chargerConnectivite(lat, lng, ctrl.signal)
      .then(setCalculee)
      .catch(() => { if (!ctrl.signal.aborted) setCalculee(null); });
    return () => ctrl.abort();
  }, [dejaFournie, lat, lng]);
  const connectivite = lieu.connectivite ?? calculee;

  const type = typeDe(lieu);
  const puceInfos = lieu.noteGoogle !== null
    ? { texte: `★ ${fmt1(lieu.noteGoogle)}`, ton: lieu.noteGoogle >= 4 ? "ok" : "warn" }
    : type ? { texte: type, ton: "" } : null;

  return (
    <section className={`sr-info${ouvert ? " open" : ""}`} aria-label="Informations sur le lieu choisi">
      <div className="sr-cards">
        {lieu.images.length > 0 && (
          <CarteLieu
            id="photos"
            titre="Photos"
            large
            resume={<GaleriePhotos images={lieu.images} nom={lieu.nom} hue={hue} />}
            details={<GaleriePhotos images={lieu.images} nom={lieu.nom} hue={hue} grande />}
            {...commun}
          />
        )}

        <CarteLieu
          id="infos"
          titre="Informations"
          badge={puceInfos}
          resume={<p className="sr-brief clamp">{lieu.description ?? (lieu.sousTitre || "Aucune description.")}</p>}
          details={<DetailsInfos lieu={lieu} sources={sources} />}
          {...commun}
        />

        <CarteLieu
          id="securite"
          titre="Sécurité"
          badge={securite?.niveau ? { texte: securite.niveau, ton: securite.ton ?? "" } : null}
          resume={securite ? <p className="sr-brief">{securite.resume ?? "Voir le détail."}</p> : INDISPONIBLE}
          details={securite ? <DetailsSecurite securite={securite} /> : undefined}
          voirPlusInactif
          {...commun}
        />

        <CarteLieu
          id="transport"
          titre="Transport"
          resume={transport ? <>{transport.resume.map((l, i) => <p className="sr-brief" key={i}>{l}</p>)}</> : INDISPONIBLE}
          details={transport ? <DetailsTransport transport={transport} onItineraire={onItineraire} /> : undefined}
          voirPlusInactif
          {...commun}
        />

        <CarteLieu
          id="reseau"
          titre="Connectivité"
          badge={connectivite ? { texte: connectivite.label, ton: connectivite.ok ? "ok" : "warn" } : null}
          resume={
            connectivite ? <p className="sr-brief">{connectivite.brief}</p>
              : connectivite === undefined ? <p className="sr-brief sr-vide">Chargement…</p>
              : INDISPONIBLE
          }
          details={connectivite ? <DetailsConnectivite connectivite={connectivite} /> : undefined}
          {...commun}
        />
      </div>
    </section>
  );
}
