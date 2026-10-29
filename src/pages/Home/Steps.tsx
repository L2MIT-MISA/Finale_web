import { useLang } from "../../i18n/LanguageContext";

export interface Step {
  n: number;
  title: string;
  text: string;
  example?: string;
  target?: string;
}

/** Cibles de défilement par position (comportement, indépendant de la langue). */
const TARGETS: Array<string | undefined> = [undefined, "galerie", "telecharger"];

export default function Steps({ onPick }: { onPick: (step: Step) => void }) {
  const { t } = useLang();
  const items: Step[] = t.steps.items.map((item, i) => ({
    n: i + 1,
    title: item.title,
    text: item.text,
    example: item.example,
    target: TARGETS[i],
  }));

  return (
    <ol className="steps" aria-label={t.steps.label}>
      {items.map((step) => (
        <li key={step.n}>
          <button
            type="button"
            className="step"
            onClick={() => onPick(step)}
            aria-label={
              step.target
                ? `${step.title} — ${t.steps.goLabel}`
                : `${step.title} — ${t.steps.tryLabel} : ${step.example}`
            }
          >
            <span className="step__top">
              <span className="badge" aria-hidden="true">{step.n}</span>
              <span className="step__title">{step.title}</span>
            </span>
            <span className="step__text">{step.text}</span>
          </button>
        </li>
      ))}
    </ol>
  );
}
