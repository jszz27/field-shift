# Space Apps 2026: project submission fields (draft)

Paste each section into the matching field on the team's **Project** tab (My Team → Project → Edit).
Replace every [bracket] first. All text must be in English. Deadline: **Sunday Nov 15, 11:59 p.m.,
Local Event time**. Use "Save Progress" often; resubmitting is allowed until the deadline.

---

## Project Name
Field Shift

## High-Level Project Summary
Field Shift is a free web tool that helps farmers choose crop rotations for the climate their field has
now, not the one it had 30 years ago. A farmer drops a pin on their field. Field Shift pulls 44 years of
daily NASA POWER weather for that exact point and shows, in plain words, how the season has shifted
since 1981–2000: frost dates, heat, rainfall, dry spells and water demand. It combines this with the
field's soil and a crop knowledge base in which every value is cited. It then generates every rotation
that follows basic farming rules, scores each one against the farmer's current practice on nitrogen,
soil cover, diversity, water demand, climate risk and simplicity, and ranks them by the priorities the
farmer chose. Each recommendation explains why, tied to a measured change: for a field near Ames, Iowa,
the first fall frost now comes 9 days later, which leaves room for a cereal rye cover crop after
harvest. This addresses the challenge directly. Farmers face shifting seasons, tighter water and
declining soil health, but rarely get field-level evidence of how their conditions changed or how a
different rotation would perform.

## Link to Project Demo
[Public Google Drive link to the 7-slide PDF: Share → "Anyone with the link" → Viewer. Test it in a
private browser window.]

## Link to Final Project
https://field-shift-pi.vercel.app (live app) · Code: https://github.com/jszz27/field-shift

## Detailed Project Description
**What it does.** Field Shift turns NASA Earth-observation data into a field-level crop rotation
decision. For any point on Earth it:
1. Compares 1981–2000 with 2005–2024 at that exact point: growing degree days, days above 35 °C,
   growing-season rain and its year-to-year variability, the longest dry spell, reference
   evapotranspiration (ET0), root-zone soil wetness, and frost dates. Where there is no regular frost,
   it measures the start, end and length of the rainy season instead. Each change comes with a
   one-line meaning for a farmer.
2. Detects the soil: USDA SSURGO in the US (texture, water-holding capacity, organic matter, drainage)
   or ISRIC SoilGrids elsewhere. The farmer can override it with a soil texture.
3. Asks what the farmer grows now, and has them **rank** four priorities (soil health, water
   conservation, yield stability, simplicity) instead of typing numbers. Any priority can be marked
   "doesn't matter".
4. Generates every 2–5 year rotation from a regional crop pack and filters it with farming rules: no
   annual crop two years in a row, alfalfa stands of 2–3 years, winter wheat only after an early enough
   harvest, and no alfalfa on poorly drained soil. Where the harvest leaves enough days before the
   site's current first fall frost, it adds a cover crop.
5. Simulates each crop through 20 seasons of real daily weather with an FAO-56 root-zone water
   balance. Scores come from the irrigation gap, FAO-33 water-limited yield loss, mid-season heat days,
   fertilizer nitrogen after legume credits, the share of the year the soil is covered, crop and family
   diversity, and simplicity.
6. Ranks the rotations against the farmer's current practice and explains each one in plain language.
   The farmer can swap any crop and re-score it instantly. A methodology panel shows every formula,
   input and source.

**How it works.** A Python FastAPI backend calls the NASA POWER and EONET APIs, USDA Soil Data Access
and SoilGrids. It caches every response and computes FAO-56 Penman-Monteith ET0 from POWER weather. The
crop knowledge base (`data/crops.json`) gives a source for every non-empty value. If a value has no
source, it stays empty and the measure that needs it is skipped, never guessed. The Next.js frontend
uses Leaflet for the map and Recharts for charts. Priority ranks become weights with the rank-order
centroid method (Barron & Barrett 1996). Two demo fields (Ames, Iowa and Niamey, Niger) are saved as
snapshots, so the demo also runs offline.

**Example.** Near Ames, the frost-free season grew from 168 to 179 days, but the air now demands 46 mm
more water a year and growing-season rain fell 41 mm. Against continuous corn (score 22.9 with soil
health ranked first), the top rotation is three years of alfalfa followed by corn, with cereal rye
(71.6). It cuts fertilizer nitrogen from 203 to 28 kg/ha a year and raises soil cover from 73 % to 94 %
of the year. When the farmer ranks simplicity first, plain corn–soybean becomes the top pick. Near
Niamey, Niger, the tool tracks the rainy season instead (10 days longer, but with longer dry breaks)
and suggests adding legumes to pearl millet.

**Benefits.** Field-level, explainable evidence instead of a black box. Every recommendation is tied to
a measured local shift. It works anywhere POWER and SoilGrids have data, and runs in a browser with no
account or install.

**What we hope to achieve.** A starting point for conversations between farmers and agronomists about
adapting rotations to a changing climate, which can grow as more cited crop data is added.

**Limitations.** Scores are relative to the rotations compared, not yield predictions. Crop data is
richest for the US Midwest; some tropical crop values are still missing, and those measures are then
skipped. Regions with two rainy seasons a year are not handled well yet. Irrigated farming is not
modelled.

