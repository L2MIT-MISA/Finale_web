import { useEffect, useRef, useState, type FormEvent } from "react";
import { SendIcon, SparkIcon } from "./icons";
import { plur } from "./placeFormat";

export interface Message {
  id: number;
  from: "user" | "ai";
  text: string;
}

interface Props {
  messages: Message[];
  busy: boolean;
  total: number;
  triees: boolean;
  onSend: (texte: string) => void;
  onShowList: () => void;
}

export default function ChatPanel({ messages, busy, total, triees, onSend, onShowList }: Props) {
  const [valeur, setValeur] = useState("");
  const corps = useRef<HTMLDivElement>(null);
  const pret = valeur.trim().length > 0 && !busy;

  useEffect(() => {
    if (corps.current) corps.current.scrollTop = corps.current.scrollHeight;
  }, [messages.length, busy, total]);

  function envoyer(e: FormEvent) {
    e.preventDefault();
    const t = valeur.trim();
    if (!t || busy) return;
    onSend(t);
    setValeur("");
  }

  return (
    <div className="sr-chat">
      <div className="sr-chat-head">
        <div className="sr-chat-avatar"><SparkIcon /></div>
        <div className="sr-chat-id">
          <div className="sr-chat-label">ASSISTANT CONNECTÉO</div>
          <div className="sr-chat-sub">Je vous aide à trouver le bon lieu</div>
        </div>
        {total > 0 && <span className="sr-chip-count">{plur(total, "lieu", "lieux")}</span>}
      </div>

      <div className="sr-chat-body" ref={corps} aria-live="polite">
        {messages.map((m) => (
          <div key={m.id} className={`sr-bubble ${m.from}`}>{m.text}</div>
        ))}

        {busy && (
          <div className="sr-bubble ai sr-typing" aria-label="L'assistant réfléchit"><span /><span /><span /></div>
        )}

        {!busy && total > 0 && (
          <div className="sr-found">
            <div className="sr-found-title">{plur(total, "lieu trouvé", "lieux trouvés")}</div>
            {triees && <div className="sr-found-sub">Classés par pertinence.</div>}
            <button type="button" className="sr-primary" onClick={onShowList}>Voir les lieux trouvés</button>
          </div>
        )}
      </div>

      <form className="sr-chat-form" onSubmit={envoyer}>
        <label htmlFor="chat-q" className="sr-sr">Posez votre question</label>
        <input
          id="chat-q"
          type="text"
          value={valeur}
          onChange={(e) => setValeur(e.target.value)}
          placeholder="Posez votre question..."
          autoComplete="off"
        />
        <button type="submit" className={`sr-send${pret ? " on" : ""}`} disabled={!pret} aria-label="Envoyer"><SendIcon /></button>
      </form>
    </div>
  );
}
