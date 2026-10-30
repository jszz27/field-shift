// Client for the Field Shift FastAPI backend (backend/main.py)

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Point = { lat: number; lon: number };

export type SoilProfile = {
  source: string;
  name?: string | null;
  texture_class: string;
  organic_matter_pct: number | null;
  awc_mm_per_m: number;
  drainage: string | null;
};

export type SoilResponse = { profile: SoilProfile | null; source: string | null; manual_textures: string[] };

export type Crop = { id: string; name: string; family: string; type: "cash" | "cover" | "perennial" };

// baseline: a demo field's current practice (crop ids), null elsewhere
export type CropsResponse = { zone: string; pack: string; crops: Crop[]; baseline: string[] | null };

export type DemoSite = Point & { id: string; name: string };

export type DemoSitesResponse = { sites: DemoSite[]; offline: boolean };

export type Weights = { soil_health: number; water: number; stability: number; simplicity: number };

// A detected profile, or just a texture class the user picked
export type SoilInput = Partial<SoilProfile> & { texture_class: string };

export type RecommendRequest = Point & { baseline: string[]; soil?: SoilInput; weights: Weights };

export type ScoredRotation = {
  label: string;
  rotation: string[];
  covers: (string | null)[];
  final: number | null;
  scores: Record<string, number | null>;
  metrics: Record<string, number | null>;
  reasons?: string[];
  skipped: Record<string, string>;
  assumed_timing: string[];
  rule_breaks?: string[];
};

export type ScoreRequest = RecommendRequest & { rotation: string[] };

export type ScoreResponse = {
  pack: string;
  ranked_on: string[];
  baseline: ScoredRotation;
  rotation: ScoredRotation;
  rank: number | null;
  n_comparable: number;
};

export type RecommendResponse = {
  zone: string;
  pack: string;
  soil: SoilProfile;
  ranked_on: string[];
  n_valid: number;
  n_comparable: number;
  baseline: ScoredRotation;
  rotations: ScoredRotation[];
};

export type ClimateIndicator = {
  indicator: string;
  label: string;
  unit: string;
  then: number;
  now: number;
  change: number;
  then_display: string;
  now_display: string;
  direction: "up" | "down" | "same";
  text: string;
  meaning: string;
};

export type ClimateShiftResponse = {
  zone: "north_temperate" | "south_temperate" | "tropical";
  periods: { then: [number, number]; now: [number, number] };
  indicators: ClimateIndicator[];
  source: string;
  offline: boolean;
};

export type SourcedValue = { value: unknown; source: string | null };

export type MethodologyIndicator = {
  name: string;
  unit: string;
  better: "lower" | "higher";
  formula: string;
  crop: string[];
  pack: string[];
  site: string[];
  assumptions: string[];
};

export type MethodologyCrop = {
  name: string;
  type: Crop["type"];
  library: Record<string, SourcedValue>;
  pack: Record<string, SourcedValue>;
  notes: Record<string, string>;
};

export type MethodologyResponse = {
  pack: string;
  indicators: Record<string, MethodologyIndicator>;
  final: string;
  crops: Record<string, MethodologyCrop>;
  sources: Record<string, { title: string; url: string | null }>;
};

type ErrorBody = { detail?: string | { msg: string }[] };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new Error(
      "Cannot reach the Field Shift server. If nobody has used it for a while it may be waking up: wait a minute, then try again.",
    );
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = (body as ErrorBody | null)?.detail;
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail;
    throw new Error(message || `API error ${res.status}`);
  }
  return body as T;
}

const query = (p: Point) => `lat=${p.lat}&lon=${p.lon}`;

export const api = {
  demoSites: () => request<DemoSitesResponse>("/api/demo-sites"),
  climateShift: (p: Point) => request<ClimateShiftResponse>(`/api/climate-shift?${query(p)}`),
  soil: (p: Point) => request<SoilResponse>(`/api/soil?${query(p)}`),
  crops: (p: Point) => request<CropsResponse>(`/api/crops?${query(p)}`),
  methodology: (pack: string) => request<MethodologyResponse>(`/api/methodology?pack=${encodeURIComponent(pack)}`),
  recommend: (req: RecommendRequest) => post<RecommendResponse>("/api/recommend", req),
  score: (req: ScoreRequest) => post<ScoreResponse>("/api/score", req),
};

function post<T>(path: string, body: unknown) {
  return request<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}
