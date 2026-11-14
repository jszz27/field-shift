# Field Shift

**Crop rotations for the climate your field has now, built on 40+ years of NASA data.**

NASA Space Apps Challenge 2026 project · Live app: **https://field-shift-pi.vercel.app**

A farmer drops a pin on their field. Field Shift:

1. **Shows how the climate there has shifted.** It compares 1981–2000 with 2005–2024 at that exact point,
   using daily NASA POWER weather: frost dates, growing heat, days above 35 °C, growing-season rain and
   its variability, dry spells, water demand (ET0) and root-zone wetness. Where there is no regular
   frost, it measures the rainy season instead.
2. **Reads the soil.** USDA SSURGO in the US, ISRIC SoilGrids elsewhere; the farmer can override it with
   a soil texture.
3. **Asks what the farmer grows now** and has them **rank four priorities**: soil health, water
   conservation, yield stability and simplicity.
4. **Generates and ranks every valid 2–5 year rotation** against current practice. Each one comes with
   plain-language reasons tied to the measured climate shift. Any crop can be swapped and re-scored, and
   every formula, input and source is shown in the app.

Example: near Ames, Iowa, the first fall frost now comes 9 days later (Oct 10 → Oct 19), so a cereal
rye cover crop fits after harvest. With soil health ranked first, three years of alfalfa then corn
scores 71.6 against 22.9 for continuous corn. It cuts fertilizer nitrogen from 203 to 28 kg/ha a year.

## Data

| Source | Used for |
|---|---|
| [NASA POWER](https://power.larc.nasa.gov/) daily API (AG community), 1981–2024: T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, WS2M, ALLSKY_SFC_SW_DWN, GWETTOP, GWETROOT | Climate-shift indicators, FAO-56 ET0, daily crop water balance |
| [NASA EONET](https://eonet.gsfc.nasa.gov/) v3 events | Hazard context near the field (not scored) |
| [USDA NRCS SSURGO](https://sdmdataaccess.sc.egov.usda.gov/) / [ISRIC SoilGrids 2.0](https://soilgrids.org/) | Soil texture, water-holding capacity, organic matter, drainage |
| [`data/crops.json`](data/crops.json) | Crop knowledge base: 17 crops, 5 region packs, 177 values, each citing one of 19 sources (FAO-56, FAO-33, USDA, university extension, Sacks et al. 2010) |

## How it works

- **Climate shift** (`backend/climate_shift.py`): per-year indicators averaged over each 20-year
  period. Climate zones decide which apply: northern temperate, southern temperate (season year
  Jul–Jun), or frost-free. For frost-free zones, the rainy season comes from the FAO rain-vs-ET0 rule
  with Sivakumar's false-start check.
- **ET0** (`backend/et0.py`): FAO-56 Penman-Monteith from POWER weather.
- **Rotations** (`backend/rotations.py`): every 2–5 year cycle from the region's crop pack, filtered by
  farming rules: no annual crop two years running, alfalfa stands of 2–3 years, winter wheat only after
  an early enough harvest, no alfalfa on poorly drained soil. A cover crop is added where the harvest
  leaves enough days before the site's current first fall frost.
- **Scoring** (`backend/scoring.py`): each crop is simulated through 20 seasons of real weather with an
  FAO-56 root-zone water balance. Six measures (nitrogen, soil cover, diversity, water demand, climate
  risk, simplicity) are scaled 0–100 within the rotations compared. The farmer's priority ranking
  becomes weights by the rank-order centroid method (Barron & Barrett 1996). **A value without a
  source is never guessed**: the measure that needs it is skipped, and the app says so.
- **API** (`backend/main.py`): FastAPI. **Website** (`frontend/`): Next.js, React, Tailwind, Leaflet,
  Recharts.

## Run it locally

Requirements: Python 3.12 and Node.js 20.9+.

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn main:app --port 8000

# Website (second terminal)
cd frontend
npm install
npm run dev          # http://localhost:3000
```

On Windows, `.\run_demo.ps1` starts both. By default it runs offline: only the two demo fields work
(Ames, Iowa and Niamey, Niger), served from `snapshots/`. Use `-Online` for any point on Earth, and
`-Rebuild` after code changes. Set `OFFLINE=1` to run the backend from snapshots only.

Tests: `cd backend; .\.venv\Scripts\python -m pytest` (73 tests).

Deployment: the website is on Vercel (root directory `frontend`, `NEXT_PUBLIC_API_URL` = backend URL);
the API is on Render via [`render.yaml`](render.yaml) (set `CORS_ORIGINS` to the website URL).

## Limitations

- Scores compare the rotations with each other. They are not yield predictions or professional advice.
- Crop data is richest for the US Midwest. Some tropical crop values are not sourced yet, so those
  measures are skipped there.
- Southern-temperate sites use Argentine Pampas planting dates. Regions with two rainy seasons a year
  (e.g. East Africa) are not handled well yet. Irrigated farming is not modelled.
- Climate data comes from the POWER grid (about 0.5°), so neighbouring fields share climate numbers;
  soil is specific to the point.
- No crop-suitability check by season length yet: very cold places can still get corn rotations.

## Use of AI

Built with **Anthropic's Claude (Claude Code) as a coding and writing assistant**, under the team's
direction. The idea, the challenge choice and all design and agronomic decisions are the team's own.
Claude helped write and test much of the code in this repository (backend, frontend and tests), research
and check crop-value sources, debug, and draft documentation. Commits it co-wrote carry a
`Co-Authored-By: Claude` line. Every change was reviewed by the team and covered by tests. No
AI-generated images, audio or video are used.

## Credits

Built for the NASA Space Apps Challenge 2026. Map data © OpenStreetMap contributors; offline outlines
from Natural Earth via [world-atlas](https://github.com/topojson/world-atlas). NASA POWER data is from
the NASA Langley Research Center POWER Project, funded through the NASA Earth Science Directorate
Applied Science Program. Full source list: in the app, open "How each score is computed" → Sources.
