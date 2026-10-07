import { useState, type FormEvent } from "react";
import { SendIcon } from "./icons";

interface ResultsSearchBarProps {
  busy: boolean;
  message: string;
  onSearch: (query: string) => void;
}

export default function ResultsSearchBar({ busy, message, onSearch }: ResultsSearchBarProps) {
  const [value, setValue] = useState("");
  const ready = value.trim().length > 0 && !busy;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = value.trim();
    if (!query || busy) return;
    onSearch(query);
    setValue("");
  }

  return (
    <div className="sr-foot">
      <form className="sr-search" role="search" onSubmit={handleSubmit}>
        <input
          type="text"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Posez votre question..."
          autoComplete="off"
          aria-label="Nouvelle recherche"
        />
        <button type="submit" className={`sr-send ${ready ? "enabled" : ""}`} disabled={!ready} aria-label="Envoyer">
          <SendIcon />
        </button>
      </form>
      {message && <p className="sr-message" aria-live="polite">{message}</p>}
    </div>
  );
}
