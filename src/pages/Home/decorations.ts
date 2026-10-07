export type DecoSymbol = "wifi" | "x" | "plus" | "ring" | "signal";

/** [symbol, left%, top%, sizePx, rotateDeg] — repris du modèle */
type DecoEntry = [DecoSymbol, number, number, number, number];

export const DECO_SETS: Record<"a" | "b", DecoEntry[]> = {
  a: [
    ["wifi", 3, 1, 40, -12],
    ["x", 92, 2, 28, 15],
    ["plus", 82, 1, 26, 0],
    ["ring", 14, 3, 20, 0],
    ["signal", 94, 95, 36, 0],
    ["x", 6, 94, 30, -20],
    ["wifi", 62, 94, 40, 10],
    ["plus", 34, 96, 24, 0],
    ["ring", 76, 92, 20, 0],
  ],
  b: [
    ["wifi", 9, 18, 64, -14],
    ["x", 20, 72, 34, 12],
    ["plus", 6, 48, 30, 0],
    ["ring", 16, 88, 26, 0],
    ["signal", 84, 16, 50, 8],
    ["wifi", 88, 64, 58, 16],
    ["x", 76, 86, 30, -10],
    ["plus", 92, 40, 28, 0],
    ["ring", 70, 8, 22, 0],
    ["x", 30, 8, 26, 20],
  ],
};
