import { useEffect, useMemo, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import "./DownloadPage.css";

/* ------------------------------------------------------------------ *
 * 1. CONFIGURATION — fichiers d'installation directe et textes
 *    `file` = chemin du fichier servi par VOTRE site (dossier public/).
 * ------------------------------------------------------------------ */
export interface Platform {
  id: string;
  name: string;
  requirement: string;
  file: string;
  fileName?: string;
  buttonLabel?: string;
  /** Mention affichée sous le nom, ex. "APK • installation directe" */
  format?: string;
}

export const DEFAULT_PLATFORMS: Platform[] = [
  {
    id: "android",
    name: "Android",
    requirement: "Android 5.0 ou version ultérieure",
    file: "/downloads/connecteo.apk",
    fileName: "connecteo.apk",
    buttonLabel: "Télécharger l'APK",
    format: "Fichier APK • installation directe",
  },
  {
    id: "ios",
    name: "iOS",
    requirement: "iOS 13.0 ou version ultérieure",
    file: "/downloads/connecteo.ipa",
    fileName: "connecteo.ipa",
    buttonLabel: "Télécharger le fichier iOS",
    format: "Fichier IPA • installation directe",
  },
  {
    id: "harmonyos",
    name: "HarmonyOS",
    requirement: "HarmonyOS 2.0 ou version ultérieure",
    file: "/downloads/connecteo.hap",
    fileName: "connecteo.hap",
    buttonLabel: "Télécharger le fichier HarmonyOS",
    format: "Fichier HAP • installation directe",
  },
];

/* ------------------------------------------------------------------ *
 * 2. DÉTECTION DU SYSTÈME
 * ------------------------------------------------------------------ */
interface NavigatorLike {
  userAgent?: string;
  platform?: string;
  maxTouchPoints?: number;
}

export function detectPlatform(nav?: NavigatorLike | null): string | null {
  const n = nav ?? (typeof navigator !== "undefined" ? navigator : null);
  if (!n) return null;
  const ua = n.userAgent || "";

  // HarmonyOS doit être testé AVANT Android (son UA contient souvent "Android")
  if (/HarmonyOS|OpenHarmony|ArkWeb|HMSCore|HuaweiBrowser/i.test(ua)) {
    return "harmonyos";
  }
  if (/Android/i.test(ua)) return "android";
  // iPadOS 13+ se présente comme un Mac : on vérifie l'écran tactile
  if (
    /iPhone|iPad|iPod/i.test(ua) ||
    (n.platform === "MacIntel" && (n.maxTouchPoints ?? 0) > 1)
  ) {
    return "ios";
  }
  return null;
}

/** Hook : détecte la plateforme côté client (compatible SSR). */
export function usePlatform() {
  const [platform, setPlatform] = useState<string | null>(null);
  useEffect(() => setPlatform(detectPlatform()), []);
  return platform;
}

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ------------------------------------------------------------------ *
 * 3. ICÔNES (stroke, style du site)
 * ------------------------------------------------------------------ */
const stroke = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

function PlatformIcon({ id }: { id: string }) {
  if (id === "android") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="7" y="3" width="10" height="18" rx="2.5" {...stroke} />
        <path d="M11 18h2" {...stroke} />
      </svg>
    );
  }
  if (id === "ios") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="7" y="3" width="10" height="18" rx="2.5" {...stroke} />
        <circle cx="12" cy="17.5" r="1" fill="currentColor" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8" {...stroke} />
      <path d="M12 4v16M4 12h16" {...stroke} />
    </svg>
  );
}

const DownloadIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" className="dl-btn__icon">
    <path d="M12 4v10m0 0-4-4m4 4 4-4M5 19h14" {...stroke} />
  </svg>
);

const CheckIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" className="dl-note__icon">
    <circle cx="12" cy="12" r="9" {...stroke} />
    <path d="m8 12.5 2.7 2.7L16 9.5" {...stroke} />
  </svg>
);

/* ------------------------------------------------------------------ *
 * 4. CONTENUS — bénéfices et FAQ (ton "bénéfice", pas "fonctionnalité")
 * ------------------------------------------------------------------ */
