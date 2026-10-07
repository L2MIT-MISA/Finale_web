// @ts-nocheck
import { useState, useEffect } from 'react';
import {
    APIProvider, Map, AdvancedMarker, Polyline, InfoWindow, useMap
} from '@vis.gl/react-google-maps';
import './style/Carte.css';
import './style/Itineraire.css';
import './style/Bulle.css';
import './style/Zoom.css';

const CENTRE = { lat: -18.8792, lng: 47.5079 };
// ============================================================
// BOUTONS DE ZOOM
// ============================================================
function ZoomControls() {
    const map = useMap();
    return (
        <div className="zoom-controls">
            <button className="zoom-btn" onClick={() => map.setZoom((map.getZoom() || 6) + 1)}>+</button>
            <button className="zoom-btn" onClick={() => map.setZoom((map.getZoom() || 6) - 1)}>−</button>
        </div>
    );
}

// ============================================================
// BULLE LORA
// ============================================================
function BulleLora({ dispositif, onClose }) {
    return (
        <InfoWindow
            position={{ lat: dispositif.lat, lng: dispositif.lng }}
            onCloseClick={onClose}
            pixelOffset={[0, -40]}
        >
            <div className="bulle-pylone">
                <div className="bulle-header" style={{ borderBottomColor: '#27ae60' }}>
                    <span className="bulle-icone">📶</span>
                    <h3 style={{ color: '#27ae60' }}>{dispositif.id}</h3>
                </div>
                <div className="bulle-corps">
                    <div className="bulle-ligne">
                        <strong>Batterie :</strong> {dispositif.batterie}%
                    </div>
                    {dispositif.pylone_proche ? (
                        <>
                            <div className="bulle-ligne">
                                <strong>Pylône le plus proche :</strong>{' '}
                                {dispositif.pylone_proche.nom || dispositif.pylone_proche.code_site}
                            </div>
                            <div className="bulle-ligne">
                                <strong>Distance :</strong>{' '}
                                {(dispositif.pylone_proche.distance_m / 1000).toFixed(2)} km
                            </div>
                        </>
                    ) : (
                        <div className="bulle-ligne">Aucun pylône à proximité</div>
                    )}
                    <div className="bulle-coords">
                        📍 {dispositif.lat.toFixed(4)}, {dispositif.lng.toFixed(4)}
                    </div>
                </div>
            </div>
        </InfoWindow>
    );
}

// ============================================================
// MARQUEUR LORA + LIAISON VERS LE PYLÔNE LE PLUS PROCHE
// ============================================================
function MarqueurLora({ dispositif, onSelect }) {
    return (
        <>
            <AdvancedMarker
                position={{ lat: dispositif.lat, lng: dispositif.lng }}
                title={`${dispositif.id} — batterie ${dispositif.batterie}%`}
                onClick={() => onSelect(dispositif)}
            >
                <img
                    src="/lora.png"
                    alt="Dispositif LoRa"
                    style={{
                        width: '40px',
                        height: 'auto',
                        cursor: 'pointer',
                        filter: 'drop-shadow(0 3px 6px rgba(0,0,0,0.35))',
                        transition: 'transform 0.15s ease'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.2)'}
                    onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                />
            </AdvancedMarker>

            {dispositif.pylone_proche && (
                <Polyline
                    path={[
                        { lat: dispositif.lat, lng: dispositif.lng },
                        { lat: dispositif.pylone_proche.lat, lng: dispositif.pylone_proche.lng }
                    ]}
                    strokeColor="#27ae60"
                    strokeOpacity={0.6}
                    strokeWeight={2}
                    icons={[{
                        icon: { path: 'M 0,-1 0,1', strokeOpacity: 1, scale: 3 },
                        offset: '0',
                        repeat: '10px'
                    }]}
                />
            )}
        </>
    );
}

// ============================================================
// ITINÉRAIRE (POLYLIGNE)
// ============================================================
function ItineraireAffiche({ trace }) {
    const map = useMap();
    useEffect(() => {
        if (!trace || trace.length === 0 || !map) return;
        const bounds = new window.google.maps.LatLngBounds();
        trace.forEach((point) => bounds.extend(point));
        map.fitBounds(bounds, { padding: 60 });
    }, [trace, map]);

    if (!trace || trace.length === 0) return null;

    return (
        <Polyline
            path={trace}
            strokeColor="#1a73e8"
            strokeWeight={6}
            strokeOpacity={0.85}
        />
    );
}

// ============================================================
// FONCTIONS UTILITAIRES (Nominatim + OSRM)
// ============================================================
async function geocoder(adresse) {
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(adresse)}&limit=1`;
    const res = await fetch(url, { headers: { 'Accept-Language': 'fr' } });
    const data = await res.json();
    if (data.length === 0) throw new Error(`Adresse non trouvée : "${adresse}"`);
    return {
        lat: parseFloat(data[0].lat),
        lng: parseFloat(data[0].lon),
        nom: data[0].display_name
    };
}

async function calculerItineraire(depart, arrivee) {
    const url = `https://router.project-osrm.org/route/v1/driving/${depart.lng},${depart.lat};${arrivee.lng},${arrivee.lat}?overview=full&geometries=geojson`;
    const res = await fetch(url);
    const data = await res.json();
    if (!data.routes || data.routes.length === 0) throw new Error("Aucun itinéraire trouvé");
    const route = data.routes[0];
    const trace = route.geometry.coordinates.map(([lng, lat]) => ({ lat, lng }));
    return {
        trace,
        distance: `${(route.distance / 1000).toFixed(1)} km`,
        duree: `${Math.round(route.duration / 60)} min`
    };
}

