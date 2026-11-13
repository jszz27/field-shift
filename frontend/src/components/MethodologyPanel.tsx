"use client";

import { useEffect, useState } from "react";
import {
  api, type MethodologyResponse, type ScoredRotation, type SoilProfile, type SourcedValue, type Weights,
} from "@/lib/api";
import { ordinal, PRIORITIES, type Priority } from "@/lib/priorities";

const ORDER = ["n_balance", "soil_cover", "diversity", "water_demand", "climate_risk", "simplicity"];

// Raw measures behind each score, with their units
const MEASURES: Record<string, [string, string][]> = {
  n_balance: [["n_balance", "kg N/ha/yr"]],
  soil_cover: [["soil_cover", "% of the year"]],
  diversity: [["diversity", "crops + families"]],
  water_demand: [["water_demand", "mm/yr irrigation gap"]],
  climate_risk: [["yield_loss_pct", "% yield loss"], ["heat_days", "heat days"]],
};

const FIELD_LABELS: Record<string, string> = {
  kc: "Crop coefficient Kc", rooting_depth_m: "Rooting depth (m)", depletion_p: "Depletion fraction p",
  ky: "Yield response ky", heat: "Heat threshold", n_effect: "N effect", n_season: "N season",
  n_need_kg_ha: "N rate (kg/ha)", next_crop_n_adjust_kg_ha: "N credit to next crop (kg/ha)",
  residue_cover: "Residue", cover: "Cover-crop timing", stage_days: "Stage lengths (days)",
  plant: "Planting window", harvest: "Harvest window", plant_after: "Planting after rains",
  family: "Plant family", type: "Type",
};

// "1st Soil health (52%) · 2nd Water conservation (27%) · …", then the priorities left out
function priorityLine(weights: Weights) {
  const keys = (Object.keys(PRIORITIES) as Priority[]).sort((a, b) => weights[b] - weights[a]);
  const ranked = keys.filter((k) => weights[k] > 0).map((k, i) =>
    `${ordinal(i + 1)} ${PRIORITIES[k].label} (${Math.round(weights[k] * 100)}%)`);
  const skipped = keys.filter((k) => !(weights[k] > 0)).map((k) => PRIORITIES[k].label);
  return ranked.join(" · ") + (skipped.length ? `. Doesn’t matter: ${skipped.join(", ")}` : "");
}

function format(value: unknown): string {
  if (value == null) return "not sourced";
  if (Array.isArray(value)) {
    return value.length === 2 && value.every((v) => typeof v === "number") ? `${value[0]}–${value[1]}` : value.map(format).join(", ");
  }
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([k, v]) => `${k.replaceAll("_", " ")} ${format(v)}`)
      .join(", ");
  }
  return String(value);
}

function siteInputs(key: string, soil: SoilProfile, zone: string): [string, string] | null {
  const soilSource = soil.source.startsWith("SSURGO") ? "ssurgo" : soil.source.startsWith("SoilGrids") ? "soilgrids" : "manual_soil";
  const all: Record<string, [string, string]> = {
    awc_mm_per_m: [`Soil holds ${soil.awc_mm_per_m} mm of water per m (${soil.texture_class})`, soilSource],
    PRECTOTCORR: ["Daily rain, 2005–2024", "power"],
    et0: ["Daily reference evapotranspiration ET0, 2005–2024", "fao56_et0"],
    T2M: ["Daily mean air temperature, 2005–2024", "power"],
    first_fall_frost: ["Current first fall frost (2005–2024 mean)", "power"],
    rain_onset: ["Rainy-season onset each year (rain vs ET0)", "power"],
  };
  if (key === "first_fall_frost" && zone === "tropical") return null;
  if (key === "rain_onset" && zone !== "tropical") return null;
  return all[key] ?? null;
}

function SourceLink({ id, sources }: { id: string | null; sources: MethodologyResponse["sources"] }) {
  if (!id) return null;
  const s = sources[id];
  const label = <sup className="ml-0.5 text-[10px] text-zinc-500">[{id}]</sup>;
  return s?.url ? (
    <a href={s.url} target="_blank" rel="noreferrer" title={s.title} className="hover:underline">{label}</a>
  ) : (
    <span title={s?.title}>{label}</span>
  );
}

const rounded = (v: number | null | undefined) => (v == null ? null : Math.round(v * 10) / 10);

type Props = {
  pack: string;
  zone: string;
  rotation: ScoredRotation;
  baseline: ScoredRotation;
  soil: SoilProfile;
  weights: Weights;
};

