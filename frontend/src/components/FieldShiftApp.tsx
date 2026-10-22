"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import type { Point } from "@/lib/api";
import InputsPanel from "./InputsPanel";

// Leaflet touches `window`, so the map renders only in the browser
const MapPicker = dynamic(() => import("./MapPicker"), {
  ssr: false,
  loading: () => <div className="flex h-full items-center justify-center text-sm text-zinc-500">Loading map…</div>,
});

export default function FieldShiftApp() {
  const [point, setPoint] = useState<Point | null>(null);

  return (
    <div className="flex min-h-screen flex-col bg-zinc-50 text-zinc-900 lg:h-screen">
      <header className="border-b border-zinc-200 bg-white px-4 py-3 sm:px-6">
        <h1 className="text-lg font-semibold">Field Shift</h1>
        <p className="text-sm text-zinc-600">Crop rotations for the climate your field has now</p>
      </header>

      <main className="flex flex-1 flex-col lg:min-h-0 lg:flex-row">
        <section className="h-[60vh] lg:h-auto lg:flex-1" aria-label="Map: click to choose a field">
          <MapPicker point={point} onPick={setPoint} />
        </section>

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
          {point && <InputsPanel key={`${point.lat},${point.lon}`} point={point} />}
        </aside>
      </main>
    </div>
  );
}
