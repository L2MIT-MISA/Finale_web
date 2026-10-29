import { useEffect, useRef, useState, type ReactNode } from "react";
import { QRCodeSVG } from "qrcode.react";
import type { Connectivite, Lieu, SourceIA } from "../../pages/Search/searchTypes";
import { chargerConnectiviteEnCache } from "../../services/connectivite";
import SecuriteLieu from "../ConnecteoMap/SecuriteLieu";
import { DetailsConnectivite, DetailsInfos } from "./DetailsLieu";
import { PinIcon } from "./icons";
import { hueDe } from "./placeFormat";

interface Props {
  lieu: Lieu;
  sources: SourceIA[];
  enregistre: boolean;
  onToggleSave: () => void;
  onClose: () => void;
  /** Trace l'itinéraire vers ce lieu sur la carte. */
  onItineraire: () => void;
  onToast: (message: string) => void;
}

type Onglet = "apercu" | "securite" | "reseau";
const ONGLETS: { id: Onglet; label: string }[] = [
  { id: "apercu", label: "Aperçu" },
  { id: "securite", label: "Sécurité" },
  { id: "reseau", label: "Réseau" },
];

const INDISPONIBLE = <p className="sr-brief sr-vide">Information non disponible pour ce lieu.</p>;

const Svg = ({ children, sw = 1.9 }: { children: ReactNode; sw?: number }) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>
);

// Photos du lieu : diaporama automatique, flèches et pastilles (comme la maquette).
function Photos({ lieu, onClose }: { lieu: Lieu; onClose: () => void }) {
  const images = lieu.images;
  const n = images.length;
  const [slide, setSlide] = useState(0);
  const [cassees, setCassees] = useState<string[]>([]);
  const touche = useRef(0);
  const hue = hueDe(lieu.id);
  const idx = n ? slide % n : 0;
  const image = images[idx];

  useEffect(() => {
    if (n < 2) return;
    const timer = setInterval(() => {
      if (Date.now() - touche.current >= 4000) setSlide((s) => s + 1);
    }, 3500);
    return () => clearInterval(timer);
  }, [n]);

  const aller = (d: number) => { touche.current = Date.now(); setSlide((idx + d + n) % n); };
  const fond = n > 0
    ? `linear-gradient(135deg, hsl(${hue + idx * 16},42%,38%), hsl(${hue + 34 + idx * 16},48%,26%))`
    : undefined;
  const visible = image && !cassees.includes(image.url);

  return (
    <div className={`sr-d-photo${n === 0 ? " empty" : ""}`} style={{ background: fond }}>
      {visible ? (
        <img src={image.url} alt={image.legende ?? lieu.nom} onError={() => setCassees((c) => [...c, image.url])} />
      ) : (
        <span className="sr-d-photo-label">{n > 0 ? "Photo indisponible" : "Pas de photo"}</span>
      )}
      {n > 1 && (
        <>
          <button type="button" className="sr-d-hit" aria-label="Photo suivante" onClick={() => aller(1)} />
          <button type="button" className="sr-arrow left" aria-label="Photo précédente" onClick={() => aller(-1)}>‹</button>
          <button type="button" className="sr-arrow right" aria-label="Photo suivante" onClick={() => aller(1)}>›</button>
          <div className="sr-dots" aria-hidden="true">
            {images.map((_, k) => <span key={k} className={k === idx ? "on" : ""} />)}
          </div>
        </>
      )}
      {n > 0 && <span className="sr-d-counter">{image?.legende ? `${image.legende} ` : ""}{idx + 1} / {n}</span>}
      <button type="button" className="sr-d-close" aria-label="Fermer" onClick={onClose}>✕</button>
    </div>
  );
}

