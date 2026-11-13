// Farmers rank their priorities; the ranking becomes the weights the API takes
import type { Weights } from "./api";

export type Priority = keyof Weights;

export const PRIORITIES: Record<Priority, { label: string; hint: string }> = {
  soil_health: { label: "Soil health", hint: "Nitrogen, soil cover, crop variety" },
  water: { label: "Water conservation", hint: "Irrigation gap" },
  stability: { label: "Yield stability", hint: "Drought and heat risk" },
  simplicity: { label: "Simplicity", hint: "Fewer crops and machines" },
};

export const DEFAULT_RANKING: Priority[] = ["soil_health", "water", "stability", "simplicity"];

/** Rank-order centroid weights (Barron & Barrett 1996): with k ranked, place i gets
 *  (1/k) * sum(1/j for j = i..k), i.e. 52/27/15/6 % for four. Unranked priorities get 0. */
export function rocWeights(ranked: Priority[]): Weights {
  const k = ranked.length;
  const weights: Weights = { soil_health: 0, water: 0, stability: 0, simplicity: 0 };
  ranked.forEach((p, i) => {
    let sum = 0;
    for (let j = i + 1; j <= k; j++) sum += 1 / j;
    weights[p] = Math.round((sum / k) * 1000) / 1000;
  });
  return weights;
}

export function ordinal(n: number) {
  return `${n}${["th", "st", "nd", "rd"][n % 10 > 3 || Math.floor(n / 10) === 1 ? 0 : n % 10]}`;
}
