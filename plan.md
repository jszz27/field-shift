# 🌾 Field Shift: NASA Data-Driven Crop Rotation Decision Support System

> **NASA Space Apps Challenge 2026: Strategy & Implementation Roadmap (v2)**
> Event: **Nov 14–15, 2026** · Full challenge statements: **Oct 28** · Submission & Judging guides: **Nov 13**
> We start building now (Oct 20) and use the 48-hour event for integration, polish and submission.

---

## 📌 1. Project Overview

### Problem Statement
Farmers face shifting temperatures, changing rainfall, water shortages, extreme weather and declining soil health. Picking a crop rotation that protects the field, saves water and holds up over time is hard. Farmers rarely have clear, local information on how their conditions have changed or how different rotations would perform under them.

### Proposed Solution
**Field Shift** is a web tool for farmers and agricultural planners. A user drops a pin on their field. Field Shift then:

1. Pulls **40+ years of NASA climate and soil-moisture data** for that exact point and shows **how conditions have shifted** (season length, frost dates, heat stress, dry spells, rainfall variability, root-zone wetness).
2. Combines that with **local soil data** (texture, water-holding capacity, organic matter, drainage) and a **crop knowledge base** (water need, heat tolerance, nitrogen effect, crop family, timing windows).
3. Lets the farmer **set their own priorities with sliders** (soil health, water conservation, yield stability, simplicity/economics).
4. **Generates and ranks valid 3–5 year rotations**, explains *why* each one scores as it does, and compares it with the farmer's current practice.

### Design Principles
- **Explore, don't dictate:** sliders, side-by-side comparison, and a "swap a crop" option instead of one black-box answer.
- **Honest indicators:** relative, explainable scores with cited coefficients. No made-up precise predictions (e.g., we do **not** claim "SOM will reach 3.6%").
- **"Changing conditions" is the headline:** every recommendation is linked to a measured climate shift at that location.
- **Global by default, richer in the US:** works anywhere with POWER + SoilGrids; adds SSURGO and SMAP/Crop-CASMA detail in the US.

---

## 🎯 2. Core Features

### F1. Farm Location & Profile
- Leaflet map (no API key) with search and pin drop → lat/lon.
- Auto-filled soil profile (SSURGO in US, SoilGrids elsewhere) that the user can edit, plus a **manual soil-type dropdown fallback**.
- "Current practice" input (e.g., continuous corn, corn–soy, wheat–fallow) as the baseline.

### F2. Climate Shift Dashboard (the "changing conditions" story)
Compares **1981–2000 vs. 2005–2024** at the chosen point, using NASA POWER:

| Indicator | Computed from |
| :--- | :--- |
| Growing degree days (GDD) & season length | T2M, T2M_MAX, T2M_MIN |
| Last spring frost / first fall frost | T2M_MIN |
| Growing-season rainfall + variability (CV) | PRECTOTCORR |
| Heat-stress days (> 35 °C) | T2M_MAX |
| Longest dry spell | PRECTOTCORR |
| Reference evapotranspiration (ET₀, FAO-56) | T2M, RH2M, WS2M, ALLSKY_SFC_SW_DWN |
| Root-zone soil wetness trend | GWETROOT, GWETTOP |

Each indicator shows "then vs. now" plus a one-line plain-language interpretation.

### F3. Hazard Context Timeline
- NASA EONET events (drought, floods, severe storms, temperature extremes, wildfires) within a bounding box around the farm, 2015–present.
- **Context only. Not used in scoring** (EONET is meant for reference and visualization, and its point coverage is sparse).

### F4. Priority-Weighted Rotation Recommender
- Sliders: 🟢 Soil Health · 🔵 Water Conservation · 🟡 Yield Stability / Climate Risk · ⚪ Simplicity / Economics.
- Engine generates **all valid rotations** from rules, scores them, and returns the top 3–5 along with the baseline.
- Each result has a "Why this rotation?" explanation tied to climate-shift findings (e.g., "Your frost-free season is 12 days longer than in the 1990s, so winter rye now fits after soybean harvest").

