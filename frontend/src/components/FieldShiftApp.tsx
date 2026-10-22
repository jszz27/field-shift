"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import type { Point } from "@/lib/api";
import ClimateShiftPanel from "./ClimateShiftPanel";
import InputsPanel, { type Recommendation } from "./InputsPanel";
import ResultsPanel from "./ResultsPanel";

// Leaflet touches `window`, so the map renders only in the browser
const MapPicker = dynamic(() => import("./MapPicker"), {
  ssr: false,
  loading: () => <div className="flex h-full items-center justify-center text-sm text-zinc-500">Loading map…</div>,
});

type Tab = "results" | "climate";

export default function FieldShiftApp() {
  const [point, setPoint] = useState<Point | null>(null);
  const [result, setResult] = useState<Recommendation | null>(null);
  const [tab, setTab] = useState<Tab>("climate");
  const pointKey = point ? `${point.lat},${point.lon}` : "";

  function pick(p: Point) {
    setPoint(p);
    setResult(null);  // results belong to the previous field
    setTab("climate");
  }

  function showResult(r: Recommendation) {
    setResult(r);
    setTab("results");
  }

  const tabs: { id: Tab; label: string }[] = [
    ...(result ? [{ id: "results" as Tab, label: "Recommendations" }] : []),
    { id: "climate", label: "Climate shift" },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-zinc-50 text-zinc-900 lg:h-screen">
      <header className="border-b border-zinc-200 bg-white px-4 py-3 sm:px-6">
        <h1 className="text-lg font-semibold">Field Shift</h1>
        <p className="text-sm text-zinc-600">Crop rotations for the climate your field has now</p>
      </header>

      <main className="flex flex-1 flex-col lg:min-h-0 lg:flex-row">
        <div className="flex flex-col lg:min-h-0 lg:flex-1">
          <section
            className={point ? "h-[50vh] lg:h-[40%] lg:shrink-0" : "h-[60vh] lg:h-full"}
            aria-label="Map: click to choose a field"
          >
            <MapPicker point={point} onPick={pick} />
          </section>
          {point && (
            <div className="flex flex-col border-t border-zinc-200 lg:min-h-0 lg:flex-1">
              <nav className="flex gap-1 border-b border-zinc-200 bg-white px-4 sm:px-6" aria-label="Views">
                {tabs.map(({ id, label }) => (
                  <button
                    key={id}
                    type="button"
                    aria-current={tab === id ? "page" : undefined}
                    onClick={() => setTab(id)}
                    className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
                      tab === id ? "border-green-700 text-green-800" : "border-transparent text-zinc-500 hover:text-zinc-800"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </nav>
              <div className="lg:min-h-0 lg:flex-1 lg:overflow-y-auto">
                {result && (
                  <section hidden={tab !== "results"} aria-label="Recommendations">
                    <ResultsPanel key={JSON.stringify(result.request)} result={result} />
                  </section>
                )}
                {/* Kept mounted while hidden so switching tabs does not refetch */}
                <section hidden={tab !== "climate"} aria-label="Climate shift">
                  <ClimateShiftPanel key={pointKey} point={point} />
                </section>
              </div>
            </div>
          )}
        </div>

        <aside className="w-full border-t border-zinc-200 bg-white p-4 sm:p-6 lg:w-96 lg:overflow-y-auto lg:border-l lg:border-t-0">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">Your field</h2>
          {point ? (
            <dl className="mt-3 grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-zinc-50 p-3">
                <dt className="text-xs text-zinc-500">Latitude</dt>
                <dd className="font-mono text-lg tabular-nums" data-testid="lat">{point.lat.toFixed(2)}</dd>
              </div>
              <div className="rounded-lg bg-zinc-50 p-3">
                <dt className="text-xs text-zinc-500">Longitude</dt>
                <dd className="font-mono text-lg tabular-nums" data-testid="lon">{point.lon.toFixed(2)}</dd>
              </div>
            </dl>
          ) : (
            <p className="mt-3 text-sm text-zinc-600">Click the map to drop a pin on your field.</p>
          )}
          {point && <InputsPanel key={pointKey} point={point} onResult={showResult} />}
        </aside>
      </main>
    </div>
  );
}
