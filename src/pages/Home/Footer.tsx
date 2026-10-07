import { useLang } from "../../i18n/LanguageContext";

function go(hash: string) {
  window.location.hash = hash;
}

export default function Footer() {
  const { t } = useLang();
  const f = t.footer;
  return (
    <footer className="footer">
      <div className="footer__inner">
        <a
          className="brand"
          href="#accueil"
          aria-label={f.backToTop}
          onClick={(e) => {
            e.preventDefault();
            document.getElementById("accueil")?.scrollIntoView({ behavior: "smooth" });
          }}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="3" width="18" height="18" rx="5" fill="currentColor" />
            <path d="M8 12h8M12 8v8" stroke="#fff" strokeWidth="2" strokeLinecap="round" fill="none" />
          </svg>
          Connectéo
        </a>
        <nav className="footer__nav" aria-label={f.secondaryNav}>
          <button type="button" onClick={() => go("#pages/Download")}>
            {f.download}
          </button>
          <button type="button" onClick={() => go("#pages/About")}>
            {f.about}
          </button>
          <button type="button" onClick={() => go("#pages/Auth")}>
            {f.connect}
          </button>
        </nav>
      </div>
      <p className="footer__note">{f.note}</p>
    </footer>
  );
}
