import type { PlaceResult } from "../../pages/Search/searchTypes";
import { ArrowIcon, BackIcon, PinIcon } from "./icons";
import {
  connectivityLabel,
  connectivityTone,
  formatMeters,
  formatOperator,
  formatType,
  nearestTower,
  safeWebsite,
} from "./placeFormat";

interface PlaceDetailProps {
  place: PlaceResult;
  onBack: () => void;
  onFocus: () => void;
}

export default function PlaceDetail({ place, onBack, onFocus }: PlaceDetailProps) {
  const tone = connectivityTone(place);
  const operators = Object.entries(place.connectivityDetails?.operators ?? {});

  return (
    <div className="sr-detail">
      <div className="sr-detail-top">
        <button type="button" className="sr-back" onClick={onBack}>
          <BackIcon />
          Retour aux résultats
        </button>
      </div>

      <div className="sr-detail-scroll">
        <div className="sr-hero">
          <div className="sr-hero-icon"><PinIcon /></div>
          <div className="sr-hero-info">
            <div className="sr-tag">{formatType(place.type)}</div>
            <div className="sr-hero-title">{place.name}</div>
          </div>
        </div>

        <div className={`sr-status ${tone}`}>{connectivityLabel(place)}</div>

        {operators.length > 0 && (
          <div className="sr-section">
            <div className="sr-section-title">Couverture réseau</div>
            <div className="sr-op-list">
              {operators.map(([name, operator]) => {
                const tower = nearestTower(operator);
                return (
                  <div className="sr-op" key={name}>
                    <div className="sr-op-row">
                      <span className="sr-op-name">{formatOperator(name)}</span>
                      <span className="sr-chips">
                        {operator.technologies_actives.length > 0
                          ? operator.technologies_actives.map((tech) => <span className="sr-chip" key={tech}>{tech}</span>)
                          : <span className="sr-op-none">Aucun signal</span>}
                      </span>
                    </div>
                    {tower && <div className="sr-op-tower">Pylône le plus proche : {tower.name}, {formatMeters(tower.distance_meters)}</div>}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="sr-section">
          <div className="sr-section-title">Informations</div>
          <div className="sr-info-list">
            <div className="sr-info-row"><span className="sr-label">Adresse</span><span className="sr-value">{place.address}</span></div>
            {place.openingHours && <div className="sr-info-row"><span className="sr-label">Horaires</span><span className="sr-value">{place.openingHours}</span></div>}
            {place.phone && <div className="sr-info-row"><span className="sr-label">Téléphone</span><a className="sr-value sr-link" href={`tel:${place.phone}`}>{place.phone}</a></div>}
            {place.website && <div className="sr-info-row"><span className="sr-label">Site web</span><a className="sr-value sr-link" href={safeWebsite(place.website)} target="_blank" rel="noopener noreferrer">{place.website}</a></div>}
            <div className="sr-info-row"><span className="sr-label">Type</span><span className="sr-value sr-capitalize">{formatType(place.type)}</span></div>
          </div>
        </div>

        <button type="button" className="sr-action" onClick={onFocus}>
          <ArrowIcon />
          Y aller
        </button>
      </div>
    </div>
  );
}