// Fiche détaillée d'un lieu (à la manière de Google Maps) : photos, nom, onglets, actions.
// Rendue avec key={lieu.id} côté parent : l'état repart à zéro à chaque lieu.
export default function PlaceDetailPanel({ lieu, sources, enregistre, onToggleSave, onClose, onItineraire, onToast }: Props) {
  const [onglet, setOnglet] = useState<Onglet>("apercu");
  const [qr, setQr] = useState(false);
  // undefined = chargement en cours, null = aucune donnée
  const [calculee, setCalculee] = useState<Connectivite | null | undefined>(undefined);

  const { lat, lng } = lieu.position;
  const dejaFournie = lieu.connectivite !== null;
  useEffect(() => {
    if (dejaFournie) return;
    let annule = false;
    void chargerConnectiviteEnCache(lat, lng).then((c) => { if (!annule) setCalculee(c); });
    return () => { annule = true; };
  }, [dejaFournie, lat, lng]);
  const connectivite = lieu.connectivite ?? calculee;

  const { securite } = lieu;
  const lienCarte = `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
  const resumeSecurite = securite?.resume ?? "Police, hôpitaux et pharmacies à proximité.";
  const resumeReseau = connectivite ? connectivite.brief : connectivite === undefined ? "Chargement…" : "Information non disponible.";

  async function partager() {
    if (typeof navigator.share === "function") {
      try {
        await navigator.share({ title: lieu.nom, url: lienCarte });
      } catch {
        /* partage annulé */
      }
      return;
    }
    try {
      await navigator.clipboard.writeText(lienCarte);
      onToast("Lien copié");
    } catch {
      onToast("Copie impossible sur ce navigateur");
    }
  }

  const bientot = () => onToast("Cette fonction arrive bientôt.");

  const actions: { label: string; icone: ReactNode; principal?: boolean; onClick: () => void }[] = [
    { label: "Itinéraires", principal: true, onClick: onItineraire, icone: <path d="M3 11 21 3l-8 18-2-8-8-2Z" /> },
    {
      label: enregistre ? "Enregistré" : "Enregistrer",
      onClick: onToggleSave,
      icone: <path d="M6 3h12v18l-6-4-6 4V3Z" fill={enregistre ? "currentColor" : "none"} />,
    },
    {
      label: "Envoyer vers le téléphone",
      onClick: () => setQr((v) => !v),
      icone: <><rect x="7" y="2" width="10" height="20" rx="2" /><path d="M11 18h2" /></>,
    },
    {
      label: "Partager",
      onClick: () => void partager(),
      icone: <><circle cx="6" cy="12" r="2.5" /><circle cx="18" cy="6" r="2.5" /><circle cx="18" cy="18" r="2.5" /><path d="m8.2 10.8 7.6-3.6M8.2 13.2l7.6 3.6" /></>,
    },
    { label: "Signaler", onClick: bientot, icone: <path d="M5 21V4M5 4h11l-2 4 2 4H5" /> },
  ];

  return (
    <section className="sr-detail" aria-label="Détails du lieu">
      <Photos lieu={lieu} onClose={onClose} />

      <div className="sr-d-title">
        <h2>{lieu.nom}</h2>
        {lieu.sousTitre && <div className="sr-d-loc">{lieu.sousTitre}</div>}
        {(securite?.niveau || connectivite) && (
          <div className="sr-d-chips">
            {securite?.niveau && <span className={`sr-badge big ${securite.ton ?? ""}`}>{securite.niveau}</span>}
            {connectivite && <span className={`sr-badge big ${connectivite.ok ? "ok" : "warn"}`}>{connectivite.label}</span>}
          </div>
        )}
      </div>

      <div className="sr-d-tabs" role="tablist">
        {ONGLETS.map((o) => (
          <button key={o.id} type="button" role="tab" aria-selected={onglet === o.id} className={onglet === o.id ? "on" : ""} onClick={() => setOnglet(o.id)}>
            {o.label}
          </button>
        ))}
      </div>

      <div className="sr-d-actions">
        {actions.map((a) => (
          <button key={a.label} type="button" className={a.principal ? "principal" : ""} onClick={a.onClick}>
            <span><Svg>{a.icone}</Svg></span>
            {a.label}
          </button>
        ))}
      </div>

      {qr && (
        <div className="sr-d-qr">
          <QRCodeSVG value={lienCarte} size={132} marginSize={1} />
          <p>Scannez ce code avec votre téléphone pour ouvrir le lieu dans Google Maps.</p>
          <button type="button" onClick={() => setQr(false)}>Fermer</button>
        </div>
      )}

      {onglet === "apercu" && (
        <div className="sr-d-body">
          <div className="sr-d-row"><span className="ico"><PinIcon /></span><span>{lieu.sousTitre || "Madagascar"}</span></div>
          <button type="button" className="sr-d-row nav" onClick={() => setOnglet("securite")}>
            <span className="ico"><Svg><path d="M12 3 4 6v6c0 4.5 3.4 8 8 9 4.6-1 8-4.5 8-9V6l-8-3Z" /></Svg></span>
            <span className="txt"><strong>Sécurité</strong><br />{resumeSecurite}</span>
            <span className="chev" aria-hidden="true">›</span>
          </button>
          <button type="button" className="sr-d-row nav" onClick={() => setOnglet("reseau")}>
            <span className="ico"><Svg><path d="M5 20v-4M10 20v-8M15 20V8M20 20V4" /></Svg></span>
            <span className="txt"><strong>Connectivité</strong><br />{resumeReseau}</span>
            <span className="chev" aria-hidden="true">›</span>
          </button>
          <div className="sr-d-infos">
            <DetailsInfos lieu={lieu} sources={sources} />
          </div>
          <div className="sr-d-suggest">
            <button type="button" onClick={bientot}>Suggérer une modification</button>
          </div>
        </div>
      )}

      {onglet === "securite" && (
        <div className="sr-d-body pad">
          <p className="sr-brief">{resumeSecurite}</p>
          <SecuriteLieu ouvert lieu={{ nom: lieu.nom, sousTitre: lieu.sousTitre, position: { lat, lng } }} />
        </div>
      )}

      {onglet === "reseau" && (
        <div className="sr-d-body pad">
          {connectivite ? <DetailsConnectivite connectivite={connectivite} />
            : connectivite === undefined ? <p className="sr-brief sr-vide">Chargement…</p>
            : INDISPONIBLE}
        </div>
      )}
    </section>
  );
}
