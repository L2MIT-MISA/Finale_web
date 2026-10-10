import { useState, useEffect, useRef, useMemo } from 'react';
import type { FormEvent, KeyboardEvent, ReactElement } from 'react';
import {
    APIProvider,
    Map,
    AdvancedMarker,
    AdvancedMarkerAnchorPoint,
    useMap
} from '@vis.gl/react-google-maps';
import './style/Carte.css';
import type { Lieu } from './types';
import SecuriteLieu from './SecuriteLieu';
import { COULEUR_TECH, chargerPylonesReseau, decouperParReseau } from './reseau';
import type { Pylone } from './reseau';
import './style/variables.css';
import './style/BarreRecherche.css';
import './style/FicheLieu.css';
import './style/Sidebar.css';
import './style/ZoomControls.css';
import './style/Itineraire.css';
import './style/Responsive.css';

const CENTRE = { lat: -18.8792, lng: 47.5079 };

/* ───────── Types ───────── */

type ModeId = 'car' | 'bike' | 'foot';

interface Mode {
    id: ModeId;
    label: string;
    serveur: string;
    couleur: string;
    icone: ReactElement;
}

interface Coord {
    lat: number;
    lng: number;
}

interface ResultatItineraire {
    trace: google.maps.LatLngLiteral[];
    distanceM: number;
    dureeS: number;
}

type ResultatsParMode = Partial<Record<ModeId, ResultatItineraire>>;

interface NominatimItem {
    lat: string;
    lon: string;
    display_name: string;
    name?: string;
    boundingbox?: string[];
}

interface OsrmResponse {
    routes?: Array<{
        distance: number;
        duration: number;
        geometry: { coordinates: Array<[number, number]> };
    }>;
}

interface LieuExterne {
    id: string | number;
    nom: string;
    sousTitre?: string;
    approximatif?: boolean;
    position: Coord;
}

interface CarteInfo {
    centre?: { latitude: number; longitude: number };
    zoom_suggere?: number;
}

interface CarteProps {
    lieux?: LieuExterne[];
    carte?: CarteInfo | null;
    selected?: LieuExterne | null;
    demandeItineraire?: number;
    onSelect?: (l: LieuExterne) => void;
}

const AUCUN_LIEU: LieuExterne[] = [];

const MODES: Mode[] = [
    {
        id: 'car',
        label: 'Voiture',
        serveur: 'https://routing.openstreetmap.de/routed-car',
        couleur: '#2f5fff',
        icone: (
            <svg viewBox="0 0 24 24">
                <path d="M3 17v-4l2-6h14l2 6v4z" />
                <circle cx="7.5" cy="17" r="1.6" />
                <circle cx="16.5" cy="17" r="1.6" />
                <path d="M3 13h18" />
            </svg>
        )
    },
    {
        id: 'bike',
        label: 'Vélo',
        serveur: 'https://routing.openstreetmap.de/routed-bike',
        couleur: '#16a34a',
        icone: (
            <svg viewBox="0 0 24 24">
                <circle cx="6" cy="16" r="3.5" />
                <circle cx="18" cy="16" r="3.5" />
                <path d="M6 16l4-8h5l3 8M10 8H8" />
            </svg>
        )
    },
    {
        id: 'foot',
        label: 'À pied',
        serveur: 'https://routing.openstreetmap.de/routed-foot',
        couleur: '#e5484d',
        icone: (
            <svg viewBox="0 0 24 24">
                <circle cx="13" cy="4.5" r="1.8" />
                <path d="M12 8l-2 5 3 2v5M10 13l-3 2M12 8l3 3 3 1" />
            </svg>
        )
    }
];

/* ───────── Recherche de lieux (Nominatim) ───────── */