const BENEFITS = [
  {
    title: "Hors ligne d'abord",
    text: "Cartes, lieux et infos essentielles restent accessibles même quand le réseau disparaît.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M2 2l20 20M8.5 16.4a5 5 0 0 1 7 0M2 8.8a15 15 0 0 1 4.2-2.6M10.7 5.1A15 15 0 0 1 22 8.8M5 12.9a10 10 0 0 1 3-1.9M13 11a10 10 0 0 1 6 1.9M12 20h.01" />
      </svg>
    ),
  },
  {
    title: "Données locales vérifiées",
    text: "Lieux, services et contacts utiles, vérifiés à Madagascar — pas de résultats au hasard.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 21s-7-4.6-9.3-9A5.3 5.3 0 0 1 12 6a5.3 5.3 0 0 1 9.3 6c-2.3 4.4-9.3 9-9.3 9Z" />
        <circle cx="12" cy="11" r="2" />
      </svg>
    ),
  },
  {
    title: "Urgences 24h/24",
    text: "Signalez un problème et recevez de l'aide à toute heure, où que vous soyez sur l'île.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z" />
      </svg>
    ),
  },
];

const FAQS = [
  {
    q: "L'application est-elle vraiment gratuite ?",
    a: "Oui. Le téléchargement et l'utilisation sont entièrement gratuits, sans compte et sans abonnement.",
  },
  {
    q: "Fonctionne-t-elle sans connexion internet ?",
    a: "Oui. Les cartes, les lieux enregistrés et les infos essentielles restent accessibles hors ligne. Seules les recherches les plus détaillées demandent une connexion.",
  },
  {
    q: "Mon téléphone est-il compatible ?",
    a: "Connectéo fonctionne sur Android 5.0 ou version ultérieure, iOS 13 ou version ultérieure, et HarmonyOS 2.0 ou version ultérieure.",
  },
  {
    q: "Comment installer le fichier sur Android ?",
    a: "Téléchargez le fichier APK, ouvrez-le, puis autorisez « Installer depuis cette source » si votre téléphone le demande. L'icône Connectéo apparaît ensuite sur votre écran d'accueil.",
  },
];

const INSTALL_STEPS = [
  {
    title: "Téléchargez le fichier",
    text: "Choisissez la version adaptée à votre téléphone ci-dessus.",
  },
  {
    title: "Ouvrez le fichier",
    text: "Sur Android, autorisez l'installation depuis cette source si le téléphone le demande.",
  },
  {
    title: "Retrouvez Connectéo",
    text: "L'icône apparaît sur votre écran d'accueil, prête à vous guider.",
  },
];

/* ------------------------------------------------------------------ *
 * 5. SECTIONS
 * ------------------------------------------------------------------ */
function Hero({
  appName,
  detected,
  platforms,
}: {
  appName: string;
  detected: string | null;
  platforms: Platform[];
}) {
  const current = platforms.find((p) => p.id === detected) ?? null;
  return (
    <section className="dl-hero">
      <div className="dl-container dl-hero__grid">
        <div className="dl-hero__copy">
          <p className="dl-eyebrow">Application gratuite</p>
          <h1 className="dl-hero__title">Emportez Madagascar dans votre poche.</h1>
          <p className="dl-hero__sub">
            {appName} vous guide 24h/24, même sans connexion : lieux, services
            et urgences, partout sur l&apos;île.
          </p>
          <div className="dl-hero__cta-row">
            {current ? (
              <a className="dl-hero__cta" href={current.file} download={current.fileName ?? true}>
                <DownloadIcon />
                Télécharger pour {current.name}
              </a>
            ) : (
              <button type="button" className="dl-hero__cta" onClick={() => scrollToId("dl-platforms")}>
                <DownloadIcon />
                Choisir ma version
              </button>
            )}
          </div>
          <ul className="dl-chips" aria-label="Points forts">
            <li className="dl-chip">Gratuite</li>
            <li className="dl-chip">Hors ligne</li>
            <li className="dl-chip">24h/24</li>
          </ul>
          <p className="dl-hero__note">Android • iOS • HarmonyOS — sans compte requis</p>
        </div>
        <div className="dl-hero__visual">
          <div className="dl-phone" role="img" aria-label={`Aperçu de l'application ${appName}`}>
            <div className="dl-phone__notch" />
            <div className="dl-phone__screen">
              <div className="dl-phone__top">
                <span className="dl-phone__dot" />
                <span>{appName}</span>
              </div>
              <div className="dl-phone__search">
                <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="11" cy="11" r="7" />
                  <path d="m20 20-3.5-3.5" />
                </svg>
                Pharmacie à proximité
              </div>
              <svg className="dl-phone__map" viewBox="0 0 230 190" aria-hidden="true">
                <defs>
                  <radialGradient id="dl-glow" cx="50%" cy="50%" r="50%">
                    <stop offset="0" stopColor="#38bdf8" stopOpacity=".45" />
                    <stop offset="1" stopColor="#38bdf8" stopOpacity="0" />
                  </radialGradient>
                </defs>
                <circle cx="115" cy="95" r="85" fill="url(#dl-glow)" />
                <line x1="90" y1="60" x2="140" y2="45" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
                <line x1="140" y1="45" x2="180" y2="88" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
                <line x1="180" y1="88" x2="158" y2="132" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
                <line x1="116" y1="108" x2="158" y2="132" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
                <line x1="90" y1="60" x2="116" y2="108" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
                <line x1="116" y1="108" x2="80" y2="140" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
                <circle cx="90" cy="60" r="5" fill="#ffd166" />
                <circle cx="140" cy="45" r="3.5" fill="#7dd3fc" />
                <circle cx="180" cy="88" r="3.5" fill="#7dd3fc" />
                <circle cx="116" cy="108" r="5" fill="#ffd166" />
                <circle cx="158" cy="132" r="3.5" fill="#7dd3fc" />
                <circle cx="80" cy="140" r="3.5" fill="#7dd3fc" />
              </svg>
              <div className="dl-phone__card">
                <strong>Centre de santé</strong>
                <span>À 1,2 km · Ouvert</span>
              </div>
            </div>
          </div>
          <span className="dl-float dl-float--left">Accès hors ligne</span>
          <span className="dl-float dl-float--right">Données locales</span>
        </div>
      </div>
    </section>
  );
}

