"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { api, type DemoSitesResponse, type Point } from "@/lib/api";
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
  const [demo, setDemo] = useState<DemoSitesResponse | null>(null);
  const pointKey = point ? `${point.lat},${point.lon}` : "";

  useEffect(() => {
    api.demoSites().then(setDemo, () => setDemo(null));  // the buttons are a shortcut: hide them if this fails
  }, []);

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
          {/* Pinned while the panel scrolls (desktop). Sticky stops at the aside's padding edge, so
              -top-6 and the negative margins pull the band up over that padding: content slides
              under a solid band instead of showing through above it */}
          <div className="lg:sticky lg:-top-6 lg:z-10 lg:-mx-6 lg:-mt-6 lg:border-b lg:border-zinc-200 lg:bg-white lg:px-6 lg:pb-4 lg:pt-6">
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
          </div>
          {demo && demo.sites.length > 0 && (
            <div className="mt-3 text-sm">
              <p className="text-zinc-600">
                Or try a demo field:
                {demo.offline && (
                  <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-900">
                    Offline demo mode
                  </span>
                )}
              </p>
              <div className="mt-1 flex flex-wrap gap-2">
                {demo.sites.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => pick({ lat: s.lat, lon: s.lon })}
                    aria-pressed={point?.lat === s.lat && point?.lon === s.lon}
                    className="rounded-md border border-zinc-300 px-2.5 py-1 hover:border-green-700 aria-pressed:border-green-700 aria-pressed:bg-green-50"
                  >
                    {s.name}
                  </button>
                ))}
              </div>
            </div>
          )}
          {point && <InputsPanel key={pointKey} point={point} onResult={showResult} />}
        </aside>
      </main>
    </div>
  );
}
