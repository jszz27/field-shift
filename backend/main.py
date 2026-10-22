"""Field Shift API (plan §6): climate shift, soil, hazards, recommendations and scores.

Run from backend/:  uvicorn main:app --reload
With OFFLINE=1 the API serves the demo-site snapshots only (no network).
"""
import math
import os
from typing import Annotated

import numpy as np
import requests
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import snapshots
from climate_shift import NOW, THEN, compare_periods, takeaways, yearly_indicators
from eonet_client import fetch_hazards
from power_client import fetch_power_daily
from scoring import describe, recommend, score_rotation
from soil_client import FAO56_AWC_MM_PER_M, get_soil, manual_profile

app = FastAPI(title="Field Shift API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

Lat = Annotated[float, Query(ge=-90, le=90)]
Lon = Annotated[float, Query(ge=-180, le=180)]
CropList = Annotated[list[str], Field(min_length=1, max_length=5)]


@app.exception_handler(FileNotFoundError)
def no_snapshot(request, err):
    return JSONResponse(status_code=503, content={"detail": str(err)})


@app.exception_handler(requests.RequestException)
def upstream_failed(request, err):
    return JSONResponse(status_code=502, content={"detail": f"Data service failed: {err}"})


@app.exception_handler(ValueError)
def bad_input(request, err):
    return JSONResponse(status_code=422, content={"detail": str(err)})


def clean(value):
    """JSON-safe copy: numpy numbers to Python, NaN to None, tuples to lists."""
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


class SoilInput(BaseModel):
    """A soil profile from GET /api/soil, or just a texture class picked by the user."""
    texture_class: str
    awc_mm_per_m: float | None = None
    organic_matter_pct: float | None = None
    source: str | None = None

    def profile(self):
        if self.awc_mm_per_m is None:
            if self.texture_class not in FAO56_AWC_MM_PER_M:
                raise ValueError(f"Unknown texture {self.texture_class!r}; use one of {sorted(FAO56_AWC_MM_PER_M)}")
            return manual_profile(self.texture_class, self.organic_matter_pct)
        return self.model_dump()


class Weights(BaseModel):
    soil_health: float = Field(1.0, ge=0)
    water: float = Field(1.0, ge=0)
    stability: float = Field(1.0, ge=0)
    simplicity: float = Field(1.0, ge=0)


class RecommendRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    baseline: CropList
    soil: SoilInput | None = None
    weights: Weights = Weights()
    years: list[Annotated[int, Field(ge=2, le=5)]] | None = None
    pack: str | None = None
    top: int = Field(5, ge=1, le=20)


class ScoreRequest(RecommendRequest):
    rotation: CropList
    covers: list[str | None] | None = None


def public(r, crops):
    """A scored rotation as the frontend sees it."""
    keys = ("rotation", "covers", "final", "scores", "metrics", "reasons", "skipped", "assumed_timing", "rule_breaks")
    return {"label": describe(r["rotation"], crops), **{k: r[k] for k in keys if k in r}}


def site_summary(result):
    return {"zone": result["zone"], "pack": result["pack"], "soil": result["soil"], "ranked_on": result["ranked_on"]}


@app.get("/api/climate-shift")
def climate_shift(lat: Lat, lon: Lon):
    table = compare_periods(yearly_indicators(fetch_power_daily(lat, lon), lat))
    return clean({
        "lat": lat, "lon": lon, "zone": table.attrs["zone"],
        "season_year_start_month": table.attrs["year_start"],
        "periods": {"then": THEN, "now": NOW},
        "indicators": takeaways(table),
        "source": "NASA POWER daily point data (AG community)",
        "offline": snapshots.offline(),
    })


@app.get("/api/soil")
def soil(lat: Lat, lon: Lon):
    profile = get_soil(lat, lon)
    return clean({
        "lat": lat, "lon": lon, "profile": profile, "source": profile["source"] if profile else None,
        "manual_textures": sorted(FAO56_AWC_MM_PER_M),  # choices when no soil service covers the point
        "offline": snapshots.offline(),
    })


@app.get("/api/hazards")
def hazards(lat: Lat, lon: Lon):
    """EONET events near the point, as GeoJSON. Context only: never used in scoring."""
    return clean(fetch_hazards(lat, lon))


@app.post("/api/recommend")
def recommend_rotations(req: RecommendRequest):
    result = recommend(req.lat, req.lon, req.pack, req.baseline, req.weights.model_dump(),
                       req.soil.profile() if req.soil else None, req.top, req.years)
    crops = result["site"]["crops"]
    return clean({
        **site_summary(result),
        "n_valid": result["n_valid"], "n_comparable": result["n_comparable"],
        "baseline": public(result["baseline"], crops),
        "rotations": [public(r, crops) for r in result["rotations"]],
    })


@app.post("/api/score")
def score(req: ScoreRequest):
    result = score_rotation(req.lat, req.lon, req.pack, req.baseline, req.rotation, req.covers,
                            req.weights.model_dump(), req.soil.profile() if req.soil else None, req.years)
    crops = result["site"]["crops"]
    return clean({
        **site_summary(result),
        "baseline": public(result["baseline"], crops),
        "rotation": public(result["rotation"], crops),
        "rank": result["rank"], "n_comparable": result["n_comparable"],
    })
