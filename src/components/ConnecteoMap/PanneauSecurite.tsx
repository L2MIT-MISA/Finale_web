import { useEffect, useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { MOCK_SECURITY_DATA } from './mockSecurityData';
import type { Lieu, SecurityData } from './types';
import './style/PanneauSecurite.css';

/* ============================================================
   PanneauSecurite : AFFICHAGE uniquement.
   Props :
     lieu            Lieu (requis)
     securityData    objet au format de mockSecurityData.ts     (optionnel)
     chargement      boolean (optionnel)
     erreur          string  (optionnel)
     onRetour        () => void  (optionnel)
     onItineraire    () => void  (optionnel)
     integre         boolean (optionnel)
     replie          boolean (optionnel) — contrôle externe du repli
     onToggleReplie  () => void (optionnel) — callback de toggle
   ============================================================ */

/* ───────── Utilitaires ───────── */

type ToneKey = 'good' | 'ok' | 'mid' | 'bad' | 'none';

interface Tone {
    key: ToneKey;
    label: string;
}

const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

function formatDistance(m?: number | null): string {
    if (!isNum(m)) return '—';
    return m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(1)} km`;
}

function formatPercent(v?: number): string {
    return isNum(v) ? `${Math.round(v)}%` : '—';
}

function clampPercent(v?: number): number {
    return isNum(v) ? Math.max(0, Math.min(100, v)) : 0;
}

// 80-100 vert · 60-79 jaune · 40-59 orange · 0-39 rouge
function getTone(score?: number): Tone {
    if (!isNum(score)) return { key: 'none', label: 'Indisponible' };
    if (score >= 80) return { key: 'good', label: 'Bon' };
    if (score >= 60) return { key: 'ok', label: 'Correct' };
    if (score >= 40) return { key: 'mid', label: 'Moyen' };
    return { key: 'bad', label: 'Faible' };
}

function getLevelTone(level?: string): ToneKey {
    const n = String(level || '')
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');
    if (['elevee', 'haute', 'high', 'bonne', 'good'].includes(n)) return 'good';
    if (['moyenne', 'medium'].includes(n)) return 'ok';
    if (['faible', 'basse', 'low'].includes(n)) return 'bad';
    return 'none';
}

function pluralize(n: number, singulier: string, pluriel: string): string {
    return n > 1 ? pluriel : singulier;
}

/* ───────── Hooks d'animation ───────── */

// Compte de 0 vers la valeur cible (désactivé si prefers-reduced-motion)
function useAnimatedNumber(target: number | undefined, duration = 900): number {
    const [value, setValue] = useState(0);

    useEffect(() => {
        if (!isNum(target)) {
            setValue(0);
            return undefined;
        }
        const reduit = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
        if (reduit) {
            setValue(target);
            return undefined;
        }
        let raf = 0;
        let debut: number | undefined;
        const pas = (t: number) => {
            if (debut === undefined) debut = t;
            const p = Math.min(1, (t - debut) / duration);
            const eased = 1 - Math.pow(1 - p, 3);
            setValue(Math.round(target * eased));
            if (p < 1) raf = requestAnimationFrame(pas);
        };
        raf = requestAnimationFrame(pas);
        return () => cancelAnimationFrame(raf);
    }, [target, duration]);

    return value;
}

// Passe à true juste après le montage pour déclencher les transitions CSS
function useReady(dep: unknown): boolean {
    const [ready, setReady] = useState(false);
    useEffect(() => {
        setReady(false);
        const id = setTimeout(() => setReady(true), 40);
        return () => clearTimeout(id);
    }, [dep]);
    return ready;
}

/* ───────── Icônes SVG ───────── */

const ICONS = {
    shield: (
        <>
            <path d="M12 3l8 3v6c0 5-3.4 8-8 9-4.6-1-8-4-8-9V6z" />
            <path d="M9 12l2 2 4-4" />
        </>
    ),
    police: (
        <>
            <path d="M12 3l8 3v6c0 5-3.4 8-8 9-4.6-1-8-4-8-9V6z" />
            <path d="M12 8.5l1.2 2.4 2.6.4-1.9 1.8.5 2.6-2.4-1.3-2.4 1.3.5-2.6-1.9-1.8 2.6-.4z" />
        </>
    ),
    hospital: (
        <>
            <rect x="4" y="4" width="16" height="16" rx="3" />
            <path d="M12 8v8M8 12h8" />
        </>
    ),
    emergency: <path d="M3 12h4l2-5 4 10 2-5h6" />,
    pharmacy: (
        <>
            <rect x="3" y="9" width="18" height="6" rx="3" transform="rotate(-45 12 12)" />
            <path d="M9.5 9.5l5 5" />
        </>
    ),
    mobile: (
        <>
            <rect x="7" y="2.5" width="10" height="19" rx="2" />
            <path d="M11 18.5h2" />
        </>
    ),
    wifi: (
        <>
            <path d="M5 12.5a10 10 0 0 1 14 0M8 15.5a6 6 0 0 1 8 0" />
            <circle cx="12" cy="19" r="1" />
        </>
    ),
    lora: (
        <>
            <circle cx="12" cy="12" r="2" />
            <path d="M7.8 7.8a6 6 0 0 0 0 8.4M16.2 7.8a6 6 0 0 1 0 8.4M4.9 4.9a10 10 0 0 0 0 14.2M19.1 4.9a10 10 0 0 1 0 14.2" />
        </>
    ),
    road: <path d="M8 3L5 21M16 3l3 18M12 4v3M12 10.5v3M12 17v3" />,
    refresh: (
        <>
            <path d="M20 12a8 8 0 0 1-14 5.3M4 12a8 8 0 0 1 14-5.3" />
            <path d="M18 3v4h-4M6 21v-4h4" />
        </>
    ),
    back: <path d="M19 12H5M11 6l-6 6 6 6" />,
    arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
    chevronDown: <path d="M6 9l6 6 6-6" />,
    chevronUp: <path d="M6 15l6-6 6 6" />
} satisfies Record<string, ReactElement>;

type IconName = keyof typeof ICONS;

function Icon({ name, className = 'secu-icon' }: { name: IconName; className?: string }) {
    return (
        <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
            {ICONS[name]}
        </svg>
    );
}

/* ───────── Petits composants ───────── */

const RAYON = 54;
const CIRCONFERENCE = 2 * Math.PI * RAYON;

function ScoreRing({ score, tone }: { score?: number; tone: Tone }) {
    const ready = useReady(score);
    const affiche = useAnimatedNumber(score);
    const safe = clampPercent(score);
    const offset = ready ? CIRCONFERENCE * (1 - safe / 100) : CIRCONFERENCE;

    return (
        <div className={`secu-ring tone-${tone.key}`}>
            <svg
                viewBox="0 0 140 140"
                role="img"
                aria-label={isNum(score) ? `Score de sécurité : ${safe} sur 100, ${tone.label}` : 'Score indisponible'}
            >
                <circle className="secu-ring-track" cx="70" cy="70" r={RAYON} />
                <circle
                    className="secu-ring-value"
                    cx="70"
                    cy="70"
                    r={RAYON}
                    strokeDasharray={CIRCONFERENCE}
                    strokeDashoffset={offset}
                />
            </svg>
            <div className="secu-ring-center">
                <Icon name="shield" className="secu-icon secu-ring-shield" />
                <div className="secu-ring-value-line">
                    <span className="secu-ring-num">{isNum(score) ? affiche : '—'}</span>
                    {isNum(score) && <span className="secu-ring-max"> / 100</span>}
                </div>
            </div>
        </div>
    );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
    return (
        <section className="secu-section">
            <h3 className="secu-section-title">{title}</h3>
            {children}
        </section>
    );
}

interface ServiceCardProps {
    icon: IconName;
    title: string;
    main: ReactNode;
    sub?: ReactNode;
    aside?: ReactNode;
}

function ServiceCard({ icon, title, main, sub, aside }: ServiceCardProps) {
    return (
        <div className="secu-card">
            <div className="secu-card-icon">
                <Icon name={icon} />
            </div>
            <div className="secu-card-info">
                <div className="secu-card-title">{title}</div>
                <div className="secu-card-main">{main}</div>
                {sub && <div className="secu-card-sub">{sub}</div>}
            </div>
            {aside}
        </div>
    );
}

function LevelPill({ level }: { level?: string }) {
    return <span className={`secu-pill tone-${getLevelTone(level)}`}>{level || '—'}</span>;
}

function Meter({ icon, label, value }: { icon?: IconName; label: string; value?: number }) {
    const ready = useReady(value);
    const tone = getTone(value);
    return (
        <div className={`secu-meter tone-${tone.key}`}>
            <div className="secu-meter-head">
                {icon && <Icon name={icon} />}
                <span className="secu-meter-label">{label}</span>
                <span className="secu-meter-value">{formatPercent(value)}</span>
            </div>
            <div
                className="secu-meter-track"
                role="progressbar"
                aria-label={label}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={isNum(value) ? Math.round(value) : undefined}
            >
                <div className="secu-meter-fill" style={{ width: ready ? `${clampPercent(value)}%` : '0%' }} />
            </div>
        </div>
    );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
    return (
        <div className="secu-row">
            <span className="secu-row-label">{label}</span>
            <span className="secu-row-value">{children}</span>
        </div>
    );
}

function Squelette() {
    return (
        <div className="secu-skeleton" aria-busy="true" aria-label="Chargement des données de sécurité">
            <div className="secu-skel secu-skel-score" />
            <div className="secu-skel" />
            <div className="secu-skel" />
            <div className="secu-skel" />
        </div>
    );
}

/* ───────── Composant principal ───────── */

interface PanneauSecuriteProps {
    lieu: Lieu | null;
    securityData?: SecurityData | null;
    chargement?: boolean;
    erreur?: string | null;
    onRetour?: () => void;
    onItineraire?: () => void;
    /** true = affiché dans une section existante (sans position flottante ni en-tête) */
    integre?: boolean;
    /** Contrôle externe du repli (optionnel) */
    replie?: boolean;
    /** Callback de toggle (optionnel) */
    onToggleReplie?: () => void;
}

function PanneauSecurite({
    lieu,
    securityData,
    chargement = false,
    erreur = null,
    onRetour,
    onItineraire,
    integre = false,
    replie: replieControle,
    onToggleReplie
}: PanneauSecuriteProps) {
    const [replieInterne, setReplieInterne] = useState(false);

    // Mode contrôlé si le parent fournit `replie`
    const replie = replieControle ?? replieInterne;
    const toggleReplie = () => {
        if (onToggleReplie) onToggleReplie();
        else setReplieInterne((v) => !v);
    };

    // un nouveau lieu redéploie le panneau (uniquement en mode non contrôlé)
    const cle = lieu ? `${lieu.lat},${lieu.lng}` : '';
    useEffect(() => {
        if (replieControle === undefined) setReplieInterne(false);
    }, [cle, replieControle]);

    if (!lieu) return null;

    const data: SecurityData = securityData ?? MOCK_SECURITY_DATA;
    const estDemo = securityData ? securityData.isDemo === true : true;
    // Pendant le chargement ou en cas d'erreur, on n'affiche pas la mention « démonstration »
    const enAttente = chargement || Boolean(erreur);
    const tone = getTone(data.score);

    const { police, hospitals, emergency, pharmacies, connectivity, accessibility, resilience } = data;
    const adresse = lieu.adresse || lieu.nom;

    return (
        <aside
            className={'secu-panel' + (integre ? ' secu-integre' : '') + (replie ? ' replie' : '')}
            aria-label={`Sécurité de ${lieu.libelle}`}
        >
            <header className="secu-head">
                {onRetour && (
                    <button
                        type="button"
                        className="secu-btn-round"
                        onClick={onRetour}
                        aria-label="Fermer le panneau de sécurité"
                        title="Retour"
                    >
                        <Icon name="back" />
                    </button>
                )}
                <div className="secu-head-text">
                    <div className="secu-kicker">
                        <Icon name="shield" />
                        Sécurité
                    </div>
                    <h2 className="secu-place">{lieu.libelle}</h2>
                    {adresse && <div className="secu-addr">{adresse}</div>}
                </div>
                <button
                    type="button"
                    className="secu-btn-round secu-toggle"
                    onClick={toggleReplie}
                    aria-label={replie ? 'Déplier le panneau' : 'Replier le panneau'}
                    aria-expanded={!replie}
                >
                    <Icon name={replie ? 'chevronUp' : 'chevronDown'} className="secu-icon" />
                </button>
            </header>

            <div className="secu-body">
                {chargement && <Squelette />}

                {!chargement && erreur && <div className="secu-error">{erreur}</div>}

                {!chargement && !erreur && (
                    <>
                        {/* ─── Score global ─── */}
                        <div className={`secu-score tone-${tone.key}`}>
                            <ScoreRing score={data.score} tone={tone} />
                            <div className="secu-score-label">{tone.label}</div>
                            <p className="secu-score-note">
                                Indice calculé à partir des infrastructures et services disponibles.
                            </p>
                        </div>

                        {/* ─── 1. Services de sécurité ─── */}
                        <Section title="Services de sécurité">
                            <ServiceCard
                                icon="police"
                                title="Police / Gendarmerie"
                                main={
                                    isNum(police?.count)
                                        ? `${police.count} ${pluralize(police.count, 'poste', 'postes')} à proximité`
                                        : 'Donnée indisponible'
                                }
                                sub={
                                    <>
                                        Plus proche : {formatDistance(police?.nearestDistance)}
                                        {police?.availability && <> · Disponibilité : {police.availability}</>}
                                    </>
                                }
                            />
                        </Section>

                        {/* ─── 2. Services médicaux ─── */}
                        <Section title="Services médicaux">
                            <ServiceCard
                                icon="hospital"
                                title="Hôpitaux"
                                main={
                                    isNum(hospitals?.count)
                                        ? `${hospitals.count} ${pluralize(hospitals.count, 'hôpital', 'hôpitaux')}`
                                        : 'Donnée indisponible'
                                }
                                sub={`Plus proche : ${formatDistance(hospitals?.nearestDistance)}`}
                            />
                            {emergency && (
                                <ServiceCard
                                    icon="emergency"
                                    title="Urgences"
                                    main={
                                        emergency.availability
                                            ? `Disponibilité : ${emergency.availability}`
                                            : "Niveau d'accès"
                                    }
                                    aside={<LevelPill level={emergency.access} />}
                                />
                            )}
                            <ServiceCard
                                icon="pharmacy"
                                title="Pharmacies"
                                main={
                                    isNum(pharmacies?.count)
                                        ? `${pharmacies.count} ${pluralize(pharmacies.count, 'pharmacie proche', 'pharmacies proches')}`
                                        : 'Donnée indisponible'
                                }
                                sub={
                                    isNum(pharmacies?.nearestDistance)
                                        ? `Plus proche : ${formatDistance(pharmacies.nearestDistance)}`
                                        : null
                                }
                            />
                        </Section>

                        {/* ─── 3. Connectivité ─── */}
                        {connectivity && (
                            <Section title="Connectivité">
                                <div className="secu-block">
                                    <Meter icon="mobile" label="Réseau mobile" value={connectivity.mobile} />
                                    <Meter icon="wifi" label="Internet" value={connectivity.internet} />
                                    <Meter icon="lora" label="LoRa" value={connectivity.lora} />
                                </div>
                            </Section>
                        )}

                        {/* ─── 4. Accessibilité ─── */}
                        <Section title="Accessibilité">
                            <div className="secu-block">
                                {isNum(accessibility?.roads) && (
                                    <Meter icon="road" label="Routes accessibles" value={accessibility.roads} />
                                )}
                                <div className="secu-rows">
                                    <Row label="Police la plus proche">{formatDistance(police?.nearestDistance)}</Row>
                                    <Row label="Hôpital le plus proche">
                                        {formatDistance(hospitals?.nearestDistance)}
                                    </Row>
                                    {isNum(accessibility?.emergencyTime) && (
                                        <Row label="Intervention estimée">
                                            {`${Math.round(accessibility.emergencyTime)} min`}
                                        </Row>
                                    )}
                                </div>
                            </div>
                        </Section>

                        {/* ─── 5. Résilience ─── */}
                        {resilience && (
                            <Section title="Résilience">
                                <div className="secu-block">
                                    <p className="secu-text">
                                        <Icon name="refresh" /> Capacité de la zone à rester fonctionnelle si un
                                        service tombe en panne.
                                    </p>
                                    <div className="secu-rows">
                                        <Row label="Connectivité redondante">
                                            <LevelPill level={resilience.connectivity} />
                                        </Row>
                                        <Row label="Services médicaux">
                                            <LevelPill level={resilience.medical} />
                                        </Row>
                                        <Row label="Routes alternatives">
                                            <LevelPill level={resilience.alternatives} />
                                        </Row>
                                    </div>
                                </div>
                            </Section>
                        )}
                    </>
                )}
            </div>

            <footer className="secu-foot">
                {!enAttente &&
                    (estDemo ? (
                        <span className="secu-demo">
                            <span className="secu-demo-dot" />
                            Données de démonstration
                        </span>
                    ) : (
                        <span>Indice informatif, non scientifique</span>
                    ))}
                {onItineraire && (
                    <button type="button" className="secu-btn-primary" onClick={onItineraire}>
                        <Icon name="arrow" className="secu-icon" />
                        Itinéraire
                    </button>
                )}
            </footer>
        </aside>
    );
}

export default PanneauSecurite;