export default function MethodologyPanel({ pack, zone, rotation, baseline, soil, weights }: Props) {
  const [m, setM] = useState<MethodologyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    api.methodology(pack).then((d) => current && setM(d), (e: Error) => current && setError(e.message));
    return () => {
      current = false;
    };
  }, [pack]);

  if (error) return <p className="mt-3 rounded-md bg-red-50 p-2 text-sm text-red-800">{error}</p>;
  if (!m) return <p className="mt-3 text-sm text-zinc-500">Loading the methodology…</p>;

  const cashIds = [...new Set(rotation.rotation)];
  const coverIds = [...new Set(rotation.covers.filter((c): c is string => !!c))];
  const used = new Set<string>();
  const cite = (f: SourcedValue | undefined) => {
    if (f?.source && f.value != null) used.add(f.source);
    return f;
  };

  return (
    <div className="mt-4 flex flex-col gap-3">
      <h3 className="font-semibold">How each score is computed</h3>
      {ORDER.map((key) => {
        const ind = m.indicators[key];
        const ids = key === "soil_cover" ? [...cashIds, ...coverIds] : cashIds;
        const fields = [...ind.crop, ...ind.pack].filter((f) =>
          ids.some((id) => f === "type" || f in m.crops[id].library || f in m.crops[id].pack),
        );
        const describe = (r: ScoredRotation) => {
          if (key === "simplicity") {
            const n = new Set(r.rotation).size;
            const penalty = (r.metrics.simplicity ?? n) - n;  // perennial penalties the backend added
            return `${n} crop${n === 1 ? "" : "s"}${penalty > 0 ? ` + ${penalty} for a perennial` : ""}`;
          }
          return MEASURES[key].map(([k, unit]) => `${format(rounded(r.metrics[k]))} ${unit}`).join(", ");
        };
        const sites = ind.site.map((s) => siteInputs(s, soil, zone)).filter((s): s is [string, string] => !!s);
        sites.forEach(([, source]) => used.add(source));
        const score = rotation.scores[key];
        return (
          <details key={key} className="rounded-md border border-zinc-200 p-3 text-sm">
            <summary className="cursor-pointer font-medium">
              {ind.name}: score {score == null ? "not scored" : Math.round(score)}
              <span className="font-normal text-zinc-500">
                {" "}· {describe(rotation)} (current practice {describe(baseline)}; {ind.better} is better)
              </span>
            </summary>
            <p className="mt-2"><span className="font-medium">Formula.</span> {ind.formula}</p>
            {rotation.skipped[key] && <p className="mt-1 text-amber-900">Not scored here: {rotation.skipped[key]}.</p>}
            {fields.length > 0 && (
              <div className="mt-2 overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-zinc-500">
                      <th className="py-1 pr-3 font-medium">Crop</th>
                      {fields.map((f) => <th key={f} className="py-1 pr-3 font-medium">{FIELD_LABELS[f] ?? f}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {ids.map((id) => {
                      const crop = m.crops[id];
                      return (
                        <tr key={id} className="border-t border-zinc-100 align-top">
                          <td className="py-1 pr-3 font-medium">{crop.name}</td>
                          {fields.map((f) => {
                            const value = f === "type" ? { value: crop.type, source: null } : cite(crop.library[f] ?? crop.pack[f]);
                            const legume = crop.library.n_effect?.value === "fixes";
                            if (legume && (f === "n_need_kg_ha" || f === "n_season") && value?.value == null) {
                              return <td key={f} className="py-1 pr-3 text-zinc-500">not needed (legume)</td>;
                            }
                            if (f === "plant" && crop.type === "perennial" && value?.value == null) {
                              // perennials are not sown each year: their season runs from the last spring frost
                              used.add("power");
                              return (
                                <td key={f} className="py-1 pr-3">
                                  from last spring frost<SourceLink id="power" sources={m.sources} />
                                </td>
                              );
                            }
                            return (
                              <td key={f} className={`py-1 pr-3 ${value?.value == null ? "text-zinc-400" : ""}`}>
                                {value ? format(value.value) : "–"}
                                <SourceLink id={value?.value == null ? null : value.source} sources={m.sources} />
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
            {sites.length > 0 && (
              <ul className="mt-2 list-disc pl-4 text-xs text-zinc-700">
                {sites.map(([text, source]) => (
                  <li key={text}>{text}<SourceLink id={source} sources={m.sources} /></li>
                ))}
              </ul>
            )}
            {ind.assumptions.length > 0 && (
              <ul className="mt-2 list-disc pl-4 text-xs text-zinc-500">
                {ind.assumptions.map((a) => <li key={a}>Assumption: {a}</li>)}
              </ul>
            )}
          </details>
        );
      })}

      <details className="rounded-md border border-zinc-200 p-3 text-sm">
        <summary className="cursor-pointer font-medium">Final score: {rotation.final ?? "not ranked"}</summary>
        <p className="mt-2">{m.final}</p>
        <p className="mt-1 text-xs text-zinc-600">
          Your priorities: {priorityLine(weights)}
        </p>
      </details>

      <details className="rounded-md border border-zinc-200 p-3 text-sm">
        <summary className="cursor-pointer font-medium">Sources ({used.size})</summary>
        <ul className="mt-2 flex flex-col gap-1 text-xs">
          {[...used].sort().map((id) => (
            <li key={id}>
              <span className="text-zinc-500">[{id}]</span>{" "}
              {m.sources[id]?.url ? (
                <a href={m.sources[id].url!} target="_blank" rel="noreferrer" className="text-green-800 hover:underline">
                  {m.sources[id].title}
                </a>
              ) : (
                m.sources[id]?.title ?? id
              )}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