// ============================================================
// PANNEAU ITINÉRAIRE
// ============================================================
function PanneauItineraire({ onCalculer, onEffacer, infos, chargement, destination, demande }) {
    const [ouvert, setOuvert] = useState(false);
    const [depart, setDepart] = useState('');
    const [arrivee, setArrivee] = useState('');
    const [coordArrivee, setCoordArrivee] = useState(null);

    // « Voir l'itinéraire » (fiche du lieu) : ouvre le panneau avec le lieu comme destination
    useEffect(() => {
        if (!demande || !destination) return;
        setOuvert(true);
        setArrivee(destination.nom);
        setCoordArrivee(destination.position);
    }, [demande]);

    const handleCalculer = (e) => {
        e.preventDefault();
        if (!depart.trim() || !arrivee.trim()) return;
        onCalculer(depart.trim(), arrivee.trim(), coordArrivee);
    };

    const handleEffacer = () => {
        setDepart('');
        setArrivee('');
        setCoordArrivee(null);
        onEffacer();
    };

    return (
        <div className="itineraire-panel">
            {!ouvert && (
                <button className="itineraire-toggle" onClick={() => setOuvert(true)} title="Calculer un itinéraire" aria-label="Calculer un itinéraire"><svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9" /><polygon points="16 8 14 14 8 16 10 10 16 8" /></svg></button>
            )}
            {ouvert && (
                <div className="itineraire-contenu">
                    <div className="itineraire-header">
                        <h3>Itinéraire</h3>
                        <button className="itineraire-fermer" onClick={() => setOuvert(false)}>✕</button>
                    </div>
                    <form onSubmit={handleCalculer}>
                        <div className="itineraire-champ">
                            <span className="icone">🟢</span>
                            <input type="text" placeholder="Point de départ" value={depart} onChange={(e) => setDepart(e.target.value)} />
                        </div>
                        <div className="itineraire-champ">
                            <span className="icone">🔴</span>
                            <input type="text" placeholder="Destination" value={arrivee} onChange={(e) => { setArrivee(e.target.value); setCoordArrivee(null); }} />
                        </div>
                        <div className="itineraire-actions">
                            <button type="submit" className="btn-calculer" disabled={chargement}>
                                {chargement ? 'Calcul...' : 'Calculer'}
                            </button>
                            <button type="button" className="btn-effacer" onClick={handleEffacer}>Effacer</button>
                        </div>
                    </form>
                    {infos && infos.distance && (
                        <div className="itineraire-infos">
                            <div className="info-ligne"><strong>Distance :</strong> {infos.distance}</div>
                            <div className="info-ligne"><strong>⏱Durée :</strong> {infos.duree}</div>
                        </div>
                    )}
                    {infos && infos.erreur && (<div className="itineraire-erreur">{infos.erreur}</div>)}
                    <div className="itineraire-credit">Itinéraire : OpenStreetMap</div>
                </div>
            )}
        </div>
    );
}

// ============================================================
// BBOX + ZOOM SELON RAYON
// ============================================================
function zoomPourRayon(rayonKm) {
    if (rayonKm <= 1) return 15;
    if (rayonKm <= 2) return 14;
    if (rayonKm <= 5) return 13;
    if (rayonKm <= 10) return 12;
    if (rayonKm <= 20) return 11;
    if (rayonKm <= 50) return 10;
    return 9;
}

// ============================================================
// CONFIG
// ============================================================
const RAYON_KM = 10;

