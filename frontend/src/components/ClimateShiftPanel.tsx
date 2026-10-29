"use client";

import { useEffect, useState } from "react";
import { api, type ClimateIndicator, type ClimateShiftResponse, type Point } from "@/lib/api";

const ZONES: Record<ClimateShiftResponse["zone"], string> = {
  north_temperate: "Northern temperate: seasons set by frost",
  south_temperate: "Southern temperate: seasons set by frost (summer is Nov–Mar)",
  tropical: "Frost-free: seasons set by the rains",
};

const UNITS: Record<string, string> = { "°C-days": "°C-days", days: "days", mm: "mm", "%": "%", seasons: "" };

function change(r: ClimateIndicator) {
  if (r.direction === "same") return "no clear change";
  if (r.unit === "date") {
    const days = Math.abs(Math.round(r.now) - Math.round(r.then));
    return `${days} days ${r.direction === "up" ? "later" : "earlier"}`;
  }
  const sign = r.change > 0 ? "+" : "−";
  const digits = r.unit === "0-1" ? 2 : Math.abs(r.change) < 10 ? 1 : 0;
  const unit = r.unit === "%" ? "pts" : UNITS[r.unit] ?? "";  // a change in a % is in percentage points
  return `${sign}${Math.abs(r.change).toFixed(digits)} ${unit}`.trim();
}

function Card({ r }: { r: ClimateIndicator }) {
  const arrow = r.direction === "same" ? "→" : r.direction === "up" ? "↑" : "↓";
  return (
    <article className="flex flex-col gap-1 rounded-lg border border-zinc-200 bg-white p-3">
      <h3 className="text-sm font-medium text-zinc-700">{r.label}</h3>
      <p className="text-xl tabular-nums">
        <span className="text-zinc-500">{r.then_display}</span>
        <span className="mx-1.5 text-zinc-400">→</span>
        <span className="font-semibold">{r.now_display}</span>
        {r.unit !== "date" && r.unit !== "0-1" && <span className="ml-1 text-sm text-zinc-500">{UNITS[r.unit]}</span>}
      </p>
      <p className="text-xs font-medium text-zinc-600">
        <span aria-hidden>{arrow}</span> {change(r)}
      </p>
      <p className="text-sm text-zinc-700">{r.meaning}</p>
    </article>
  );
}

export default function ClimateShiftPanel({ point }: { point: Point }) {
  const [data, setData] = useState<ClimateShiftResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // The parent remounts this panel for every new pin
  useEffect(() => {
    let current = true;
    api.climateShift(point).then((d) => current && setData(d), (e: Error) => current && setError(e.message));
    return () => {
      current = false;
    };
  }, [point]);

  return (
    <div className="p-4 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold">How the climate has shifted here</h2>
        {data && (
          <p className="text-sm text-zinc-600">
            {data.periods.then.join("–")} vs {data.periods.now.join("–")}
            {data.offline && (
              <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-900">
                using saved data
              </span>
            )}
          </p>
        )}
      </div>
      {error && <p className="mt-3 rounded-md bg-red-50 p-2 text-sm text-red-800">{error}</p>}
      {!data && !error && (
        <p className="mt-3 text-sm text-zinc-500">
          Loading 44 years of NASA POWER weather for this point (about 30 seconds the first time)…
        </p>
      )}
      {data && (
        <>
          <p className="mt-1 text-sm text-zinc-600">{ZONES[data.zone]}</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {data.indicators.map((r) => (
              <Card key={r.indicator} r={r} />
            ))}
          </div>
          <p className="mt-3 text-xs text-zinc-500">Source: {data.source}. Each value is a 20-year average.</p>
        </>
      )}
    </div>
  );
}