async function chercherLieux(texte: string, limite = 5): Promise<Lieu[]> {
    const url =
        `https://nominatim.openstreetmap.org/search?format=json&addressdetails=0&limit=${limite}` +
        '&accept-language=fr&viewbox=47.35,-18.75,47.65,-19.05' +
        `&q=${encodeURIComponent(texte)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Service de recherche indisponible, réessayez.');
    const data = (await res.json()) as NominatimItem[];
    return data.map((d) => {
        const morceaux = d.display_name.split(',').map((s) => s.trim());
        const [sud, nord, ouest, est] = (d.boundingbox || []).map(parseFloat);
        return {
            lat: parseFloat(d.lat),
            lng: parseFloat(d.lon),
            nom: d.display_name,
            libelle: d.name || morceaux[0],
            adresse: morceaux.slice(1).join(', '),
            bbox: [sud, nord, ouest, est].every((v) => Number.isFinite(v))
                ? { sud, nord, ouest, est }
                : null
        };
    });
}

async function geocoder(adresse: string): Promise<Lieu> {
    const r = await chercherLieux(adresse, 1);
    if (r.length === 0) throw new Error(`Adresse non trouvée : « ${adresse} »`);
    return r[0];
}

function positionActuelle(): Promise<Lieu> {
    return new Promise((resolve, reject) => {
        const echec = () =>
            reject(new Error('Position indisponible : indiquez un point de départ.'));
        if (!navigator.geolocation) {
            echec();
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (p) =>
                resolve({
                    lat: p.coords.latitude,
                    lng: p.coords.longitude,
                    nom: 'Ma position',
                    libelle: 'Ma position',
                    adresse: '',
                    bbox: null
                }),
            echec,
            { timeout: 8000 }
        );
    });
}

async function calculerItineraire(
    mode: Mode,
    depart: Coord,
    arrivee: Coord
): Promise<ResultatItineraire> {
    const url = `${mode.serveur}/route/v1/driving/${depart.lng},${depart.lat};${arrivee.lng},${arrivee.lat}?overview=full&geometries=geojson`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as OsrmResponse;
    if (!data.routes || data.routes.length === 0) throw new Error('Aucun itinéraire');
    const route = data.routes[0];
    return {
        trace: route.geometry.coordinates.map(([lng, lat]) => ({ lat, lng })),
        distanceM: route.distance,
        dureeS: route.duration
    };
}

function formaterDistance(m: number): string {
    return m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(1)} km`;
}

function formaterDuree(s: number): string {
    const minutes = Math.max(1, Math.round(s / 60));
    if (minutes < 60) return `${minutes} min`;
    const h = Math.floor(minutes / 60);
    const reste = minutes % 60;
    return `${h} h ${String(reste).padStart(2, '0')}`;
}

/* ───────── Trace : polyligne multicolore selon couverture réseau ───────── */

interface TraceProps {
    path: google.maps.LatLngLiteral[];
}

function Trace({ path }: TraceProps) {
    const map = useMap();
    const [pylones, setPylones] = useState<Pylone[] | null>(null);

    useEffect(() => {
        let alive = true;
        chargerPylonesReseau()
            .then((data) => {
                if (alive) setPylones(data);
            })
            .catch((err) => console.error('[Trace] Erreur chargement pylones :', err));
        return () => {
            alive = false;
        };
    }, []);

    useEffect(() => {
        if (!map || !path || path.length === 0) return undefined;

        // Tant que les pylônes ne sont pas chargés : ligne grise neutre
        if (!pylones) {
            const contour = new google.maps.Polyline({
                path,
                map,
                strokeColor: '#ffffff',
                strokeOpacity: 0.95,
                strokeWeight: 9,
                zIndex: 1
            });
            const ligne = new google.maps.Polyline({
                path,
                map,
                strokeColor: '#9ca3af',
                strokeOpacity: 1,
                strokeWeight: 5,
                zIndex: 2
            });
            return () => {
                contour.setMap(null);
                ligne.setMap(null);
            };
        }

        // Sinon : segments colorés selon la tech dominante
        const segments = decouperParReseau(path, pylones);
        const polylines: google.maps.Polyline[] = [];

        for (const seg of segments) {
            if (seg.points.length < 2) continue;
            const contour = new google.maps.Polyline({
                path: seg.points,
                map,
                strokeColor: '#ffffff',
                strokeOpacity: 0.95,
                strokeWeight: 9,
                zIndex: 1
            });
            const ligne = new google.maps.Polyline({
                path: seg.points,
                map,
                strokeColor: seg.couleur,
                strokeOpacity: 1,
                strokeWeight: 5,
                zIndex: 2
            });
            polylines.push(contour, ligne);
        }

        return () => {
            polylines.forEach((p) => p.setMap(null));
        };
    }, [map, path, pylones]);

    return null;
}