**Tools.** Python 3.12, FastAPI, pandas, NumPy, pytest (73 tests); TypeScript, Next.js, React, Tailwind
CSS, Leaflet, Recharts; hosted on Vercel (website) and Render (API).

## Use of Super Intelligence (SI)
Yes. We used Anthropic's Claude (through Claude Code) as a coding and writing assistant, under the
team's direction. The idea, the choice of challenge and every design and agronomic decision were ours.

**How we used it efficiently:**
- **Plan first, then build in small checked steps.** Before any code, we wrote our own project plan:
  the problem, design principles, data sources, the API contract and a 15-step build order, each step
  with a "done when" check. Claude worked one step at a time against that plan. We reviewed each step
  before it was committed, so nothing was generated blindly.
- **AI proposes, the team decides.** For every judgment call, Claude laid out the options with
  trade-offs and we chose. Examples: how to define climate zones, how to detect the rainy season,
  excluding alfalfa on poorly drained soil, and turning priority rankings into weights.
- **A strict "never invent a number" rule.** Claude helped find and check published sources for crop
  values. Any value it could not cite stayed empty, and the tool skips that measure instead of
  guessing. The result is 177 cited values from 19 sources (FAO, USDA and university extension guides).
- **Verified, not trusted.** Every feature came with automated tests (73 in total). Claude also ran the
  app in a real browser to test it the way a farmer would, and probed 16 locations worldwide to find
  where it failed, which led us to fix coverage for the Southern Hemisphere, frost-free regions and
  deserts.
- **Result.** Over four weeks of part-time work (Oct 15 – Nov 13, 26 commits), the team built about
  3,700 lines of tested code (Python backend, tests and a Next.js frontend), now deployed online.
  [Only if it's true by submission time: "A working farmer has tried it on their own field."] That let
  us spend our own time on the questions that matter: does this make sense to a farmer, and is every
  number honest?

**Where SI was used:** code, tests, debugging, source research and checking, and drafting text (slides,
this description, the README). **Not used for:** the idea, the challenge choice, design decisions, or
images. No SI-generated images, audio or video appear; the slides show screenshots of our own app. As
the guide requires, the repository's README acknowledges the AI-assisted code. (This answer is not
shown to judges.)

## NASA Data
- **NASA POWER (Prediction Of Worldwide Energy Resources)**, Daily API, AG community, point data for
  1981-01-01 to 2024-12-31: T2M, T2M_MAX, T2M_MIN (air temperature), PRECTOTCORR (precipitation), RH2M
  (humidity), WS2M (wind speed), ALLSKY_SFC_SW_DWN (solar radiation), GWETTOP and GWETROOT (surface and
  root-zone soil wetness). Used for every climate-shift indicator, for FAO-56 reference
  evapotranspiration, and for the daily crop water balance. https://power.larc.nasa.gov/
- **NASA EONET (Earth Observatory Natural Event Tracker)** v3: drought, flood, severe storm,
  temperature-extreme and wildfire events from 2015 on, within ±3° of the field. Used as context only
  and not scored, because coverage is sparse. https://eonet.gsfc.nasa.gov/

## Space Agency Partner Data and Other References
We did not use Space Agency Partner data.

Other data and references:
- USDA NRCS SSURGO soil survey (Soil Data Access): https://sdmdataaccess.sc.egov.usda.gov/
- ISRIC SoilGrids 2.0: https://soilgrids.org/
- FAO Irrigation and Drainage Paper 56 (Allen et al. 1998): ET0 equations, Tables 11, 12, 19 and 22
- FAO Irrigation and Drainage Paper 33 / FAO 66: crop yield response to water (Ky)
- FAO (1978) growing-period method; Sivakumar (1988) false-start rule (rainy-season onset)
- Sacks, Deryng, Foley & Ramankutty (2010), *Crop planting dates*, Global Ecology and Biogeography
  19:607–620 (Southern Hemisphere crop calendars)
- USDA NASS Agricultural Handbook 628, Usual Planting and Harvesting Dates (2010)
- Iowa State University (Sawyer 2008) and K-State MF2586: nitrogen rates and credits
- University of Minnesota Extension: alfalfa establishment
- USDA NRCS residue management guides; SARE *Cover Crops* (Myers), Ch. 6
- USDA Technical Bulletin 1935 (2013): crop temperature thresholds
- Barron & Barrett (1996): rank-order centroid weights
- Map: OpenStreetMap contributors (tiles), Natural Earth via world-atlas (offline outlines), Leaflet
- Software: FastAPI, pandas, NumPy, Next.js, React, Tailwind CSS, Recharts, topojson-client
- Hosting: Vercel, Render

Full source list with links: in the app, open "How each score is computed" → Sources.

---

## Before you click "Submit for Judging"
- [ ] Every [bracket] above is replaced (demo link, team name, challenge, member names in the slides).
- [ ] The demo link opens in a private window without signing in. The deck has 7 slides.
- [ ] The final-project link works. Open it once shortly before submitting, because the free server
      sleeps.
- [ ] All team members are confirmed at the same Local Event.
- [ ] Tick "Terms and Conditions" and "Confirm All Work is Original", then **Submit for Judging**, and
      check for the confirmation banner.
