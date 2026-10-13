import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import ConnecteoMap from "../../components/ConnecteoMap/ConnecteoMap";
import ChatPanel, { type Message } from "../../components/SearchResults/ChatPanel";
import PlaceDetailPanel from "../../components/SearchResults/PlaceDetailPanel";
import PlacesList from "../../components/SearchResults/PlacesList";
import TalkIntro from "../../components/SearchResults/TalkIntro";
import { cleLieu } from "../../components/SearchResults/placeFormat";
import { demanderIA, lieuxDe, messagesDe } from "../../services/assistant";
import { HERO_SLIDES } from "../Home/galleryData";
import type { CarteIA, Lieu, SourceIA } from "./searchTypes";
import "../../components/SearchResults/SearchResults.css";
import "./SearchPage.css";

export const REQUETE_KEY = "connecteo-requete";
const HERO_SLIDE_KEY = "connecteo-hero-slide";
const ENREGISTRES_KEY = "connecteo-enregistres";

function lireRequete(): string {
  try {
    return sessionStorage.getItem(REQUETE_KEY)?.trim() ?? "";
  } catch {
    return "";
  }
}

// Photo de fond de l'accueil au moment du clic sur « Rechercher » (la première par défaut).
function lireFond(): string {
  try {
    const i = Number(sessionStorage.getItem(HERO_SLIDE_KEY));
    return HERO_SLIDES[Number.isInteger(i) && i >= 0 && i < HERO_SLIDES.length ? i : 0].src;
  } catch {
    return HERO_SLIDES[0].src;
  }
}

function lireEnregistres(): Set<string> {
  try {
    const brut = JSON.parse(localStorage.getItem(ENREGISTRES_KEY) ?? "[]") as unknown;
    return new Set(Array.isArray(brut) ? brut.filter((k): k is string => typeof k === "string") : []);
  } catch {
    return new Set();
  }
}

