import { useRef } from "react";
import { useLang } from "../../i18n/LanguageContext";
import Deco from "./Deco";
import { GALLERY_SLIDES } from "./galleryData";

export default function Gallery() {
  const { t } = useLang();
  const trackRef = useRef<HTMLDivElement>(null);
  const captions = GALLERY_SLIDES.map((slide, i) => ({
    ...slide,
    title: t.gallery.slides[i]?.title ?? slide.title,
    place: t.gallery.slides[i]?.place ?? slide.place,
  }));

  function step(): number {
    const slide = trackRef.current?.querySelector(".slide");
    return slide instanceof HTMLElement ? slide.offsetWidth : 0;
  }

  function prev() {
    trackRef.current?.scrollBy({ left: -step() });
  }

  function next() {
    trackRef.current?.scrollBy({ left: step() });
  }

  return (
    <section className="gallery" id="galerie">
      <Deco set="a" />
      <div className="gallery-head">
        <h2>{t.gallery.title}</h2>
        <div className="arrows">
          <button type="button" onClick={prev} aria-label={t.gallery.prev}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M19 12H5M11 6l-6 6 6 6" />
            </svg>
          </button>
          <button type="button" onClick={next} aria-label={t.gallery.next}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </button>
        </div>
      </div>
      <div className="track" ref={trackRef} tabIndex={0} aria-label={t.gallery.carouselLabel}>
        {captions.map((slide) => (
          <figure className="slide" key={slide.id}>
            <img src={slide.src} alt={slide.alt} loading="lazy" />
            <figcaption>
              {slide.title}
              <small>{slide.place}</small>
            </figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}