function AjusterVue({ path }: { path: google.maps.LatLngLiteral[] }) {
    const map = useMap();

    useEffect(() => {
        if (!map || !path || path.length === 0) return;
        const bounds = new google.maps.LatLngBounds();
        path.forEach((p) => bounds.extend(p));
        const large = window.innerWidth > 800;
        const padding = large
            ? { top: 60, bottom: 60, left: 440, right: 90 }
            : { top: Math.round(window.innerHeight * 0.55), bottom: 50, left: 30, right: 30 };
        map.fitBounds(bounds, padding);
    }, [map, path]);

    return null;
}

function AllerA({ lieu }: { lieu: Lieu }) {
    const map = useMap();

    useEffect(() => {
        if (!map || !lieu) return undefined;
        const large = window.innerWidth > 800;
        const padding = large
            ? { top: 100, bottom: 220, left: 440, right: 90 }
            : { top: 90, bottom: Math.round(window.innerHeight * 0.55), left: 30, right: 70 };
        const bounds = lieu.bbox
            ? new google.maps.LatLngBounds(
                { lat: lieu.bbox.sud, lng: lieu.bbox.ouest },
                { lat: lieu.bbox.nord, lng: lieu.bbox.est }
            )
            : new google.maps.LatLngBounds(
                { lat: lieu.lat, lng: lieu.lng },
                { lat: lieu.lat, lng: lieu.lng }
            );
        map.fitBounds(bounds, padding);
        // un point précis donnerait un zoom absurde : on plafonne
        const plafond = lieu.bbox ? 17 : 16;
        const ecouteur = google.maps.event.addListenerOnce(map, 'idle', () => {
            if ((map.getZoom() || 0) > plafond) map.setZoom(plafond);
        });
        return () => ecouteur.remove();
    }, [map, lieu]);

    return null;
}

/* ───────── Contrôles de zoom (bas droite) ───────── */

function ZoomControls({
    typeCarte,
    onToggleType
}: {
    typeCarte: string;
    onToggleType: () => void;
}) {
    const map = useMap();
    const zoomer = (delta: number) => {
        if (!map) return;
        map.setZoom((map.getZoom() || 12) + delta);
    };
    return (
        <div className="zoom-controls zoom-controls-bottom-right">
            <button
                type="button"
                className="zoom-btn"
                onClick={() => zoomer(1)}
                aria-label="Zoom avant"
            >
                +
            </button>
            <button
                type="button"
                className="zoom-btn"
                onClick={() => zoomer(-1)}
                aria-label="Zoom arrière"
            >
                −
            </button>
            <button
                type="button"
                className="zoom-btn zoom-btn-type"
                onClick={onToggleType}
                aria-label="Changer le type de carte"
                title={typeCarte === 'hybrid' ? 'Passer au plan' : 'Passer au satellite'}
            >
                {typeCarte === 'hybrid' ? '🗺️' : '🛰️'}
            </button>
        </div>
    );
}

/* ───────── Barre de recherche ───────── */

interface BarreRechercheProps {
    lieu: Lieu | null;
    onChoisir: (l: Lieu) => void;
    onEffacer: () => void;
}