### F5. Rotation Comparison & Outcome View
- Side-by-side: **Current practice vs. Recommended** across a 3–5 year timeline (crop-by-year strip, including cover crops).
- Radar/bar chart of the five indicator scores (see §4).
- Seasonal water-demand chart (crop ET vs. rainfall) per rotation, giving a real "water saved" estimate in mm/season.
- "Swap a crop" interaction: the farmer edits a year and scores update live.

### F6. Methodology Panel ("How we calculate this")
- Every score shows its formula, inputs and cited sources (FAO-56, extension publications, etc.).
- States limitations plainly. This is how we earn the **validity** criterion.

---

## 🛰️ 3. Data Sources & Integration Strategy

### 3.1 Data Stack

| Role | Source | Access | Coverage | Used for |
| :--- | :--- | :--- | :--- | :--- |
| **Main engine** | **NASA POWER** Daily & Climatology API (AG community) | REST, no login, JSON | Global, 1981 → near real time | All climate indicators, ET₀, soil wetness |
| Soil moisture validation | **NASA SMAP** via **Crop-CASMA** (USDA NASS / GMU / NASA) | Web service / pre-computed | CONUS | Soil-moisture anomaly layer + cross-check of POWER GWETROOT |
| Hazard context | **NASA EONET v3** | REST, no login, GeoJSON | Global, event-based | Hazard timeline (F3) |
| Soil (US) | **USDA Soil Data Access (SSURGO)** | REST/SQL | US | Texture, AWC, OM, drainage |
| Soil (global) | **ISRIC SoilGrids** | REST | Global (~250 m) | Clay/sand/silt, SOC, pH |
| Crop traits | Team-built **crop knowledge base** (JSON) | Local file | — | Kc curves, GDD needs, heat tolerance, N effect, family, windows |
| *Stretch* | NASA **GPM IMERG** | Earthdata Login | Global | Rainfall-intensity / extreme-storm check |
| *Stretch* | NASA **NEX-GDDP-CMIP6** | Earthdata / AWS | Global | "2040s outlook" for the chosen point |

**Why this setup:** POWER covers precipitation, temperature, ET inputs *and* soil wetness through one simple, login-free API, so the core product runs anywhere on Earth. SMAP and GPM raw files (HDF5/NetCDF, Earthdata login, gridding) are too costly to make the critical path. We bring SMAP in through Crop-CASMA for the US demo and keep GPM/CMIP6 as stretch goals.

### 3.2 Reference API Calls

**POWER daily point (1981–2024, Ames IA example):**
```
https://power.larc.nasa.gov/api/temporal/daily/point
  ?parameters=T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,WS2M,ALLSKY_SFC_SW_DWN,GWETTOP,GWETROOT
  &community=AG&longitude=-93.62&latitude=42.03
  &start=19810101&end=20241231&format=JSON
```
- Max **20 parameters per request**. Split if needed.
- Also test `/api/temporal/climatology/point` for long-term averages.
- Verify parameter names in the POWER API Pages ("Try it out") before coding.

**EONET hazards (GeoJSON):**
```
https://eonet.gsfc.nasa.gov/api/v3/events/geojson
  ?category=drought,floods,severeStorms,tempExtremes,wildfires
  &status=all&start=2015-01-01&end=<today>
  &bbox=<minLon>,<maxLat>,<maxLon>,<minLat>
```
- `status=all` is required. The default returns only currently open events.
- bbox order = upper-left (lon, lat), then lower-right (lon, lat). Use roughly ±2–3° around the farm.

### 3.3 Reliability Rules
- **Cache every POWER response by rounded coordinate** (POWER warns that repeated requests for the same location can be blocked).
- **Pre-bake JSON snapshots** for all demo locations so the demo runs offline if venue Wi-Fi fails.
- Every external call has a timeout and a fallback (cached data or manual input) with a visible "using cached data" badge.

