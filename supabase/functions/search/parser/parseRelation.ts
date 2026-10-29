export function parseRelation(text: string): string | null {
  if (
    text.includes("pres de") ||
    text.includes("proche de") ||
    text.includes("a proximite de") ||
    text.includes("aux alentours de") ||
    text.includes("autour de")
  ) {
    return "near";
  }

  return null;
}