import { useCallback, useEffect, useRef, useState } from "react";
import ConnecteoMap from "../../components/ConnecteoMap/ConnecteoMap";
import ChatPanel, { type Message } from "../../components/SearchResults/ChatPanel";
import PlaceInfo from "../../components/SearchResults/PlaceInfo";
import PlacesList from "../../components/SearchResults/PlacesList";
import { demanderIA, imagesDe, lieuxDe, messagesDe, sourcesWebDe } from "../../services/assistant";
import type { CarteIA, ImageReponseIA, Lieu, SourceIA } from "./searchTypes";
import "../../components/SearchResults/SearchResults.css";
import "./SearchPage.css";

export const REQUETE_KEY = "connecteo-requete";

function lireRequete(): string {
  try {
    return sessionStorage.getItem(REQUETE_KEY)?.trim() ?? "";
  } catch {
    return "";
  }
}

export default function SearchPage() {
  const [initiale] = useState(lireRequete);
  const [messages, setMessages] = useState<Message[]>(() => [
    initiale
      ? { id: 0, from: "user", text: initiale }
      : { id: 0, from: "ai", text: "Que cherchez-vous ? Décrivez un lieu ou un besoin." },
  ]);
  const [lieux, setLieux] = useState<Lieu[]>([]);
  const [sources, setSources] = useState<SourceIA[]>([]);
  const [carte, setCarte] = useState<CarteIA | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [demandeItineraire, setDemandeItineraire] = useState(0);
  const [vue, setVue] = useState<"chat" | "liste">("chat");
  const [busy, setBusy] = useState(Boolean(initiale));
  const [infoMasquee, setInfoMasquee] = useState(false);
  // Faux tant que l'utilisateur n'a pas ouvert la carte : le chat occupe alors tout l'écran (arrivée depuis l'accueil).
  // Une fois la carte ouverte, elle reste en place et la discussion revient dans le panneau latéral.
  const [carteOuverte, setCarteOuverte] = useState(false);

  const idRef = useRef(1);
  const ctrlRef = useRef<AbortController | null>(null);

  const ajouter = useCallback((from: Message["from"], text: string, suggestions?: string[], sourcesWeb?: SourceIA[],
                               images?: ImageReponseIA[]) => {
    setMessages((m) => [...m, { id: idRef.current++, from, text, suggestions, sources: sourcesWeb, images }]);
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
        const versListe = Boolean(rep.ouvrir_carte) && nouveaux.length > 0;
        if (versListe) setCarteOuverte(true);
        setVue(versListe ? "liste" : "chat");
        const textes = messagesDe(rep);
        const web = sourcesWebDe(rep);
        const photos = imagesDe(rep);
        textes.forEach((t, index) => {
          const dernier = index === textes.length - 1;
          ajouter("ai", t, dernier ? rep.suggestions : undefined, dernier ? web : undefined, dernier ? photos : undefined);
        });
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
    return () => ctrlRef.current?.abort();
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

  const selected = lieux.find((l) => l.id === selectedId) ?? null;
  const triees = lieux.length > 1;

  return (
    <main className={`search-map-page${carteOuverte ? "" : " chat-plein"}`}>
      <aside className="search-map-side">
        {vue === "chat" ? (
          <ChatPanel
            messages={messages}
            busy={busy}
            total={lieux.length}
            triees={triees}
            showFound={true}
            onSend={envoyer}
            onShowList={() => { setSelectedId(null); setCarteOuverte(true); setVue("liste"); }}
          />
        ) : (
          <PlacesList
            lieux={lieux}
            selectedId={selectedId}
            onSelect={(l) => setSelectedId(l.id)}
            onBack={() => { setSelectedId(null); setVue("chat"); }}
          />
        )}
      </aside>

      {/* La carte n'apparaît qu'une fois ouverte (« Voir les lieux trouvés ») ; ensuite elle reste affichée à côté du panneau. */}
      {carteOuverte && (
        <section className="search-map-column" aria-label="Carte et informations">
          <div className="sr-map-wrap">
            <ConnecteoMap
              lieux={lieux}
              carte={carte}
              selected={selected}
              demandeItineraire={demandeItineraire}
              onSelect={(l) => setSelectedId(String(l.id))}
            />
          </div>
          {selected && (
            <PlaceInfo
              key={selected.id}
              lieu={selected}
              sources={sources}
              onItineraire={() => setDemandeItineraire((n) => n + 1)}
              masque={infoMasquee}
              onToggleMasque={() => setInfoMasquee((v) => !v)}
            />
          )}
        </section>
      )}
    </main>
  );
}