---

## 🧮 4. Recommendation Engine

### 4.1 Crop Knowledge Base (`data/crops.json`)
Initial set: **Corn, Soybean, Winter Wheat, Sorghum, Alfalfa, Oats, Canola/Sunflower** + cover crops **Cereal Rye, Crimson Clover, Radish**. Region packs add local crops (e.g., millet, chickpea, pigeon pea for the semi-arid demo).

Per crop (every value has a `source` field):
- `family` (grass / legume / brassica / …), `type` (cash / cover / perennial)
- `gdd_required`, `base_temp`, `season_window` (plant / harvest)
- `kc` curve (initial / mid / late, FAO-56), `rooting_depth`
- `heat_sensitive_stage` + threshold, `drought_tolerance` (1–5)
- `n_effect` (fixes / neutral / heavy feeder) and relative magnitude
- `residue_cover` (low / med / high), `soil_preferences` (texture, drainage)

### 4.2 Rotation Generation (rules, not a fixed list)
Enumerate all 2-, 3-, 4- and 5-year sequences from the crop set (2 years covers corn–soybean), then filter with agronomic rules:
- No same crop in consecutive years (exception: perennials like alfalfa, 2–3 yr stands). Different crops from the same family in a row (e.g. oats → corn) are allowed and penalized by the Diversity score instead.
- A fall-planted crop (winter wheat) can't follow a crop harvested after its planting window closes.
- Crop must fit the location's **current** season length / GDD (from F2).
- Cover crop is allowed only if the gap between cash-crop harvest and the next planting (or killing frost) is ≥ N days, computed from POWER frost dates.
- Soil filter: e.g., penalize or exclude crops poorly suited to the soil's drainage/texture.

### 4.3 Indicator Scores (0–100, relative, explainable)

| Indicator | What it measures | Basis |
| :--- | :--- | :--- |
| **Nitrogen Balance** | Net N supplied vs. demanded across the rotation | Legume credits vs. heavy-feeder demand (cited extension values) |
| **Soil Cover** | % of days per year the soil is covered (crop + residue + cover crop) | Season windows + POWER frost dates |
| **Water Demand** | Seasonal crop ET (Kc × ET₀) minus effective rainfall → irrigation gap (mm) | FAO-56 with POWER ET₀ and rainfall; soil AWC as buffer |
| **Climate Risk** | Exposure to heat-stress days in sensitive stages, dry spells, excess rain | POWER daily history (recent 20 yrs weighted), crop thresholds |
| **Diversity / Pest Break** | Number of families, years between repeats | Rotation structure |

**Final score** = Σ (slider weight × indicator score). Weights map to sliders:
- Soil Health → Nitrogen Balance + Soil Cover + Diversity
- Water Conservation → Water Demand
- Yield Stability → Climate Risk
- Simplicity / Economics → penalty for many crops / specialized equipment (simple, stated assumption)

### 4.4 Explanation Generator
For each top rotation, produce 2–4 plain-language reasons by linking the strongest score drivers to the F2 climate-shift findings (template-based, no LLM required).

### 4.5 Validation
- Hand-check against known agronomy: corn–soy–rye should beat continuous corn on N balance and soil cover; a drought-tolerant sequence should beat a corn-heavy one on water in the semi-arid demo.
- Unit tests for every indicator function.
- Cross-check POWER GWETROOT trend against the Crop-CASMA/SMAP anomaly for the Iowa demo (2015–present overlap).

---

## 🗺️ 5. Demo Scenarios
1. **Primary: central Iowa (corn/soy belt).** Baseline continuous corn → corn–soy–cereal rye. Story: longer season enables cover crops; heat-stress days rising.
2. **Contrast: semi-arid / drought-prone region** (e.g., western Kansas wheat–fallow, or a semi-arid site in India or East Africa). Story: water gap drives sorghum/legume rotation. Proves the tool is global.
3. (Optional) **Wet/flood-prone site**, to show excess-rain risk changing the ranking.

