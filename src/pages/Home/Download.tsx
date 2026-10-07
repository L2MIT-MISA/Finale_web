import { useLang } from "../../i18n/LanguageContext";

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function Download() {
  const { t } = useLang();
  const d = t.downloadSection;
  return (
    <section className="app" id="telecharger">
      <div className="app__circle" aria-hidden="true" />

      <div className="app__grid">
      <div className="app__copy">
        <span className="dash" aria-hidden="true" />
        <h2 className="app__title">{d.title}</h2>
        <p className="app__text">
          {d.text}
        </p>

        <ul className="tags">
          <li className="tag">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="3" y="8" width="18" height="4" rx="1" />
              <path d="M12 8v13M5 12v8h14v-8M12 8s-1-4-4-4a2 2 0 0 0 0 4h4Zm0 0s1-4 4-4a2 2 0 0 1 0 4h-4Z" />
            </svg>
            {d.tags[0] ?? "Gratuite"}
          </li>
          <li className="tag">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z" />
            </svg>
            {d.tags[1] ?? "Hors ligne"}
          </li>
          <li className="tag">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7v5l3 2" />
            </svg>
            {d.tags[2] ?? "24h/24"}
          </li>
        </ul>

        <div className="app__actions">
          <a href="#pages/Download" className="btn btn--primary">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 3v12M7 10l5 5 5-5M4 20h16" />
            </svg>
            {d.primary}
          </a>
          <a
            href="#galerie"
            className="btn btn--ghost"
            onClick={(e) => { e.preventDefault(); scrollToId("galerie"); }}
          >
            {d.secondary}
          </a>
        </div>
        <p className="app__platforms">{d.platforms}</p>
      </div>

      <div className="app__visual">
        <div className="phone" role="img" aria-label={d.phoneLabel}>
          <div className="phone__notch" />
          <div className="phone__screen">
            <div className="phone__top">
              <span className="phone__dot" />
              <span>{d.phoneName}</span>
            </div>
            <div className="phone__search">
              <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-3.5-3.5" />
              </svg>
              {d.phoneSearch}
            </div>
            <svg className="phone__map" viewBox="0 0 230 210" aria-hidden="true">
              <defs>
                <radialGradient id="app-glow" cx="50%" cy="50%" r="50%">
                  <stop offset="0" stopColor="#38bdf8" stopOpacity=".5" />
                  <stop offset="1" stopColor="#38bdf8" stopOpacity="0" />
                </radialGradient>
              </defs>
              <circle cx="115" cy="105" r="95" fill="url(#app-glow)" />
              <line x1="90" y1="70" x2="140" y2="52" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
              <line x1="140" y1="52" x2="180" y2="96" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
              <line x1="180" y1="96" x2="158" y2="142" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
              <line x1="116" y1="118" x2="158" y2="142" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
              <line x1="90" y1="70" x2="104" y2="92" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
              <line x1="104" y1="92" x2="116" y2="118" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
              <line x1="116" y1="118" x2="80" y2="150" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
              <line x1="158" y1="142" x2="132" y2="178" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
              <line x1="132" y1="178" x2="188" y2="170" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
              <line x1="180" y1="96" x2="170" y2="60" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
              <line x1="170" y1="60" x2="140" y2="52" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
              <line x1="188" y1="170" x2="158" y2="142" stroke="#38bdf8" strokeOpacity=".8" strokeWidth="1" />
              <circle cx="90" cy="70" r="5" fill="#ffd166" />
              <circle cx="140" cy="52" r="3.5" fill="#7dd3fc" />
              <circle cx="180" cy="96" r="3.5" fill="#7dd3fc" />
              <circle cx="116" cy="118" r="5" fill="#ffd166" />
              <circle cx="158" cy="142" r="3.5" fill="#7dd3fc" />
              <circle cx="80" cy="150" r="3.5" fill="#7dd3fc" />
              <circle cx="132" cy="178" r="5" fill="#ffd166" />
              <circle cx="188" cy="170" r="3.5" fill="#7dd3fc" />
              <circle cx="104" cy="92" r="3.5" fill="#7dd3fc" />
              <circle cx="170" cy="60" r="3.5" fill="#7dd3fc" />
            </svg>
            <div className="phone__card">
              <strong>{d.phoneCardTitle}</strong>
              <span>{d.phoneCardSub}</span>
            </div>
          </div>
        </div>

        <span className="float float--left">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="9" cy="8" r="3.5" />
            <path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5a6.5 6.5 0 0 1 3.5 5.5" />
          </svg>
          {d.floatLeft}
        </span>
        <span className="float float--right">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M2 2l20 20M8.5 16.4a5 5 0 0 1 7 0M2 8.8a15 15 0 0 1 4.2-2.6M10.7 5.1A15 15 0 0 1 22 8.8M5 12.9a10 10 0 0 1 3-1.9M13 11a10 10 0 0 1 6 1.9M12 20h.01" />
          </svg>
          {d.floatRight}
        </span>
      </div>
      </div>
    </section>
  );
}
