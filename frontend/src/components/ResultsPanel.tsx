"use client";

import { useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type Crop, type ScoreResponse, type ScoredRotation } from "@/lib/api";
import type { Recommendation } from "./InputsPanel";

const INDICATORS = [
  { key: "n_balance", label: "Nitrogen" },
  { key: "soil_cover", label: "Soil cover" },
  { key: "diversity", label: "Diversity" },
  { key: "water_demand", label: "Water" },
  { key: "climate_risk", label: "Climate risk" },
  { key: "simplicity", label: "Simplicity" },
];

const METRICS: { key: string; label: string; unit: string; lowerIsBetter: boolean }[] = [
  { key: "n_balance", label: "Fertilizer N", unit: "kg N/ha/yr", lowerIsBetter: true },
  { key: "soil_cover", label: "Soil covered", unit: "% of year", lowerIsBetter: false },
  { key: "water_demand", label: "Irrigation gap", unit: "mm/yr", lowerIsBetter: true },
  { key: "yield_loss_pct", label: "Water-limited yield loss", unit: "%", lowerIsBetter: true },
  { key: "heat_days", label: "Heat days in mid-season", unit: "days", lowerIsBetter: true },
];

const FAMILY_STYLE: Record<string, string> = {
  grass: "bg-amber-100 text-amber-900 border-amber-200",
  legume: "bg-green-100 text-green-900 border-green-200",
  aster: "bg-yellow-100 text-yellow-900 border-yellow-200",
  brassica: "bg-purple-100 text-purple-900 border-purple-200",
  spurge: "bg-orange-100 text-orange-900 border-orange-200",
};

type CropIndex = Record<string, Crop>;

const shortName = (crops: CropIndex, id: string) => (crops[id]?.name ?? id).split(" (")[0];

