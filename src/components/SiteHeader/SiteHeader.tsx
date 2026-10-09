import { useEffect, useRef, useState } from "react";
import { LANGS } from "../../i18n/index";
import { useLang } from "../../i18n/LanguageContext";
import { signOut } from "../../services/auth";
import { supabase } from "../../services/supabase";
import "./SiteHeader.css";

export type SiteHeaderVariant = "hero" | "page";

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function isHomePage(page: string) {
  return (
    page === "" ||
    page === "home" ||
    page === "pages/Home" ||
    page === "accueil" ||
    page === "galerie" ||
    page === "telecharger"
  );
}

type ActiveKey = "accueil" | "telecharger" | "about" | null;

function getActive(page: string): ActiveKey {
  if (isHomePage(page)) return "accueil";
  if (page === "download" || page === "pages/Download") return "telecharger";
  if (page === "about" || page === "pages/About") return "about";
  return null;
}

export default function SiteHeader({ variant, page }: { variant: SiteHeaderVariant; page: string }) {
  const home = isHomePage(page);
  const active = getActive(page);
  const { lang, setLang, t } = useLang();
  const [langOpen, setLangOpen] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const langRef = useRef<HTMLDivElement>(null);
  const accountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let mounted = true;
    supabase.auth.getSession().then(({ data }) => {
      if (mounted) setAuthed(Boolean(data.session));
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setAuthed(Boolean(session));
      if (!session) setAccountOpen(false);
    });
    return () => {
      mounted = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (!langOpen && !accountOpen) return;
    function closeOnOutside(event: MouseEvent) {
      if (!langRef.current?.contains(event.target as Node)) setLangOpen(false);
      if (!accountRef.current?.contains(event.target as Node)) setAccountOpen(false);
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setLangOpen(false);
        setAccountOpen(false);
      }
    }
    document.addEventListener("mousedown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [langOpen, accountOpen]);

  function goAccueil() {
    setMobileOpen(false);
    if (home) scrollToId("accueil");
    else window.location.hash = "#pages/Home";
  }

  function goDecouvrir() {
    setMobileOpen(false);
    if (home) {
      scrollToId("galerie");
      return;
    }
    try {
      sessionStorage.setItem("connecteo-scroll", "galerie");
    } catch {
      /* stockage indisponible */
    }
    window.location.hash = "#pages/Home";
  }

  function goTelecharger() {
    setMobileOpen(false);
    window.location.hash = "#pages/Download";
  }

  function goAbout() {
    setMobileOpen(false);
    window.location.hash = "#pages/About";
  }

  function goAuth() {
    setMobileOpen(false);
    window.location.hash = "#pages/Auth";
  }

  async function handleSignOut() {
    setSigningOut(true);
    const { error } = await signOut();
    setSigningOut(false);
    if (error) return;
    setAccountOpen(false);
    setMobileOpen(false);
    window.location.hash = "#pages/Home";
  }

  function linkClass(key: Exclude<ActiveKey, null>) {
    return `site-header__link${active === key ? " site-header__link--active" : ""}`;
  }

  return (
    <>
      <header className={variant === "page" ? "site-header site-header--page" : "site-header"}>
        <a
          className="site-header__brand"
          href="#pages/Home"
          aria-label="Connectéo — accueil"
          onClick={(e) => { e.preventDefault(); goAccueil(); }}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="3" width="18" height="18" rx="5" fill="currentColor" />
            <path d="M8 12h8M12 8v8" stroke="#fff" strokeWidth="2" strokeLinecap="round" fill="none" />
          </svg>
          Connectéo
        </a>
        <nav className="site-header__nav" aria-label="Navigation principale">
          <a
            className={linkClass("accueil")}
            href="#pages/Home"
            onClick={(e) => { e.preventDefault(); goAccueil(); }}
            aria-current={active === "accueil" ? "page" : undefined}
          >
            {t.nav.home}
          </a>
          <a
            className="site-header__link"
            href="#galerie"
            onClick={(e) => { e.preventDefault(); goDecouvrir(); }}
          >
            {t.nav.discover}
          </a>
          <a
            className={linkClass("telecharger")}
            href="#pages/Download"
            onClick={(e) => { e.preventDefault(); goTelecharger(); }}
            aria-current={active === "telecharger" ? "page" : undefined}
          >
            {t.nav.download}
          </a>
          <a
            className={linkClass("about")}
            href="#pages/About"
            onClick={(e) => { e.preventDefault(); goAbout(); }}
            aria-current={active === "about" ? "page" : undefined}
          >
            {t.nav.about}
          </a>
          <div className="site-header__lang" ref={langRef}>
            <button
              type="button"
              className="site-header__langbtn"
              aria-haspopup="menu"
              aria-expanded={langOpen}
              aria-label={t.nav.chooseLanguage}
              onClick={() => setLangOpen((open) => !open)}
            >
              {lang}
              <svg className={`site-header__chevron${langOpen ? " open" : ""}`} width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="m6 9 6 6 6-6" />
              </svg>
            </button>
            {langOpen && (
              <div className="site-header__menu" role="menu" aria-label={t.nav.languageMenu}>
                {LANGS.map((item) => (
                  <button
                    key={item.code}
                    type="button"
                    role="menuitemradio"
                    aria-checked={lang === item.code}
                    className={lang === item.code ? "active" : ""}
                    onClick={() => { setLang(item.code); setLangOpen(false); }}
                  >
                    {item.label}
                    {lang === item.code && (
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="m5 13 4 4L19 7" />
                      </svg>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
          {authed ? (
            <div className="site-header__account" ref={accountRef}>
              <button
                type="button"
                className="site-header__avatar"
                aria-haspopup="menu"
                aria-expanded={accountOpen}
                aria-label={t.nav.account}
                onClick={() => setAccountOpen((open) => !open)}
              >
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="8" r="3.5" />
                  <path d="M5.5 20c.5-4 2.7-6 6.5-6s6 2 6.5 6" />
                </svg> 
              </button>
              {accountOpen && (
                <div className="site-header__menu site-header__menu--right" role="menu">
                
                  <button
                    type="button"
                    role="menuitem"
                    disabled={signingOut}
                    onClick={handleSignOut}
                  >
                    {signingOut ? t.nav.signingOut : t.nav.signOut}
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button type="button" className="site-header__btn" onClick={goAuth}>
              {t.nav.connect}
            </button>
          )}
        </nav>
        <button
          type="button"
          className="site-header__burger"
          aria-label={t.nav.openMenu}
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((open) => !open)}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <line x1="4" y1="7" x2="20" y2="7" />
            <line x1="4" y1="12" x2="20" y2="12" />
            <line x1="4" y1="17" x2="20" y2="17" />
          </svg>
        </button>
      </header>
      {mobileOpen && (
        <div className={`site-header__panel${variant === "page" ? " site-header__panel--page" : ""}`} role="menu" aria-label={t.nav.mobileMenu}>
          <button type="button" role="menuitem" className={active === "accueil" ? "active" : ""} onClick={goAccueil}>{t.nav.home}</button>
          <button type="button" role="menuitem" onClick={goDecouvrir}>{t.nav.discover}</button>
          <button type="button" role="menuitem" className={active === "telecharger" ? "active" : ""} onClick={goTelecharger}>{t.nav.download}</button>
          <button type="button" role="menuitem" className={active === "about" ? "active" : ""} onClick={goAbout}>{t.nav.about}</button>
          {authed ? (
            <button type="button" role="menuitem" disabled={signingOut} onClick={handleSignOut}>
              {signingOut ? t.nav.signingOut : t.nav.signOut}
            </button>
          ) : (
            <button type="button" role="menuitem" className="site-header__panel-cta" onClick={goAuth}>{t.nav.connect}</button>
          )}
        </div>
      )}
    </>
  );
}
