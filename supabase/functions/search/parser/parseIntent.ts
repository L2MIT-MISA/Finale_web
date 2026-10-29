import { INTENTS } from "../dictionaries/intents.ts";

export function parseIntent(text: string): string | null {
  for (const [intent, phrases] of Object.entries(INTENTS)) {
    for (const phrase of phrases) {
      if (text.includes(phrase)) {
        return intent;
      }
    }
  }

  return null;
}