function Strip({ r, crops, onSwap }: { r: ScoredRotation; crops: CropIndex; onSwap?: (year: number, id: string) => void }) {
  const growable = Object.values(crops).filter((c) => c.type !== "cover");
  return (
    <ol className="flex flex-wrap items-center gap-1.5 text-sm">
      {r.rotation.map((id, i) => (
        <li key={i} className="flex items-center gap-1.5">
          {onSwap ? (
            <select
              aria-label={`Year ${i + 1} crop`}
              className={`rounded-md border px-2 py-1 ${FAMILY_STYLE[crops[id]?.family] ?? ""}`}
              value={id}
              onChange={(e) => onSwap(i, e.target.value)}
            >
              {growable.map((c) => (
                <option key={c.id} value={c.id}>{shortName(crops, c.id)}</option>
              ))}
            </select>
          ) : (
            <span className={`rounded-md border px-2 py-1 ${FAMILY_STYLE[crops[id]?.family] ?? ""}`}>
              {i + 1}. {shortName(crops, id)}
            </span>
          )}
          {r.covers[i] && (
            <span className="rounded-md border border-dashed border-green-400 px-2 py-1 text-xs text-green-800">
              + {shortName(crops, r.covers[i]!).toLowerCase()} cover
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}

function CompareChart({ rotation, baseline }: { rotation: ScoredRotation; baseline: ScoredRotation }) {
  const data = INDICATORS.filter(({ key }) => rotation.scores[key] != null || baseline.scores[key] != null).map(
    ({ key, label }) => ({ label, "This rotation": rotation.scores[key], "Current practice": baseline.scores[key] }),
  );
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} interval={0} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
          <Tooltip formatter={(v) => (typeof v === "number" ? Math.round(v) : "not scored")} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {/* minPointSize keeps a score of 0 visible as a sliver instead of a missing bar */}
          <Bar dataKey="Current practice" fill="#a1a1aa" radius={[3, 3, 0, 0]} minPointSize={2} />
          <Bar dataKey="This rotation" fill="#15803d" radius={[3, 3, 0, 0]} minPointSize={2} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function MetricsTable({ rotation, baseline }: { rotation: ScoredRotation; baseline: ScoredRotation }) {
  const show = (v: number | null | undefined) => (v == null ? "–" : Math.round(v).toString());
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs text-zinc-500">
          <th className="py-1 font-medium">Measure</th>
          <th className="py-1 text-right font-medium">Current</th>
          <th className="py-1 text-right font-medium">This rotation</th>
        </tr>
      </thead>
      <tbody>
        {METRICS.map(({ key, label, unit, lowerIsBetter }) => {
          const a = baseline.metrics[key], b = rotation.metrics[key];
          const better = a != null && b != null && Math.round(a) !== Math.round(b) && (lowerIsBetter ? b < a : b > a);
          return (
            <tr key={key} className="border-t border-zinc-100">
              <td className="py-1.5">{label} <span className="text-xs text-zinc-500">({unit})</span></td>
              <td className="py-1.5 text-right tabular-nums">{show(a)}</td>
              <td className={`py-1.5 text-right tabular-nums ${better ? "font-semibold text-green-800" : ""}`}>{show(b)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Notes({ r }: { r: ScoredRotation }) {
  const skipped = Object.entries(r.skipped);
  if (!skipped.length && !r.assumed_timing.length) return null;
  return (
    <ul className="mt-2 flex flex-col gap-1 text-xs text-zinc-500">
      {skipped.map(([k, why]) => (
        <li key={k}>Not scored ({k.replaceAll("_", " ")}): {why}.</li>
      ))}
      {r.assumed_timing.length > 0 && (
        <li>Planting date assumed at rainy-season onset for {r.assumed_timing.join(", ")} (no sourced sowing window).</li>
      )}
    </ul>
  );
}

type Edit = { rotation: string[]; result: ScoreResponse | null; loading: boolean; error: string | null };

export default function ResultsPanel({ result }: { result: Recommendation }) {
  const { request, response } = result;
  const crops: CropIndex = Object.fromEntries(result.crops.map((c) => [c.id, c]));
  const [selected, setSelected] = useState(0);
  const [edit, setEdit] = useState<Edit | null>(null);
  const latest = useRef(0);

  const base = response.baseline;
  const chosen = response.rotations[selected];
  const shown = edit?.result?.rotation ?? (edit ? { ...chosen, rotation: edit.rotation } : chosen);

  function select(i: number) {
    setSelected(i);
    setEdit(null);
  }

  async function swap(year: number, id: string) {
    const rotation = shown.rotation.map((c, i) => (i === year ? id : c));
    const ticket = ++latest.current;  // ignore answers to edits the user has already replaced
    setEdit({ rotation, result: edit?.result ?? null, loading: true, error: null });
    try {
      const res = await api.score({ ...request, rotation });
      if (ticket === latest.current) setEdit({ rotation, result: res, loading: false, error: null });
    } catch (e) {
      if (ticket === latest.current) setEdit({ rotation, result: null, loading: false, error: (e as Error).message });
    }
  }

  if (!chosen) {
    return (
      <p className="p-4 text-sm text-zinc-600 sm:p-6">
        No rotation could be compared with your current practice here: the crop data for this region is incomplete.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-5 p-4 sm:p-6">
      <div>
        <h2 className="text-lg font-semibold">Recommended rotations</h2>
        <p className="text-sm text-zinc-600">
          Your current practice, <span className="font-medium">{base.label}</span>, scores{" "}
          <span className="font-medium tabular-nums">{base.final}</span> / 100. Showing the top{" "}
          {response.rotations.length} of {response.n_comparable} rotations scored on the same measures
          ({response.n_valid} pass the farming rules).
        </p>
      </div>

      <ol className="grid gap-3 xl:grid-cols-2">
        {response.rotations.map((r, i) => (
          <li key={r.rotation.join("-")}>
            <button
              type="button"
              onClick={() => select(i)}
              aria-pressed={i === selected}
              className={`flex w-full flex-col gap-2 rounded-lg border bg-white p-3 text-left transition ${
                i === selected ? "border-green-700 ring-2 ring-green-700/20" : "border-zinc-200 hover:border-zinc-400"
              }`}
            >
              <span className="flex items-baseline justify-between gap-2">
                <span className="text-sm font-semibold">#{i + 1} {r.label}</span>
                <span className="text-lg font-semibold tabular-nums text-green-800">{r.final}</span>
              </span>
              <Strip r={r} crops={crops} />
              <ul className="list-disc pl-4 text-sm text-zinc-700">
                {r.reasons?.map((reason) => <li key={reason}>{reason}</li>)}
              </ul>
            </button>
          </li>
        ))}
      </ol>

      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="font-semibold">Compare with current practice</h3>
          <p className="text-sm tabular-nums">
            {edit?.loading ? (
              <span className="text-zinc-500">Re-scoring…</span>
            ) : edit?.result ? (
              edit.result.rank ? (
                <>Your edit: <b>{edit.result.rotation.final}</b> · rank {edit.result.rank} of {edit.result.n_comparable + 1}</>
              ) : edit.result.rotation.rule_breaks?.length ? (
                <>Your edit: <b>{edit.result.rotation.final}</b> · not ranked, it breaks a farming rule</>
              ) : (
                <>Your edit can&apos;t be scored on the same measures</>
              )
            ) : (
              <>Score <b>{chosen.final}</b> vs <b>{base.final}</b> now</>
            )}
          </p>
        </div>

        <p className="mt-3 text-xs font-medium uppercase tracking-wide text-zinc-500">Swap a crop</p>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <Strip r={shown} crops={crops} onSwap={swap} />
          {edit && (
            <button type="button" className="text-sm text-zinc-600 hover:underline" onClick={() => setEdit(null)}>
              Reset
            </button>
          )}
        </div>
        {edit?.error && <p className="mt-2 rounded-md bg-red-50 p-2 text-sm text-red-800">{edit.error}</p>}
        {edit?.result?.rotation.rule_breaks?.map((b) => (
          <p key={b} className="mt-2 rounded-md bg-amber-50 p-2 text-sm text-amber-900">Breaks a farming rule: {b.split(": ")[1]}</p>
        ))}

        <div className={edit?.loading ? "opacity-50 transition-opacity" : ""}>
          <CompareChart rotation={shown} baseline={base} />
          <MetricsTable rotation={shown} baseline={base} />
          <Notes r={shown} />
          {edit?.result?.rotation.reasons && (
            <ul className="mt-3 list-disc pl-4 text-sm text-zinc-700">
              {edit.result.rotation.reasons.map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
          )}
        </div>
        <p className="mt-3 text-xs text-zinc-500">
          Scores are 0–100 relative to the rotations compared here (100 = best of the set), weighted by your priorities.
        </p>
      </section>
    </div>
  );
}