---

## 🏗️ 6. Architecture & Stack

```
[Next.js + Leaflet + Recharts]  ──►  [FastAPI backend]
                                       ├── power_client.py   (fetch + cache)
                                       ├── eonet_client.py   (fetch + cache)
                                       ├── soil_client.py    (SSURGO / SoilGrids / fallback)
                                       ├── climate_shift.py  (F2 indicators)
                                       ├── et0.py            (FAO-56 Penman-Monteith)
                                       ├── rotations.py      (generate + filter)
                                       └── scoring.py        (indicators + weights + explanations)
                                     data/crops.json · cache/ · snapshots/
```
- **Frontend:** Next.js (React), Leaflet, Recharts, Tailwind.
- **Backend:** Python FastAPI (pandas/numpy for indicators).
- **Hosting:** Vercel (frontend) + Render/Railway (backend), with a fully local fallback for the live demo.
- **One monorepo**, `main` always deployable, feature branches + PRs.

### API Contract (agree on this in Week 1 so A, B and C can work in parallel)
- `GET /api/climate-shift?lat=&lon=` → indicators then/now + interpretations
- `GET /api/soil?lat=&lon=` → soil profile + source
- `GET /api/hazards?lat=&lon=` → EONET GeoJSON
- `POST /api/recommend` `{lat, lon, soil, baseline, weights, years}` → ranked rotations with scores + explanations
- `POST /api/score` `{rotation, ...}` → scores for a user-edited rotation ("swap a crop")

Mock JSON responses for each endpoint go in `snapshots/` on day 1 so the frontend never waits on the backend.

---

## 👥 7. Team Roles & Responsibilities (3 Members)

### Member A: Domain Lead, UX & Storytelling
- Crop knowledge base (`crops.json`) with a source for every value; rotation rules.
- Methodology panel content and limitations statement.
- Wireframes (4 screens: Location → Soil & Priorities → Ranked Rotations → Compare & Climate Shift).
- Pitch deck, demo script, video. Owns "Does this make sense to a farmer?"

### Member B: Data & Engine Lead
- POWER / EONET / soil clients with caching and fallbacks.
- Climate-shift indicators, FAO-56 ET₀, rotation generator, scoring, explanations.
- Unit tests and validation cases; Crop-CASMA cross-check.

### Member C: Frontend & Visualization Lead
- Next.js app, Leaflet map, input forms, priority sliders.
- Climate-shift dashboard, hazard timeline, rotation strip, radar chart, water-demand chart.
- "Swap a crop" interaction, responsive layout, deployment.

---

## 🚀 8. Roadmap (Oct 20 → Nov 15)

```
[Wk 1] Foundations ➜ [Wk 2] Core Engine + Realign (Oct 28) ➜ [Wk 3] Integration ➜ [Wk 4] Polish & Pitch ➜ [Nov 14–15] Event & Submit
```

### Week 1: Foundations (Oct 20–26)
- [ ] All: register team + choose local/online event; set up monorepo, Vercel/Render, shared board.
- [ ] All: agree on the API contract (§6) and commit mock JSON responses.
- [ ] A: crops.json v1 (core crops + 3 covers) and rotation rules v1; wireframes.
- [ ] B: POWER client + cache working for Iowa; first climate-shift indicators (GDD, frost dates, heat days, rainfall CV).
- [ ] C: app skeleton, Leaflet map with pin → lat/lon, forms and sliders wired to mock data.

### Week 2: Core Engine + Realign (Oct 27–Nov 2)
- [ ] **Oct 28: everyone reads the full challenge statement.** Map each listed dataset/requirement to a feature; adjust scope the same day.
- [ ] B: FAO-56 ET₀, soil client (SSURGO + SoilGrids + fallback), rotation generator, scoring v1, EONET client.
- [ ] A: sourced coefficients for all indicators; validation cases written; region pack for the contrast demo.
- [ ] C: climate-shift dashboard and results list on mock data; start the comparison view.

