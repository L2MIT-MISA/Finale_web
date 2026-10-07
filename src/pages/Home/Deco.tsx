import { DECO_SETS } from "./decorations";

export default function Deco({ set }: { set: "a" | "b" }) {
  return (
    <div className="deco" aria-hidden="true">
      {DECO_SETS[set].map(([symbol, left, top, size, rotate], index) => (
        <svg
          key={`${symbol}-${index}`}
          viewBox="0 0 24 24"
          style={{
            left: `${left}%`,
            top: `${top}%`,
            width: size,
            height: size,
            transform: `rotate(${rotate}deg)`,
          }}
        >
          <use href={`#deco-${symbol}`} />
        </svg>
      ))}
    </div>
  );
}
