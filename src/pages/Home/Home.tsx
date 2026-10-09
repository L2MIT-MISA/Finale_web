import Download from "./Download";
import Footer from "./Footer";
import Gallery from "./Gallery";
import Hero from "./Hero";
import "./Home.css";

export default function Home() {
  return (
    <div id="page-accueil">
      <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
        <defs>
          <symbol id="deco-wifi" viewBox="0 0 24 24">
            <path d="M2 8.8a15 15 0 0 1 20 0M5 12.9a10 10 0 0 1 14 0M8.5 16.4a5 5 0 0 1 7 0M12 20h.01" />
          </symbol>
          <symbol id="deco-x" viewBox="0 0 24 24">
            <path d="M6 6l12 12M18 6 6 18" />
          </symbol>
          <symbol id="deco-plus" viewBox="0 0 24 24">
            <path d="M12 5v14M5 12h14" />
          </symbol>
          <symbol id="deco-ring" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="6" />
          </symbol>
          <symbol id="deco-signal" viewBox="0 0 24 24">
            <path d="M5 20v-4M10 20v-8M15 20V8M20 20V4" />
          </symbol>
        </defs>
      </svg>
      <main>
        <Hero />
        <Gallery />
        <Download />
      </main>
      <Footer />
    </div>
  );
}