### Week 3: Integration (Nov 3–9)
- [ ] Swap mocks for live endpoints; end-to-end flow working for Iowa.
- [ ] B: explanation generator; Crop-CASMA/SMAP cross-check; unit tests passing.
- [ ] C: comparison charts, rotation strip, hazard timeline, "swap a crop."
- [ ] A: methodology panel; first full run-through of the demo story; pitch deck draft.
- [ ] Contrast demo region working end to end.

### Week 4: Polish & Pitch (Nov 10–13)
- [ ] Pre-bake snapshots for all demo locations; offline-mode test.
- [ ] Performance pass (cache warm, < 3 s to results).
- [ ] UI polish, mobile check, copy edit for farmer-friendly language.
- [ ] Rehearse the pitch; record a backup demo video.
- [ ] **Nov 13: read the Submission Guide & Judging Guide**; update the deliverables checklist below.

### Event: Nov 14–15 (48 hours)
- **Hours 0–8:** confirm requirements from the guides; fix gaps; stretch goal only if core is solid (GPM check or CMIP6 "2040s outlook").
- **Hours 8–30:** bug fixes, final polish, extra demo region if time allows.
- **Hours 30–40:** record the final demo video; finalize slides and project page text.
- **Hours 40–44:** submit **early**; verify all links (repo, live demo, video) work from a fresh browser.
- **Hours 44–48:** buffer only.

---

## 📦 9. Deliverables Checklist (update on Nov 13)
- [ ] Live demo URL + public GitHub repo with README (setup, data sources, methodology, limitations).
- [ ] Demo video (length per the 2026 Submission Guide).
- [ ] Pitch deck (~7 slides): Problem → Climate-shift insight → Solution demo → NASA data used → How scoring works → Impact & scale → Team / next steps.
- [ ] Project page on the Space Apps platform listing every NASA dataset used.

---

## ⚖️ 10. Judging Alignment
*(Confirm criteria in the 2026 Judging Guide. Historically: Impact, Creativity, Validity, Relevance, Presentation.)*

| Criterion | How Field Shift addresses it |
| :--- | :--- |
| **Impact** | Works for any farm on Earth; turns 40 years of NASA data into a field-level decision |
| **Creativity** | Climate-shift–driven rotation generation + live priority sliders + "swap a crop" |
| **Validity** | Cited coefficients, FAO-56 water method, SMAP cross-check, explicit limitations |
| **Relevance** | Covers every input named in the challenge: NASA EO, soil, crop traits, farmer priorities |
| **Presentation** | Clear "then vs. now → therefore this rotation" story; offline-safe demo |

---

## ⚠️ 11. Risks & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| POWER/soil API slow or down | Cache + pre-baked snapshots + manual soil fallback |
| Scope creep | Stretch goals (GPM, CMIP6, extra regions) only after core is done |
| Unsupported agronomic numbers | Every value in crops.json has a source; scores shown as relative, not absolute |
| Oct 28 statement changes requirements | Same-day realignment meeting; modular engine makes features easy to add or remove |
| Venue Wi-Fi fails during demo | Local backend + snapshots; backup video |
| Teammate unavailable | API contract + mocks mean any member can pick up another's area |

---

## ✅ 12. Definition of Done (core)
A user can pin any location → see the climate shift with plain-language takeaways → see an auto-filled (or manual) soil profile → set priorities → get ranked rotations with reasons → compare them with their current practice → edit a crop and see scores update. All of this works offline for demo locations, and every number traces back to NASA data or a cited source.

---

## 🧭 13. Step-by-Step Build Order

> Build in the order the data flows: each step uses the output of the one before it.
> **Rule:** finish and fully understand one step before moving on.

