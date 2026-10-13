import { useState } from "react";
import type { Lieu } from "../../pages/Search/searchTypes";
import { ImageIcon, BackIcon, PinIcon } from "./icons";
import { cleLieu, hueDe, plur } from "./placeFormat";
import { useConnectivites } from "./useConnectivites";

interface Props {
  lieux: Lieu[];
  selectedId: string | null;
  enregistres: Set<string>;
  onSelect: (l: Lieu) => void;
  onBack: () => void;
}

// Liste des lieux trouvés. Un seul filtre : « 4G ou plus ».
export default function PlacesList({ lieux, selectedId, enregistres, onSelect, onBack }: Props) {
  const [filtre4g, setFiltre4g] = useState(false);
  const connectivites = useConnectivites(lieux);

  const visibles = filtre4g ? lieux.filter((l) => connectivites[l.id]?.ok) : lieux;
  const enCalcul = filtre4g && lieux.some((l) => connectivites[l.id] === undefined);

  return (
    <div className="sr-list-view">
      <div className="sr-list-head">
        <button type="button" className="sr-link" onClick={onBack}><BackIcon /> Revenir à la discussion</button>
        <h2>{plur(visibles.length, "lieu trouvé", "lieux trouvés")}</h2>
        <div role="group" aria-label="Filtres" className="sr-filters">
          <button type="button" aria-pressed={filtre4g} className={filtre4g ? "on" : ""} onClick={() => setFiltre4g((v) => !v)}>
            4G ou plus
          </button>
        </div>
      </div>

      <div className="sr-list">
        {enCalcul && <p className="sr-list-note">Calcul de la couverture réseau…</p>}
        {!enCalcul && filtre4g && visibles.length === 0 && (
          <p className="sr-list-note">Aucun lieu avec une couverture 4G connue.</p>
        )}
        {visibles.map((l) => {
          const hue = hueDe(l.id);
          const photo = l.images[0];
          const conn = connectivites[l.id];
          return (
            <button
              key={l.id}
              type="button"
              className={`sr-item${l.id === selectedId ? " active" : ""}`}
              aria-label={`${l.nom}, ${l.sousTitre}`}
              onClick={() => onSelect(l)}
            >
              <span
                className={`sr-thumb${photo ? "" : " empty"}`}
                style={photo ? { background: `linear-gradient(135deg, hsl(${hue},42%,38%), hsl(${hue + 34},48%,26%))` } : undefined}
              >
                {photo ? <img src={photo.url} alt="" loading="lazy" onError={(e) => { e.currentTarget.style.display = "none"; }} /> : null}
                <ImageIcon />
              </span>
              <span className="sr-item-info">
                <span className="sr-item-name">{l.nom}</span>
                {l.sousTitre && <span className="sr-item-loc"><PinIcon />{l.sousTitre}</span>}
                <span className="sr-item-photos">
                  {l.images.length ? plur(l.images.length, "photo", "photos") : "Pas de photo"}
                  {enregistres.has(cleLieu(l)) ? " · ★ Enregistré" : ""}
                </span>
                {(l.securite?.niveau || conn) && (
                  <span className="sr-item-chips">
                    {l.securite?.niveau && <span className={`sr-badge ${l.securite.ton ?? ""}`}>{l.securite.niveau}</span>}
                    {conn && <span className={`sr-badge ${conn.ok ? "ok" : "warn"}`}>{conn.label}</span>}
                  </span>
                )}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
