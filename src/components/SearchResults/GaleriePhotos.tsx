import { useEffect, useRef, useState } from "react";
import type { Image } from "../../pages/Search/searchTypes";
import { ImageIcon } from "./icons";

interface Props {
  images: Image[];
  nom: string;
  hue: number;
  /** Mode détail : grande photo, flèches et miniatures. */
  grande?: boolean;
}

// Rendu avec key={lieu.id} côté parent : l'état repart à zéro à chaque lieu.
export default function GaleriePhotos({ images, nom, hue, grande = false }: Props) {
  const [slide, setSlide] = useState(0);
  const [casses, setCasses] = useState<string[]>([]);
  const touche = useRef(0);

  const n = images.length;
  const idx = n ? slide % n : 0;
  const image = images[idx];

  useEffect(() => {
    if (n < 2) return;
    const timer = setInterval(() => {
      if (Date.now() - touche.current >= 4000) setSlide((s) => s + 1);
    }, 3500);
    return () => clearInterval(timer);
  }, [n]);

  const aller = (i: number) => { touche.current = Date.now(); setSlide(i); };
  const bump = (d: number) => aller((idx + d + n) % n);
  const marquerCassee = (url: string) => setCasses((c) => [...c, url]);
  const fond = (k: number) => `linear-gradient(135deg, hsl(${hue + k * 16},42%,38%), hsl(${hue + 34 + k * 16},48%,26%))`;

  return (
    <div className="sr-galerie">
      <div className="sr-photos">
        <div className={`sr-photo-box${grande ? " open" : ""}`} style={{ background: fond(idx) }}>
          {image && !casses.includes(image.url) ? (
            <img src={image.url} alt={image.legende ?? nom} onError={() => marquerCassee(image.url)} />
          ) : (
            <span className="sr-photo-ph"><ImageIcon /><span>Photo indisponible</span></span>
          )}
          {n > 1 && (
            <>
              <button type="button" className="sr-photo-hit" aria-label="Photo suivante" onClick={() => bump(1)} />
              <div className="sr-dots" aria-hidden="true">
                {images.map((_, k) => <span key={k} className={k === idx ? "on" : ""} />)}
              </div>
            </>
          )}
          {grande && n > 1 && (
            <>
              <button type="button" className="sr-arrow left" aria-label="Photo précédente" onClick={() => bump(-1)}>‹</button>
              <button type="button" className="sr-arrow right" aria-label="Photo suivante" onClick={() => bump(1)}>›</button>
            </>
          )}
        </div>

        {grande && n > 1 && (
          <div className="sr-thumbs">
            {images.map((im, k) => (
              <button
                key={im.url}
                type="button"
                className={k === idx ? "on" : ""}
                aria-label={`Voir la photo ${k + 1}${im.legende ? ` : ${im.legende}` : ""}`}
                style={{ background: fond(k) }}
                onClick={() => aller(k)}
              >
                {casses.includes(im.url) ? k + 1 : <img src={im.url} alt="" onError={() => marquerCassee(im.url)} />}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="sr-caption">
        <span>{image?.legende ?? ""}</span>
        <span>{n > 1 ? `${idx + 1} / ${n}` : "1 photo"}</span>
      </div>
    </div>
  );
}