export default function SearchPage() {
  const [initiale] = useState(lireRequete);
  const [fond] = useState(lireFond);
  const [messages, setMessages] = useState<Message[]>(() => [
    initiale
      ? { id: 0, from: "user", text: initiale }
      : { id: 0, from: "ai", text: "Bonjour ! Dites-moi ce que vous cherchez et où : je trouve le lieu et le réseau mobile qui y fonctionne le mieux." },
  ]);
  const [lieux, setLieux] = useState<Lieu[]>([]);
  const [sources, setSources] = useState<SourceIA[]>([]);
  const [carte, setCarte] = useState<CarteIA | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [demandeItineraire, setDemandeItineraire] = useState(0);
  const [vue, setVue] = useState<"chat" | "liste">("chat");
  const [busy, setBusy] = useState(Boolean(initiale));
  const [enregistres, setEnregistres] = useState<Set<string>>(lireEnregistres);
  const [toast, setToast] = useState("");

  const idRef = useRef(1);
  const ctrlRef = useRef<AbortController | null>(null);
  const toastRef = useRef<number | undefined>(undefined);

  const ajouter = useCallback((from: Message["from"], text: string, suggestions?: string[]) => {
    setMessages((m) => [...m, { id: idRef.current++, from, text, suggestions }]);
  }, []);

  const afficherToast = useCallback((message: string) => {
    window.clearTimeout(toastRef.current);
    setToast(message);
    toastRef.current = window.setTimeout(() => setToast(""), 2200);
  }, []);

  const lancer = useCallback(
    async (texte: string) => {
      ctrlRef.current?.abort();
      const ctrl = new AbortController();
      ctrlRef.current = ctrl;
      setBusy(true);
      try {
        const rep = await demanderIA(texte, ctrl.signal);
        if (ctrl.signal.aborted) return;
        if (rep.avertissements?.length) console.warn("[IA]", rep.avertissements);

        const nouveaux = lieuxDe(rep);
        // Le backend indique explicitement quand une réponse conversationnelle doit garder la carte actuelle.
        if (!rep.garder_resultats) {
          setLieux(nouveaux);
          setSources(rep.sources ?? []);
          setCarte(rep.carte ?? null);
          setSelectedId(null);
        }
        setVue(rep.ouvrir_carte && nouveaux.length > 0 ? "liste" : "chat");
        const textes = messagesDe(rep);
        textes.forEach((t, index) => ajouter("ai", t, index === textes.length - 1 ? rep.suggestions : undefined));
      } catch {
        if (ctrl.signal.aborted) return;
        ajouter("ai", "L'assistant est indisponible. Réessayez dans un instant.");
      } finally {
        if (!ctrl.signal.aborted) setBusy(false);
      }
    },
    [ajouter],
  );

  useEffect(() => {
    if (initiale) void lancer(initiale);
    return () => {
      ctrlRef.current?.abort();
      window.clearTimeout(toastRef.current);
    };
  }, [initiale, lancer]);

  function envoyer(texte: string) {
    ajouter("user", texte);
    try {
      sessionStorage.setItem(REQUETE_KEY, texte);
    } catch {
      /* stockage indisponible */
    }
    void lancer(texte);
  }

  function basculerEnregistre(lieu: Lieu) {
    const cle = cleLieu(lieu);
    const suivant = new Set(enregistres);
    const actif = !suivant.has(cle);
    if (actif) suivant.add(cle); else suivant.delete(cle);
    setEnregistres(suivant);
    try {
      localStorage.setItem(ENREGISTRES_KEY, JSON.stringify([...suivant]));
    } catch {
      /* stockage indisponible : l'état reste valable pour cette session */
    }
    afficherToast(actif ? "Lieu enregistré" : "Retiré des enregistrés");
  }

  const selected = lieux.find((l) => l.id === selectedId) ?? null;
  const triees = lieux.length > 1;

  // « talk » : discussion seule, tant qu'aucun lieu n'est trouvé · « chat » : discussion + carte · « list » : liste + carte
  const etape = lieux.length === 0 ? "talk" : vue === "liste" ? "list" : "chat";
  const avecFiche = etape === "list" && selected !== null;
  const classes = ["search-map-page", `is-${etape}`, avecFiche ? "has-detail" : ""].filter(Boolean).join(" ");

  return (
    <main className={classes} style={{ "--sr-fond": `url('${fond}')` } as CSSProperties}>
      {etape === "talk" && <TalkIntro />}

      <aside className="search-map-side">
        {/* Toujours monté : la saisie et l'historique survivent au passage de la discussion à la liste. */}
        <div className="sr-chat-wrap">
          <ChatPanel
            messages={messages}
            busy={busy}
            total={lieux.length}
            triees={triees}
            showFound={etape === "chat"}
            placeholder={etape === "talk" ? "Écrivez votre message..." : "Posez votre question..."}
            onSend={envoyer}
            onShowList={() => { setSelectedId(null); setVue("liste"); }}
          />
        </div>
        {etape === "list" && (
          <PlacesList
            lieux={lieux}
            selectedId={selectedId}
            enregistres={enregistres}
            onSelect={(l) => setSelectedId(l.id)}
            onBack={() => { setSelectedId(null); setVue("chat"); }}
          />
        )}
      </aside>

      {avecFiche && selected && (
        <PlaceDetailPanel
          key={selected.id}
          lieu={selected}
          sources={sources}
          enregistre={enregistres.has(cleLieu(selected))}
          onToggleSave={() => basculerEnregistre(selected)}
          onClose={() => setSelectedId(null)}
          onItineraire={() => setDemandeItineraire((n) => n + 1)}
          onToast={afficherToast}
        />
      )}

      {etape !== "talk" && (
        <section className="search-map-column" aria-label="Carte">
          <div className="sr-map-wrap">
            <ConnecteoMap
              lieux={lieux}
              carte={carte}
              selected={selected}
              masquerFicheSelection
              demandeItineraire={demandeItineraire}
              onSelect={(l) => { setSelectedId(String(l.id)); setVue("liste"); }}
            />
          </div>
        </section>
      )}

      {toast && <div role="status" className="sr-toast">{toast}</div>}
    </main>
  );
}