function BarreRecherche({ lieu, onChoisir, onEffacer }: BarreRechercheProps) {
    const [texte, setTexte] = useState('');
    const [resultats, setResultats] = useState<Lieu[] | null>(null);
    const [chargement, setChargement] = useState(false);
    const [erreur, setErreur] = useState<string | null>(null);
    const [ouvert, setOuvert] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    // ferme la liste quand on clique ailleurs
    useEffect(() => {
        const fermer = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) setOuvert(false);
        };
        document.addEventListener('mousedown', fermer);
        return () => document.removeEventListener('mousedown', fermer);
    }, []);

    // si le lieu est fermé depuis la fiche, on vide la barre
    useEffect(() => {
        if (!lieu) {
            setTexte('');
            setResultats(null);
            setErreur(null);
            setOuvert(false);
        }
    }, [lieu]);

    const choisir = (l: Lieu) => {
        setTexte(l.libelle);
        setOuvert(false);
        onChoisir(l);
    };

    const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const q = texte.trim();
        if (!q || chargement) return;
        setChargement(true);
        setErreur(null);
        try {
            const r = await chercherLieux(q, 5);
            if (r.length === 0) {
                setResultats(null);
                setErreur(`Aucun résultat pour « ${q} »`);
                setOuvert(true);
                return;
            }
            // on va directement au meilleur résultat ; les autres restent proposés
            setResultats(r);
            setOuvert(r.length > 1);
            setTexte(r[0].libelle);
            onChoisir(r[0]);
        } catch (err) {
            setErreur(err instanceof Error ? err.message : 'Erreur inconnue.');
            setOuvert(true);
        } finally {
            setChargement(false);
        }
    };

    const vider = () => {
        setTexte('');
        setResultats(null);
        setErreur(null);
        setOuvert(false);
        onEffacer();
    };

    return (
        <div className="search-wrap" ref={ref}>
            <form className="search-bar" onSubmit={handleSubmit} role="search">
                <svg className="search-icon" viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="11" cy="11" r="7" />
                    <path d="M20 20l-3.5-3.5" />
                </svg>
                <input
                    type="text"
                    placeholder="Rechercher un lieu, une adresse, un quartier…"
                    value={texte}
                    onChange={(e) => setTexte(e.target.value)}
                    onFocus={() => (resultats || erreur) && setOuvert(true)}
                    onKeyDown={(e: KeyboardEvent<HTMLInputElement>) =>
                        e.key === 'Escape' && setOuvert(false)
                    }
                    autoComplete="off"
                    aria-label="Rechercher un lieu"
                />
                {texte && (
                    <button
                        type="button"
                        className="search-clear"
                        onClick={vider}
                        aria-label="Effacer la recherche"
                    >
                        ✕
                    </button>
                )}
                <button
                    type="submit"
                    className="search-submit"
                    disabled={chargement || !texte.trim()}
                >
                    {chargement ? <span className="spinner" /> : 'Chercher'}
                </button>
            </form>

            {ouvert && (erreur || (resultats && resultats.length > 1)) && (
                <div className="search-results">
                    {erreur && <div className="search-empty">{erreur}</div>}
                    {!erreur && <div className="list-label">Autres résultats</div>}
                    {!erreur &&
                        resultats?.map((l, i) => (
                            <button
                                type="button"
                                key={`${l.lat},${l.lng},${i}`}
                                className="search-item"
                                onClick={() => choisir(l)}
                            >
                                <span className="search-item-pin">📍</span>
                                <span className="search-item-text">
                                    <span className="search-item-name">{l.libelle}</span>
                                    <span className="search-item-addr">
                                        {l.adresse || l.nom}
                                    </span>
                                </span>
                            </button>
                        ))}
                </div>
            )}
        </div>
    );
}

/* ───────── Fiche lieu ───────── */

interface FicheLieuProps {
    lieu: Lieu;
    onItineraire: () => void;
    onFermer: () => void;
    /** État replié de la fiche (contrôlé par le parent) */
    repliee?: boolean;
    onToggleReplie?: () => void;
}

function FicheLieu({
    lieu,
    onItineraire,
    onFermer,
    repliee = false,
    onToggleReplie
}: FicheLieuProps) {
    return (
        <div className={'place-card' + (repliee ? ' replie' : '')}>
            <div className="place-card-body">
                <div className="place-card-title">{lieu.libelle}</div>
                <div className="place-card-addr">{lieu.adresse || lieu.nom}</div>
                <div className="place-card-coords">
                    {lieu.lat.toFixed(5)}, {lieu.lng.toFixed(5)}
                </div>
            </div>

            <div className="place-card-actions">
                <button type="button" className="btn-primary" onClick={onItineraire}>
                    <svg className="btn-icon" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M5 12h14M13 6l6 6-6 6" />
                    </svg>
                    Itinéraire
                </button>

                <button type="button" className="btn-ghost" onClick={onFermer}>
                    Fermer
                </button>
            </div>

            {/* Sécurité : le bouton « Afficher plus » est inclus dans SecuriteLieu */}
            {!repliee && (
                <div className="place-card-securite">
                    <SecuriteLieu
                        lieu={{
                            nom: lieu.libelle,
                            sousTitre: lieu.adresse,
                            position: { lat: lieu.lat, lng: lieu.lng }
                        }}
                    />
                </div>
            )}
        </div>
    );
}