### How we work through each step
1. **Learn:** understand the concept (what the data or formula means and why it matters to farmers).
2. **Build:** write the code in small pieces and run it in VS Code.
3. **Check:** inspect the output and explain what it means. Only then move to the next step.

### Stage 0: Setup (~1 hour)
- [ ] **Step 0: Project setup.** Create `field-shift/` with `backend/`, `frontend/`, `data/`, `cache/`, `snapshots/`; init Git; create a Python virtual env; install Node.
  - ✅ *Done when:* `git status` works and both Python and Node run.

### Stage 1: Get & Understand the Data (Backend)
- [ ] **Step 1: POWER fetch + cache** (§3.2, §3.3). Call the API for one Iowa point, save the response, and explore it.
  - ✅ *Done when:* 40+ years of daily data load into a table, and a second request reads from the cache instead of the internet.
- [ ] **Step 2: Climate shift indicators** (§2 F2). GDD, frost dates, heat-stress days, dry spells, rainfall variability: 1981–2000 vs. 2005–2024.
  - ✅ *Done when:* a "then vs. now" table prints for Iowa and every number makes sense.
- [ ] **Step 3: Evapotranspiration, ET₀ (FAO-56)** (§4.3). The most math-heavy step, so take it slow.
  - ✅ *Done when:* daily ET₀ for Iowa falls in a believable range (higher in summer, near zero in winter).
- [ ] **Step 4: Soil data** (§3.1). SSURGO (US) + SoilGrids (global) + manual fallback.
  - ✅ *Done when:* any point returns texture, water-holding capacity and organic matter.
- [ ] **Step 5: EONET hazards** (§2 F3). Small and easy; a breather after ET₀.
  - ✅ *Done when:* hazard events within a bounding box around the farm return as GeoJSON.

### Stage 2: Decision Logic
- [ ] **Step 6: Crop knowledge base** (§4.1). Write `crops.json` with a source for every value. Research, not code (Member A can do this alongside Stage 1).
  - ✅ *Done when:* all core crops + cover crops have every field filled in, each with a source.
- [ ] **Step 7: Rotation generator** (§4.2). List all crop sequences, then filter with the agronomy rules.
  - ✅ *Done when:* you can explain why each rejected rotation was rejected.
- [ ] **Step 8: Scoring + explanations** (§4.3, §4.4). Five indicator scores, priority weights, plain-language reasons.
  - ✅ *Done when:* hand-checked validation cases pass (e.g., corn–soy–rye beats continuous corn on soil health).

### Stage 3: API
- [ ] **Step 9: FastAPI endpoints** (§6). Wrap Steps 1–8 in the five endpoints.
  - ✅ *Done when:* each endpoint returns JSON when called from the browser.

### Stage 4: Frontend
- [ ] **Step 10: App skeleton + map + pin drop.**
  - ✅ *Done when:* clicking the map gives a lat/lon.
- [ ] **Step 11: Inputs:** soil profile, current practice, priority sliders.
  - ✅ *Done when:* form values are sent to `/api/recommend`.
- [ ] **Step 12: Climate Shift dashboard.**
  - ✅ *Done when:* "then vs. now" indicators show with plain-language takeaways.
- [ ] **Step 13: Ranked rotations + comparison charts + "swap a crop."**
  - ✅ *Done when:* editing a crop updates the scores live.
- [ ] **Step 14: Methodology panel.**
  - ✅ *Done when:* every score shows its formula, inputs and sources.

### Stage 5: Finish
- [ ] **Step 15: Demo readiness.** Snapshots + offline test, second demo region, pitch deck and video.
  - ✅ *Done when:* the full demo runs with Wi-Fi off, and the video and slides are final.

### Working in parallel with the team
| Steps | Owner | Can start |
| :--- | :--- | :--- |
| 0–5, 7–9 | Member B (data & engine) | Now |
| 6, 14 content, pitch | Member A (domain & story) | Now, alongside Stage 1 |
| 10–13 | Member C (frontend) | Now, using mock JSON from `snapshots/` |