function PlatformCard({ platform: p, current }: { platform: Platform; current: boolean }) {
  return (
    <li className={`dl-card${current ? " dl-card--current" : ""}`}>
      <span className="dl-card__logo" aria-hidden="true">
        <PlatformIcon id={p.id} />
      </span>
      <h3 className="dl-card__name">
        {p.name}
        {current && <span className="dl-card__you">Votre appareil</span>}
      </h3>
      <p className="dl-card__req">{p.requirement}</p>
      <p className="dl-card__format">{p.format ?? "Fichier d'installation directe"}</p>
      <a className="dl-btn" href={p.file} download={p.fileName ?? true}>
        <DownloadIcon />
        {p.buttonLabel ?? "Télécharger"}
      </a>
    </li>
  );
}

function PlatformsSection({
  platforms,
  current,
  titleId,
}: {
  platforms: Platform[];
  current: string | null;
  titleId: string;
}) {
  return (
    <section className="dl-platforms" id="dl-platforms" aria-labelledby={titleId}>
      <div className="dl-container">
        <p className="dl-eyebrow">Fichiers officiels et gratuits</p>
        <h2 id={titleId} className="dl-title">Choisissez votre version</h2>
        <p className="dl-subtitle">
          Téléchargement direct depuis notre site, sans boutique et sans compte.
        </p>
        <ul className="dl-grid" data-count={platforms.length}>
          {platforms.map((p) => (
            <PlatformCard key={p.id} platform={p} current={current === p.id} />
          ))}
        </ul>
      </div>
    </section>
  );
}

