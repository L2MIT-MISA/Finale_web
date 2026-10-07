import { useEffect, useState, type FormEvent } from "react";
import SiteHeader from "../../components/SiteHeader/SiteHeader";
import { fill } from "../../i18n/index";
import { useLang } from "../../i18n/LanguageContext";
import { HERO_SLIDES } from "./galleryData";
import Steps, { type Step } from "./Steps";

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function goToSearch(text: string) {
  try {
    sessionStorage.setItem("connecteo-requete", text);
  } catch {
    /* stockage indisponible */
  }
  window.location.hash = "#pages/Search";
}

export default function Hero() {
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState("");
  const { t } = useLang();
  const [slide, setSlide] = useState(0);
  const [paused, setPaused] = useState(false);
  const slides = HERO_SLIDES.map((item, i) => ({
    ...item,
    title: t.hero.slides[i]?.title ?? item.title,
    lead: t.hero.slides[i]?.lead ?? item.lead,
  }));

  const [reduceMotion] = useState(
    () =>
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );

  useEffect(() => {
    if (paused || reduceMotion) return;
    const timer = window.setTimeout(() => setSlide((i) => (i + 1) % HERO_SLIDES.length), 7000);
    return () => window.clearTimeout(timer);
  }, [slide, paused, reduceMotion]);
  useEffect(() => {
    try {
      const target = sessionStorage.getItem("connecteo-scroll");
      if (target) {
        sessionStorage.removeItem("connecteo-scroll");
        window.setTimeout(() => scrollToId(target), 60);
      }
    } catch {
      /* stockage indisponible */
    }
  }, []);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const value = query.trim();
    if (!value) {
      setMessage(t.hero.emptyQuery);
      return;
    }
    goToSearch(value);
  }

  function pickExample(step: Step) {
    if (step.target) {
      scrollToId(step.target);
      return;
    }
    if (step.example) {
      setQuery(step.example);
      document.getElementById("q")?.focus({ preventScroll: true });
    }
  }

  return (
    <section
      className="hero"
      id="accueil"
      aria-roledescription="carrousel"
      aria-label="Photos de couverture"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <div className="hero__bgs" aria-hidden="true">
        {HERO_SLIDES.map((item, i) => (
          <div
            key={item.id}
            className={`hero__bg${i === slide ? " active" : ""}`}
            style={{ backgroundImage: `url('${item.src}')` }}
          />
        ))}
      </div>
      <div className="hero__scrim" aria-hidden="true" />
      <SiteHeader variant="page" page="home" />
      <div className="hero__content">
        <div className="hero__body">
          <div className="hero__main">
            <div className="hero__swap" key={slides[slide].id}>
              <h1 className="hero__title">{slides[slide].title}</h1>
              <p className="hero__lead">{slides[slide].lead}</p>
            </div>
            <span className="dash" aria-hidden="true" />
            <form className="search" role="search" onSubmit={handleSubmit}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" />
          </svg>
          <input
            id="q"
            type="search"
            placeholder={t.hero.searchPlaceholder}
            aria-label={t.hero.searchLabel}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
          />
          <button type="submit" aria-label={t.hero.searchSubmit} disabled={query.trim() === ""}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </button>
        </form>
        <div id="msg" aria-live="polite">{message}</div>

        <div className="hero__dots" aria-label={t.hero.coverLabel}>
          {HERO_SLIDES.map((item, i) => (
            <button
              key={item.id}
              type="button"
              className={i === slide ? "active" : ""}
              aria-label={fill(t.hero.photoLabel, { n: String(i + 1), t: slides[i].title })}
              aria-current={i === slide}
              onClick={() => setSlide(i)}
            />
          ))}
        </div>
          </div>
          <Steps onPick={pickExample} />
        </div>
      </div>
    </section>
  );
}