// ============================================================
// COMPOSANT PRINCIPAL
// ============================================================
function ConnecteoMap({ lieux = [], carte = null, selected = null, demandeItineraire = 0, onSelect }: any) {
    const [trace, setTrace] = useState(null);
    const [infosItineraire, setInfosItineraire] = useState(null);
    const [chargementItineraire, setChargementItineraire] = useState(false);
    const [mapInstance, setMapInstance] = useState(null);

    // LoRa (temps réel via WebSocket)
    const [dispositifsLora] = useState([]);
    const [loraSelectionneId, setLoraSelectionneId] = useState(null);
    const loraSelectionne = dispositifsLora.find((d) => d.id === loraSelectionneId) || null;

    const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

    const recentrer = () => {
        if (!mapInstance) return;
        if (lieux.length > 1) {
            const bounds = new window.google.maps.LatLngBounds();
            lieux.forEach((l) => bounds.extend(l.position));
            mapInstance.fitBounds(bounds, 60);
            return;
        }
        const centre = lieux[0]?.position
            ?? (carte?.centre ? { lat: carte.centre.latitude, lng: carte.centre.longitude } : CENTRE);
        mapInstance.setCenter(centre);
        mapInstance.setZoom(carte?.zoom_suggere ?? (lieux.length ? 13 : zoomPourRayon(RAYON_KM)));
    };

    useEffect(() => {
        if (!mapInstance) return;
        if (selected) {
            mapInstance.panTo(selected.position);
            mapInstance.setZoom(15);
        } else {
            recentrer();
        }
    }, [selected, lieux, mapInstance]);

    // ----------------------------------------------------------
    // Itinéraire
    // ----------------------------------------------------------
    const handleCalculer = async (adresseDepart, adresseArrivee, coordArrivee) => {
        setChargementItineraire(true);
        setInfosItineraire(null);
        setTrace(null);

        try {
            const depart = await geocoder(adresseDepart);
            const arrivee = coordArrivee ?? await geocoder(adresseArrivee);
            const resultat = await calculerItineraire(depart, arrivee);
            setTrace(resultat.trace);
            setInfosItineraire({ distance: resultat.distance, duree: resultat.duree });
        } catch (err) {
            console.error('Erreur itinéraire :', err);
            setInfosItineraire({ erreur: err.message });
        } finally {
            setChargementItineraire(false);
        }
    };

    const handleEffacer = () => {
        setTrace(null);
        setInfosItineraire(null);
    };

    const handleMapClick = () => {
        setLoraSelectionneId(null);
    };

    // ----------------------------------------------------------
    // Rendu
    // ----------------------------------------------------------
    return (
        <div className="carte-wrapper">
            <APIProvider apiKey={apiKey}>
                <Map
                    defaultZoom={zoomPourRayon(RAYON_KM)}
                    defaultCenter={CENTRE}
                    mapId="DEMO_MAP_ID"
                    gestureHandling={'greedy'}
                    disableDefaultUI={true}
                    style={{ width: '100%', height: '100%' }}
                    onClick={handleMapClick}
                    onIdle={(e) => {
                        if (e.map && !mapInstance) setMapInstance(e.map);
                    }}
                >
                    {/* Lieux trouvés */}
                    {lieux.map((l, i) => {
                        const sel = selected?.id === l.id;
                        return (
                            <AdvancedMarker
                                key={`lieu-${l.id}`}
                                position={l.position}
                                title={l.nom}
                                onClick={() => onSelect?.(l)}
                                zIndex={sel ? 3000 : 2000}
                            >
                                <div className={`sr-pin${sel ? ' sel' : ''}${selected && !sel ? ' dim' : ''}${l.approximatif ? ' approx' : ''}`}>{i + 1}</div>
                            </AdvancedMarker>
                        );
                    })}

                    {/* Dispositifs LoRa en temps réel */}
                    {dispositifsLora.map((d) => (
                        <MarqueurLora
                            key={d.id}
                            dispositif={d}
                            onSelect={(disp) => setLoraSelectionneId(disp.id)}
                        />
                    ))}

                    {loraSelectionne && (
                        <BulleLora
                            dispositif={loraSelectionne}
                            onClose={() => setLoraSelectionneId(null)}
                        />
                    )}

                    {trace && <ItineraireAffiche trace={trace} />}
                    <ZoomControls />
                </Map>
            </APIProvider>

            {selected && (
                <div className="sr-map-name">
                    <strong>{selected.nom}</strong>
                    {selected.sousTitre && <span>{selected.sousTitre}</span>}
                </div>
            )}

            <button type="button" className="sr-recenter" aria-label="Recentrer sur les résultats" onClick={recentrer}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="m15.5 8.5-2 5-5 2 2-5 5-2Z" /></svg>
            </button>

            <PanneauItineraire
                onCalculer={handleCalculer}
                onEffacer={handleEffacer}
                infos={infosItineraire}
                chargement={chargementItineraire}
                destination={selected}
                demande={demandeItineraire}
            />
        </div>
    );
}

export default ConnecteoMap;