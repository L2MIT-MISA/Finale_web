import { CATEGORIES } from "../dictionaries/categories.ts";
import { ACTIONS } from "../dictionaries/actions.ts";

export function parseCategory(text: string): string | null {
  for (const [category, aliases] of Object.entries(CATEGORIES)) {
    for (const alias of aliases) {
      if (text.includes(alias)) {
        return category;
      }
    }
  }

  for (const [category, actions] of Object.entries(ACTIONS)) {
    for (const action of actions) {
      if (text.includes(action)) {
        return category;
      }
    }
  }

  return null;
}
