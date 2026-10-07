import { useEffect, useRef } from "react";
import type { PlaceResult } from "../../pages/Search/searchTypes";
import type { AssistantOption } from "../../services/assistant";
import PlaceDetail from "./PlaceDetail";
import ResultsSearchBar from "./ResultsSearchBar";
import { PinIcon } from "./icons";
import { connectivityLabel, connectivityTone } from "./placeFormat";
import "./SearchResults.css";

export interface ChatMessage {
  id: number;
  from: "user" | "ai";
  text: string;
  options?: AssistantOption[];
}

export type PanelView = "results" | "assistant";

interface SearchResultsProps {
  results: PlaceResult[];
  title: string;
  selected: PlaceResult | null;
  detailOpen: boolean;
  busy: boolean;
  message: string;
  messages: ChatMessage[];
  view: PanelView;
  onViewChange: (view: PanelView) => void;
  onSelect: (result: PlaceResult) => void;
  onBack: () => void;
  onFocus: () => void;
  onSearch: (query: string) => void;
  onOption: (option: AssistantOption) => void;
}

function SparkIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </svg>
  );
}

export default function SearchResults({
  results, title, selected, detailOpen, busy, message, messages, view,
  onViewChange, onSelect, onBack, onFocus, onSearch, onOption,
}: SearchResultsProps) {
  const showDetail = detailOpen && selected !== null;
  const bodyRef = useRef<HTMLDivElement>(null);
  const lastId = messages.length ? messages[messages.length - 1].id : -1;

  useEffect(() => {
    if (view === "assistant" && bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages.length, busy, view]);

  //affiche le vue assistant en plein panneau
  if (view === "assistant") {
    return (
      <section className="sr-panel sr-assist" aria-label="Assistant Connectéo">
        <div className="sr-assist-head">
          <div className="sr-assist-avatar"><SparkIcon /></div>
          <div className="sr-assist-id">
            <div className="sr-assist-label">Assistant Connectéo</div>
            <div className="sr-assist-sub">Je vous aide à trouver le bon lieu</div>
          </div>
          {results.length > 0 && (
            <button type="button" className="sr-assist-back" onClick={() => onViewChange("results")}>
              {results.length} {results.length > 1 ? "lieux" : "lieu"}
            </button>
          )}
        </div>

        <div className="sr-assist-body" ref={bodyRef} aria-live="polite">
          {messages.map((m) => {
            const isAsk = m.from === "ai" && m.id === lastId && m.options && m.options.length > 0;

            if (isAsk) {
              return (
                <div key={m.id} className="sr-ask">
                  <div className="sr-ask-question">{m.text}</div>
                  <div className="sr-ask-options">
                    {m.options!.map((opt, i) => (
                      <button
                        key={opt.label}
                        type="button"
                        className={`sr-ask-option${opt.danger ? " danger" : ""}${opt.success ? " success" : ""}`}
                        style={{ animationDelay: `${i * 55}ms` }}
                        onClick={() => onOption(opt)}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              );
            }

            return (
              <div key={m.id} className={`sr-bubble ${m.from}`}>{m.text}</div>
            );
          })}

          {busy && (
            <div className="sr-bubble ai sr-typing" aria-label="L'assistant réfléchit">
              <span /><span /><span />
            </div>
          )}
        </div>

        <ResultsSearchBar busy={busy} message={message} onSearch={onSearch} />
      </section>
    );
  }

  //affiche le résultat(liste)
  return (
    <section className="sr-panel" aria-label="Résultats de recherche">
      {showDetail ? (
        <PlaceDetail place={selected} onBack={onBack} onFocus={onFocus} />
      ) : (
        <>
          <div className="sr-head">
            <div className="sr-title">{title.charAt(0).toUpperCase() + title.slice(1)}</div>
            <div className="sr-count">{results.length} {results.length > 1 ? "lieux trouvés" : "lieu trouvé"}</div>
            {messages.length > 0 && (
              <button type="button" className="sr-chat-link" onClick={() => onViewChange("assistant")}>
                <SparkIcon /> Reprendre la conversation
              </button>
            )}
          </div>

          <div className="sr-list">
            {results.map((result) => (
              <button
                key={result.id}
                type="button"
                className={`sr-item ${result.id === selected?.id ? "active" : ""}`}
                onClick={() => onSelect(result)}
              >
                <span className="sr-item-icon"><PinIcon /></span>
                <span className="sr-item-info">
                  <span className="sr-item-name">{result.name}</span>
                  <span className="sr-item-address">{result.address}</span>
                  <span className="sr-item-meta">
                    <span className={`sr-tone ${connectivityTone(result)}`}>{connectivityLabel(result)}</span>
                    {result.openingHours && <span className="sr-item-hours">{result.openingHours}</span>}
                  </span>
                </span>
              </button>
            ))}
          </div>
        </>
      )}

      <ResultsSearchBar busy={busy} message={message} onSearch={onSearch} />
    </section>
  );
}