/* ───────── Panneau itinéraire (sidebar tiroir) ───────── */

interface PanneauProps {
    arriveeInitiale: string;
    onRechercher: (depart: string, arrivee: string) => void;
    onEffacer: () => void;
    onRetour: () => void;
    resultats: ResultatsParMode | null;
    modeActif: ModeId | null;
    onChoisirMode: (id: ModeId) => void;
    chargement: boolean;
    erreur: string | null;
    destination: string;
}

function Panneau({
    arriveeInitiale,
    onRechercher,
    onEffacer,
    onRetour,
    resultats,
    modeActif,
    onChoisirMode,
    chargement,
    erreur,
    destination
}: PanneauProps) {
    const [depart, setDepart] = useState('');
    const [arrivee, setArrivee] = useState(arriveeInitiale || '');
    const [replie, setReplie] = useState(false);

    const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        if (!arrivee.trim()) return;
        onRechercher(depart.trim(), arrivee.trim());
    };

    const handleEffacer = () => {
        setDepart('');
        setArrivee('');
        onEffacer();
    };

    const inverser = () => {
        setDepart(arrivee);
        setArrivee(depart);
    };

    const reference = resultats ? resultats[MODES[0].id] : undefined;

    return (
        <aside className={'sidebar' + (replie ? ' replie' : '')}>
            {/* Bouton toggle attaché au bord droit de la sidebar */}
            <button
                type="button"
                className="sidebar-collapse-btn"
                onClick={() => setReplie((v) => !v)}
                aria-label={replie ? 'Déplier le panneau' : 'Replier le panneau'}
                title={replie ? 'Déplier le panneau' : 'Replier le panneau'}
            >
                <strong style={{ fontSize: "20px" }}>{replie ? '>' : '<'}</strong>
            </button>

            <div className="sidebar-head">
                <button
                    type="button"
                    className="sidebar-back"
                    onClick={onRetour}
                    aria-label="Retour à la recherche"
                    title="Retour"
                >
                    ←
                </button>
                <div className="sidebar-head-text">
                    <h2 className="sidebar-title">Itinéraire</h2>
                    <div className="sidebar-count">
                        {resultats
                            ? `Vers ${destination}`
                            : 'Choisissez un départ et une destination'}
                    </div>
                </div>
            </div>

            <form className="route-form" onSubmit={handleSubmit}>
                <div className="route-fields">
                    <label className="route-field">
                        <span className="dot dot-start" />
                        <input
                            type="text"
                            placeholder="Départ (vide = ma position)"
                            value={depart}
                            onChange={(e) => setDepart(e.target.value)}
                            autoComplete="off"
                            autoFocus
                        />
                    </label>
                    <label className="route-field">
                        <span className="dot dot-end" />
                        <input
                            type="text"
                            placeholder="Destination"
                            value={arrivee}
                            onChange={(e) => setArrivee(e.target.value)}
                            autoComplete="off"
                        />
                    </label>
                    <button
                        type="button"
                        className="swap-btn"
                        onClick={inverser}
                        aria-label="Inverser départ et destination"
                        title="Inverser"
                    >
                        ⇅
                    </button>
                </div>
                <div className="route-actions">
                    <button
                        type="submit"
                        className="btn-primary"
                        disabled={chargement || !arrivee.trim()}
                    >
                        {chargement && <span className="spinner" />}
                        {chargement ? 'Calcul…' : 'Rechercher'}
                    </button>
                    <button type="button" className="btn-ghost" onClick={handleEffacer}>
                        Effacer
                    </button>
                </div>
            </form>

            {erreur && <div className="route-error">{erreur}</div>}

            <div className="sidebar-list">
                {resultats && <div className="list-label">Moyens de transport</div>}
                {resultats &&
                    MODES.map((mode) => {
                        const r = resultats[mode.id];
                        if (!r) {
                            return (
                                <div key={mode.id} className="result-item disabled">
                                    <div className="result-icon">{mode.icone}</div>
                                    <div className="result-info">
                                        <div className="result-name">{mode.label}</div>
                                        <div className="result-meta">
                                            Non disponible pour ce trajet
                                        </div>
                                    </div>
                                </div>
                            );
                        }
                        const identique =
                            mode.id !== MODES[0].id &&
                            reference &&
                            Math.abs(r.distanceM - reference.distanceM) /
                            reference.distanceM <
                            0.01;

                        return (
                            <div
                                key={mode.id}
                                role="button"
                                tabIndex={0}
                                className={
                                    'result-item' + (modeActif === mode.id ? ' active' : '')
                                }
                                onClick={() => onChoisirMode(mode.id)}
                                onKeyDown={(e: KeyboardEvent<HTMLDivElement>) => {
                                    if (e.key === 'Enter' || e.key === ' ') {
                                        e.preventDefault();
                                        onChoisirMode(mode.id);
                                    }
                                }}
                            >
                                <div className="result-icon">{mode.icone}</div>
                                <div className="result-info">
                                    <div className="result-name">{mode.label}</div>
                                    <div className="result-meta">
                                        <span className="result-distance">
                                            {formaterDuree(r.dureeS)}
                                        </span>
                                        <span>{formaterDistance(r.distanceM)}</span>
                                        {identique && (
                                            <span className="badge-same">
                                                Même chemin que la voiture
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
            </div>

            {/* Légende réseau */}
            <div className="legend-reseau">
                <div className="legend-title">Couverture réseau</div>
                <div className="legend-item">
                    <span
                        className="legend-swatch"
                        style={{ background: COULEUR_TECH['5g'] }}
                    />
                    <span>5G / 4G</span>
                </div>
                <div className="legend-item">
                    <span
                        className="legend-swatch"
                        style={{ background: COULEUR_TECH['3g'] }}
                    />
                    <span>3G</span>
                </div>
                <div className="legend-item">
                    <span
                        className="legend-swatch"
                        style={{ background: COULEUR_TECH['2g'] }}
                    />
                    <span>2G</span>
                </div>
                <div className="legend-item">
                    <span
                        className="legend-swatch"
                        style={{ background: COULEUR_TECH['none'] }}
                    />
                    <span>Aucun réseau</span>
                </div>
            </div>

            <div className="sidebar-foot">Itinéraires : OpenStreetMap · OSRM</div>
        </aside>
    );
}

/* ───────── Cadre la carte sur les lieux de la liste ───────── */

function VueLieux({ lieux, carte }: { lieux: LieuExterne[]; carte: CarteInfo | null }) {
    const map = useMap();

    useEffect(() => {
        if (!map) return;
        if (lieux.length > 1) {
            const bounds = new google.maps.LatLngBounds();
            lieux.forEach((l) => bounds.extend(l.position));
            map.fitBounds(bounds, 60);
            return;
        }
        const centre =
            lieux[0]?.position ??
            (carte?.centre
                ? { lat: carte.centre.latitude, lng: carte.centre.longitude }
                : null);
        if (!centre) return;
        map.setCenter(centre);
        map.setZoom(carte?.zoom_suggere ?? 13);
    }, [map, lieux, carte]);

    return null;
}

/* ───────── Composant principal ───────── */

function Carte({
    lieux = AUCUN_LIEU,
    carte = null,
    selected = null,
    demandeItineraire = 0,
    onSelect
}: CarteProps) {
    // 'recherche' = une seule barre en haut ; 'itineraire' = panneau latéral
    const [vue, setVue] = useState<'recherche' | 'itineraire'>('recherche');
    const [lieuRecherche, setLieuRecherche] = useState<Lieu | null>(null);
    const [selectionFermee, setSelectionFermee] = useState(false);
    const [ficheRepliee, setFicheRepliee] = useState(false);

    // Lieu choisi dans la liste de gauche, converti au format Lieu.
    const selId = selected?.id;
    const selLat = selected?.position.lat;
    const selLng = selected?.position.lng;
    const selNom = selected?.nom;
    const selSousTitre = selected?.sousTitre;
    const lieuSelectionne = useMemo<Lieu | null>(() => {
        if (
            selLat === undefined ||
            selLng === undefined ||
            selNom === undefined ||
            selectionFermee
        )
            return null;
        return {
            lat: selLat,
            lng: selLng,
            nom: selNom,
            libelle: selNom,
            adresse: selSousTitre ?? '',
            bbox: null
        };
    }, [selLat, selLng, selNom, selSousTitre, selectionFermee]);

    // Un nouveau clic dans la liste remplace la recherche en cours
    useEffect(() => {
        setLieuRecherche(null);
        setSelectionFermee(false);
        setFicheRepliee(false);
    }, [selId]);

    const lieu = lieuRecherche ?? lieuSelectionne;
    const setLieu = setLieuRecherche;

    const [resultats, setResultats] = useState<ResultatsParMode | null>(null);
    const [modeActif, setModeActif] = useState<ModeId | null>(null);
    const [points, setPoints] = useState<{ depart: Lieu; arrivee: Lieu } | null>(null);
    const [chargement, setChargement] = useState(false);
    const [erreur, setErreur] = useState<string | null>(null);
    const [typeCarte, setTypeCarte] = useState<'hybrid' | 'roadmap'>('hybrid');

    const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string;

    // Pré-charge les pylônes réseau dès l'ouverture
    useEffect(() => {
        chargerPylonesReseau()
            .then((data) => console.log(`${data.length} pylones reseau charges`))
            .catch((err) => console.warn('Pylones reseau indisponibles :', err.message));
    }, []);

    const handleRechercher = async (texteDepart: string, texteArrivee: string) => {
        setChargement(true);
        setErreur(null);
        setResultats(null);
        setPoints(null);

        try {
            // si la destination est le lieu déjà trouvé, on évite un nouveau géocodage
            const arrivee =
                lieu && texteArrivee === lieu.libelle ? lieu : await geocoder(texteArrivee);
            const depart = texteDepart
                ? await geocoder(texteDepart)
                : await positionActuelle();

            const reponses = await Promise.allSettled(
                MODES.map((m) => calculerItineraire(m, depart, arrivee))
            );

            const res: ResultatsParMode = {};
            MODES.forEach((m, i) => {
                const rep = reponses[i];
                if (rep.status === 'fulfilled') res[m.id] = rep.value;
            });

            const premier = MODES.find((m) => res[m.id]);
            if (!premier)
                throw new Error('Aucun itinéraire trouvé entre ces deux points.');

            setPoints({ depart, arrivee });
            setResultats(res);
            setModeActif(premier.id);
        } catch (err) {
            console.error('Erreur itinéraire :', err);
            setErreur(err instanceof Error ? err.message : 'Erreur inconnue.');
        } finally {
            setChargement(false);
        }
    };

    const handleEffacerItineraire = () => {
        setResultats(null);
        setModeActif(null);
        setPoints(null);
        setErreur(null);
    };

    const handleRetour = () => {
        handleEffacerItineraire();
        setVue('recherche');
    };

    const handleFermerLieu = () => {
        setLieu(null);
        setSelectionFermee(true);
    };

    // « Voir l'itinéraire » depuis le parent : ouvre le panneau d'itinéraire
    useEffect(() => {
        if (demandeItineraire && lieu) setVue('itineraire');
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [demandeItineraire]);

    const modeCourant = MODES.find((m) => m.id === modeActif);
    const traceCourante =
        resultats && modeActif ? resultats[modeActif]?.trace ?? null : null;

    return (
        <div className="carte-wrapper">
            <APIProvider apiKey={apiKey}>
                <Map
                    defaultZoom={12}
                    defaultCenter={CENTRE}
                    mapId="DEMO_MAP_ID"
                    mapTypeId={typeCarte}
                    gestureHandling="greedy"
                    disableDefaultUI={true}
                    style={{ width: '100%', height: '100%' }}
                >
                    {/* Résultats de la liste (pastilles numérotées) */}
                    {vue === 'recherche' &&
                        lieux.map((l, i) => {
                            if (lieuSelectionne && selId === l.id) return null; // déjà affiché par le repère rouge
                            return (
                                <AdvancedMarker
                                    key={`lieu-${l.id}`}
                                    position={l.position}
                                    title={l.nom}
                                    onClick={() => onSelect?.(l)}
                                    anchorPoint={AdvancedMarkerAnchorPoint.CENTER}
                                >
                                    <div
                                        style={{
                                            width: 30,
                                            height: 30,
                                            borderRadius: '50%',
                                            background: '#2f5fff',
                                            color: '#fff',
                                            border: `3px ${l.approximatif ? 'dashed' : 'solid'
                                                } #fff`,
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            fontWeight: 700,
                                            fontSize: 13,
                                            cursor: 'pointer',
                                            boxShadow:
                                                '0 4px 14px rgba(47, 95, 255, .5), 0 2px 6px rgba(0, 0, 0, .4)'
                                        }}
                                    >
                                        {i + 1}
                                    </div>
                                </AdvancedMarker>
                            );
                        })}
                    {vue === 'recherche' && !lieu && (
                        <VueLieux lieux={lieux} carte={carte} />
                    )}

                    {/* Lieu sélectionné ou trouvé par la recherche */}
                    {vue === 'recherche' && lieu && (
                        <>
                            <AdvancedMarker
                                position={{ lat: lieu.lat, lng: lieu.lng }}
                                title={lieu.libelle}
                                anchorPoint={AdvancedMarkerAnchorPoint.CENTER}
                            >
                                <div className="marker-pin marker-end">📍</div>
                            </AdvancedMarker>
                            <AllerA lieu={lieu} />
                        </>
                    )}

                    {/* Itinéraire */}
                    {vue === 'itineraire' && points && (
                        <>
                            <AdvancedMarker
                                position={{
                                    lat: points.depart.lat,
                                    lng: points.depart.lng
                                }}
                                title="Départ"
                                anchorPoint={AdvancedMarkerAnchorPoint.CENTER}
                            >
                                <div className="marker-pin marker-start" />
                            </AdvancedMarker>
                            <AdvancedMarker
                                position={{
                                    lat: points.arrivee.lat,
                                    lng: points.arrivee.lng
                                }}
                                title="Destination"
                                anchorPoint={AdvancedMarkerAnchorPoint.CENTER}
                            >
                                <div className="marker-pin marker-end">📍</div>
                            </AdvancedMarker>
                        </>
                    )}

                    {/* Polyligne multicolore selon couverture réseau */}
                    {vue === 'itineraire' && traceCourante && modeCourant && (
                        <>
                            <Trace path={traceCourante} />
                            <AjusterVue path={traceCourante} />
                        </>
                    )}
                </Map>

                {/* Contrôles de zoom (bas droite) */}
                <ZoomControls
                    typeCarte={typeCarte}
                    onToggleType={() =>
                        setTypeCarte((t) => (t === 'hybrid' ? 'roadmap' : 'hybrid'))
                    }
                />
            </APIProvider>

            {/* Fiche lieu (repliable) */}
            {vue === 'recherche' && lieu && (
                <FicheLieu
                    lieu={lieu}
                    onItineraire={() => setVue('itineraire')}
                    onFermer={handleFermerLieu}
                    repliee={ficheRepliee}
                    onToggleReplie={() => setFicheRepliee((v) => !v)}
                />
            )}

            {/* Panneau itinéraire (sidebar tiroir) */}
            {vue === 'itineraire' && (
                <Panneau
                    arriveeInitiale={lieu ? lieu.libelle : ''}
                    onRechercher={handleRechercher}
                    onEffacer={handleEffacerItineraire}
                    onRetour={handleRetour}
                    resultats={resultats}
                    modeActif={modeActif}
                    onChoisirMode={setModeActif}
                    chargement={chargement}
                    erreur={erreur}
                    destination={points ? points.arrivee.libelle : ''}
                />
            )}
        </div>
    );
}

export default Carte;