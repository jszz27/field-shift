"use client";

import { useEffect, useState } from "react";
import {
  api, type CropsResponse, type Point, type RecommendResponse, type SoilInput, type SoilResponse, type Weights,
} from "@/lib/api";

const MAX_YEARS = 5;

const SLIDERS: { key: keyof Weights; label: string; hint: string }[] = [
  { key: "soil_health", label: "Soil health", hint: "Nitrogen, soil cover, crop variety" },
  { key: "water", label: "Water conservation", hint: "Irrigation gap" },
  { key: "stability", label: "Yield stability", hint: "Drought and heat risk" },
  { key: "simplicity", label: "Simplicity", hint: "Fewer crops and machines" },
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-zinc-200 pt-4">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">{title}</h3>
      <div className="mt-2">{children}</div>
    </section>
  );
}

function Problem({ message }: { message: string }) {
  return <p className="rounded-md bg-red-50 p-2 text-sm text-red-800">{message}</p>;
}

export default function InputsPanel({ point }: { point: Point }) {
  const [soil, setSoil] = useState<SoilResponse | null>(null);
  const [soilError, setSoilError] = useState<string | null>(null);
  const [manualTexture, setManualTexture] = useState("");
  const [crops, setCrops] = useState<CropsResponse | null>(null);
  const [cropsError, setCropsError] = useState<string | null>(null);
  const [baseline, setBaseline] = useState<string[]>([]);
  const [weights, setWeights] = useState<Weights>({ soil_health: 50, water: 50, stability: 50, simplicity: 50 });
  const [result, setResult] = useState<RecommendResponse | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // The parent remounts this panel for every new pin, so these run once per point
  useEffect(() => {
    let current = true;
    api.soil(point).then((s) => current && setSoil(s), (e: Error) => current && setSoilError(e.message));
    api.crops(point).then(
      (c) => {
        if (!current) return;
        setCrops(c);
        const first = c.crops.find((crop) => crop.type !== "cover");
        setBaseline(first ? [first.id] : []);
      },
      (e: Error) => current && setCropsError(e.message),
    );
    return () => {
      current = false;
    };
  }, [point]);

  const growable = crops?.crops.filter((c) => c.type !== "cover") ?? [];
  const soilInput: SoilInput | undefined = manualTexture
    ? { texture_class: manualTexture }
    : soil?.profile ?? undefined;
  const ready = !!soilInput && baseline.length > 0 && !submitting;

  async function submit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      setResult(await api.recommend({ ...point, baseline, soil: soilInput, weights }));
    } catch (e) {
      setSubmitError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  const setYear = (i: number, id: string) => setBaseline((b) => b.map((c, j) => (j === i ? id : c)));

  return (
    <div className="mt-4 flex flex-col gap-4">
      <Section title="Soil">
        {soilError && <Problem message={soilError} />}
        {!soil && !soilError && <p className="text-sm text-zinc-500">Looking up the soil…</p>}
        {soil?.profile && (
          <p className="text-sm">
            <span className="font-medium capitalize">{soil.profile.texture_class}</span>
            {soil.profile.name ? ` (${soil.profile.name})` : ""} · {soil.profile.source}
            <br />
            <span className="text-zinc-600">
              Holds {soil.profile.awc_mm_per_m} mm of water per m
              {soil.profile.organic_matter_pct != null && ` · ${soil.profile.organic_matter_pct}% organic matter`}
              {soil.profile.drainage && ` · ${soil.profile.drainage.toLowerCase()}`}
            </span>
          </p>
        )}
        {soil && (
          <label className="mt-2 block text-sm">
            <span className="text-zinc-600">{soil.profile ? "Or choose a texture" : "No soil data here: choose a texture"}</span>
            <select
              className="mt-1 block w-full rounded-md border border-zinc-300 bg-white p-2"
              value={manualTexture}
              onChange={(e) => setManualTexture(e.target.value)}
            >
              <option value="">{soil.profile ? "Use the detected soil" : "Select…"}</option>
              {soil.manual_textures.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>
        )}
      </Section>

      <Section title="What you grow now">
        {cropsError && <Problem message={cropsError} />}
        {!crops && !cropsError && <p className="text-sm text-zinc-500">Loading the crops for this region…</p>}
        {crops && (
          <>
            <ol className="flex flex-col gap-2">
              {baseline.map((id, i) => (
                <li key={i} className="flex items-center gap-2 text-sm">
                  <span className="w-14 shrink-0 text-zinc-500">Year {i + 1}</span>
                  <select
                    aria-label={`Crop in year ${i + 1}`}
                    className="min-w-0 flex-1 rounded-md border border-zinc-300 bg-white p-2"
                    value={id}
                    onChange={(e) => setYear(i, e.target.value)}
                  >
                    {growable.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                  {baseline.length > 1 && (
                    <button
                      type="button"
                      aria-label={`Remove year ${i + 1}`}
                      className="rounded-md px-2 py-1 text-zinc-500 hover:bg-zinc-100"
                      onClick={() => setBaseline((b) => b.filter((_, j) => j !== i))}
                    >
                      ✕
                    </button>
                  )}
                </li>
              ))}
            </ol>
            {baseline.length < MAX_YEARS && (
              <button
                type="button"
                className="mt-2 text-sm font-medium text-green-700 hover:underline"
                onClick={() => setBaseline((b) => [...b, b[b.length - 1]])}
              >
                + Add a year
              </button>
            )}
            <p className="mt-1 text-xs text-zinc-500">
              One year = the same crop every year. Crop pack: {crops.pack.replaceAll("_", " ")}.
            </p>
          </>
        )}
      </Section>

      <Section title="Your priorities">
        <div className="flex flex-col gap-3">
          {SLIDERS.map(({ key, label, hint }) => (
            <label key={key} className="block text-sm">
              <span className="flex justify-between">
                <span className="font-medium">{label}</span>
                <span className="tabular-nums text-zinc-600">{weights[key]}</span>
              </span>
              <input
                type="range" min={0} max={100} step={5}
                className="w-full accent-green-700"
                value={weights[key]}
                onChange={(e) => setWeights((w) => ({ ...w, [key]: Number(e.target.value) }))}
              />
              <span className="text-xs text-zinc-500">{hint}</span>
            </label>
          ))}
        </div>
      </Section>

      <button
        type="button"
        disabled={!ready}
        onClick={submit}
        className="rounded-md bg-green-700 px-4 py-2 font-medium text-white hover:bg-green-800 disabled:cursor-not-allowed disabled:bg-zinc-300"
      >
        {submitting ? "Scoring rotations…" : "Get recommendations"}
      </button>
      {submitError && <Problem message={submitError} />}

      {result && (
        <Section title="Top rotations">
          <p className="text-xs text-zinc-500">
            Current practice ({result.baseline.label}): {result.baseline.final}. {result.n_comparable} of{" "}
            {result.n_valid} rotations could be compared.
          </p>
          <ol className="mt-2 flex flex-col gap-1 text-sm">
            {result.rotations.map((r) => (
              <li key={r.rotation.join("-")} className="flex justify-between gap-2">
                <span>{r.label}</span>
                <span className="tabular-nums font-medium">{r.final}</span>
              </li>
            ))}
          </ol>
        </Section>
      )}
    </div>
  );
}
