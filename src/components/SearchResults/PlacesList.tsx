import type { Lieu } from "../../pages/Search/searchTypes";
import { ImageIcon, BackIcon, PinIcon } from "./icons";
import { hueDe, plur } from "./placeFormat";

interface Props {
  lieux: Lieu[];
  selectedId: string | null;
  onSelect: (l: Lieu) => void;
  onBack: () => void;
}

export default function PlacesList({ lieux, selectedId, onSelect, onBack }: Props) {
  return (
    <div className="sr-list-view">
      <div className="sr-list-head">
        <button type="button" className="sr-link" onClick={onBack}><BackIcon /> Revenir à la discussion</button>
        <h2>{plur(lieux.length, "lieu trouvé", "lieux trouvés")}</h2>
      </div>

      <div className="sr-list">
        {lieux.map((l) => {
          const hue = hueDe(l.id);
          const photo = l.images[0];
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
                <span className="sr-item-photos">{l.images.length ? plur(l.images.length, "photo", "photos") : "Pas de photo"}</span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
