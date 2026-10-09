import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { getDict, getInitialLang, persistLang } from "./index";
import type { Dict, Lang } from "./types";

interface LanguageContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: Dict;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(getInitialLang);
  const t = useMemo(() => getDict(lang), [lang]);

  function setLang(next: Lang) {
    setLangState(next);
    persistLang(next);
  }

  const value = useMemo(() => ({ lang, setLang, t }), [lang, t]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLang(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLang doit être utilisé dans <LanguageProvider>");
  return ctx;
}