function Benefits() {
  return (
    <section className="dl-benefits" aria-label="Pourquoi télécharger l'application">
      <div className="dl-container">
        <ul className="dl-benefits__grid">
          {BENEFITS.map((b) => (
            <li key={b.title} className="dl-benefit">
              <span className="dl-benefit__icon" aria-hidden="true">{b.icon}</span>
              <h3>{b.title}</h3>
              <p>{b.text}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function QrInstall({ appName, qrValue }: { appName: string; qrValue: string }) {
  return (
    <section className="dl-qr" aria-labelledby="dl-qr-title">
      <div className="dl-container dl-qr__inner">
        <div className="dl-qr__box">
          <QRCodeSVG
            value={qrValue}
            size={132}
            level="M"
            bgColor="#ffffff"
            fgColor="#0b1048"
            title={`QR code de téléchargement ${appName}`}
          />
          <p className="dl-qr__caption">Scannez avec votre téléphone</p>
        </div>
        <div className="dl-qr__text">
          <p className="dl-eyebrow dl-eyebrow--left">Installation en 1 minute</p>
          <h2 id="dl-qr-title" className="dl-title dl-title--left">
            Scannez. Installez. Partez.
          </h2>
          <ol className="dl-steps">
            {INSTALL_STEPS.map((s, i) => (
              <li key={s.title}>
                <span className="dl-steps__num" aria-hidden="true">{i + 1}</span>
                <div>
                  <strong>{s.title}</strong>
                  <p>{s.text}</p>
                </div>
              </li>
            ))}
          </ol>
          <p className="dl-note">
            <CheckIcon />
            Application officielle {appName}, téléchargement sécurisé
          </p>
        </div>
      </div>
    </section>
  );
}

function Faq() {
  return (
    <section className="dl-faq" aria-labelledby="dl-faq-title">
      <div className="dl-container dl-faq__inner">
        <p className="dl-eyebrow">Questions fréquentes</p>
        <h2 id="dl-faq-title" className="dl-title">Ce que vous vous demandez</h2>
        <div className="dl-faq__list">
          {FAQS.map((f) => (
            <details key={f.q} className="dl-faq__item">
              <summary>{f.q}</summary>
              <p>{f.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCta({
  detected,
  platforms,
}: {
  detected: string | null;
  platforms: Platform[];
}) {
  const current = platforms.find((p) => p.id === detected) ?? null;
  return (
    <section className="dl-final" aria-label="Appel final au téléchargement">
      <div className="dl-container">
        <div className="dl-final__card">
          <h2>Prêt à explorer Madagascar ?</h2>
          <p>Gratuite, hors ligne, disponible 24h/24 — en moins d&apos;une minute sur votre téléphone.</p>
          {current ? (
            <a className="dl-hero__cta" href={current.file} download={current.fileName ?? true}>
              <DownloadIcon />
              Télécharger pour {current.name}
            </a>
          ) : (
            <button type="button" className="dl-hero__cta" onClick={() => scrollToId("dl-platforms")}>
              <DownloadIcon />
              Choisir ma version
            </button>
          )}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ *
 * 6. COMPOSANT PRINCIPAL — page « Télécharger » du site
 * ------------------------------------------------------------------ */
export interface DownloadPageProps {
  platforms?: Platform[];
  appName?: string;
  redirectPath?: string;
  qrUrl?: string;
  mode?: "all" | "filter";
  highlight?: boolean;
  showQr?: boolean;
  className?: string;
}

export default function DownloadPage({
  platforms = DEFAULT_PLATFORMS,
  appName = "Connectéo",
  redirectPath = "/telecharger/auto",
  qrUrl,
  mode = "all",
  highlight = true,
  showQr = true,
  className = "",
}: DownloadPageProps) {
  const detected = usePlatform();

  const visible = useMemo(() => {
    if (mode === "filter" && detected) {
      const match = platforms.filter((p) => p.id === detected);
      return match.length ? match : platforms;
    }
    return platforms;
  }, [mode, detected, platforms]);

  const qrValue = useMemo(() => {
    if (qrUrl) return qrUrl;
    if (typeof window === "undefined") return redirectPath;
    return `${window.location.origin}${redirectPath}`;
  }, [qrUrl, redirectPath]);

  return (
    <div className={`dl-root ${className}`.trim()}>
      <Hero appName={appName} detected={detected} platforms={platforms} />
      <PlatformsSection
        platforms={visible}
        current={highlight ? detected : null}
        titleId="dl-title"
      />
      <Benefits />
      {showQr && <QrInstall appName={appName} qrValue={qrValue} />}
      <Faq />
      <FinalCta detected={detected} platforms={platforms} />
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * 7. PAGE OUVERTE PAR LE QR CODE
 * ------------------------------------------------------------------ */
export function DownloadForDevice({
  platforms = DEFAULT_PLATFORMS,
  className = "",
}: {
  platforms?: Platform[];
  className?: string;
}) {
  const [detected, setDetected] = useState<string | null | undefined>(undefined);

  useEffect(() => setDetected(detectPlatform()), []);

  if (detected === undefined) {
    return (
      <div className={`dl-root dl-wait ${className}`.trim()} role="status">
        Détection de votre appareil…
      </div>
    );
  }

  const match = platforms.filter((p) => p.id === detected);
  const list = match.length ? match : platforms;

  return (
    <div className={`dl-root ${className}`.trim()}>
      <PlatformsSection
        platforms={list}
        current={null}
        titleId="dl-device-title"
      />
    </div>
  );
}
