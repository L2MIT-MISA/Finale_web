import { useEffect, useRef, useState, type FormEvent } from "react";
import "./SearchBar.css";

interface SearchBarProps { active: boolean; loading: boolean; onActivate: () => void; onSearch: (query: string) => void; }

export default function SearchBar({ active, loading, onActivate, onSearch }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const ready = query.trim().length > 0 && !loading;

  useEffect(() => { if (active) inputRef.current?.focus(); }, [active]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = query.trim();
    if (value && !loading) onSearch(value);
  }

  return (
    <form className="home-search" role="search" onSubmit={handleSubmit} onClick={onActivate}>
      <input
        ref={inputRef}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onFocus={onActivate}
        placeholder="Posez votre question..."
        autoComplete="off"
        aria-label="Rechercher un lieu"
      />
      <button type="submit" className={`home-search-send ${ready ? "enabled" : ""}`} disabled={!ready} aria-label="Envoyer">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <line x1="12" y1="19" x2="12" y2="5" />
          <polyline points="5 12 12 5 19 12" />
        </svg>
      </button>
    </form>
  );
}
