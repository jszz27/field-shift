# Field Shift: demo video script and shot list

Target length **about 2:00**. This is an assumption: check the length the 2026 Submission Guide asks for
(published Nov 13) and cut or stretch the "Swap a crop" and "Niamey" beats to fit.

## Before recording

1. From the repo root, run `.\run_demo.ps1` (offline mode, demo fields only). After any code change, run
   `.\run_demo.ps1 -Rebuild`.
2. Browser at 1920×1080, zoom 100%, no other tabs or bookmarks bar. The website opens at http://localhost:3000.
3. With Wi-Fi on, the map shows street tiles. With Wi-Fi off it shows country outlines and an
   "Offline: simplified map" note. Either is fine; pick one and keep it for every take.
4. Leave the sliders at 50 and the soil on "Use the detected soil".

All numbers below are what the app shows for the demo fields. If a number on screen differs, say the
on-screen number.

## Script

| Time | On screen (shot) | Narration |
| :--- | :--- | :--- |
| 0:00–0:12 | Title slide of the deck, then the app's empty world map. | "Farmers plan crop rotations on yesterday’s climate. Field Shift shows how the climate at your own field has changed, and which rotation fits it now." |
| 0:12–0:20 | Click **Ames, Iowa, USA** under "Or try a demo field". The pin drops and the Climate shift tab opens. | "Let’s pick a corn field near Ames, Iowa. Field Shift pulls 44 years of NASA POWER weather for this exact point." |
| 0:20–0:40 | Hover the **First fall frost** card (Oct 10 → Oct 19), then **Frost-free season** (168 → 179), then **Water demand (ET0)** (886 → 932 mm). | "Compared with 1981 to 2000, the first fall frost now comes nine days later, and the frost-free season is eleven days longer. But the air demands 46 more millimetres of water a year, and growing-season rain is down." |
| 0:40–0:50 | Point at the right panel: the soil line (Loam, Clarion, SSURGO) and "Year 1: Maize". | "Soil comes from the USDA soil survey. This farmer grows maize every year. We leave the four priority sliders even." |
| 0:50–1:15 | Click **Get recommendations**. Show the #1 card: alfalfa ×3 → maize, 69.9, the "+ cereal rye cover" tag, and its reasons. | "Field Shift generated 113 rotations that follow basic farming rules and ranked them. The top one, alfalfa then maize, scores 69.9 against 46.1 today. It needs 28 kilograms of nitrogen fertilizer instead of 203, keeps soil covered 94% of the year, and cereal rye now fits after alfalfa because frost comes nine days later." |
| 1:15–1:30 | Scroll to **Compare with current practice**. In **Swap a crop**, change year 4 from Maize to **Soybean**. Show "Your edit: 66.6 · rank 3 of 12". | "Farmers stay in control. Swap any crop and it re-scores instantly: soybean instead of maize ranks third." |
| 1:30–1:40 | Open **How each score is computed** → **Water demand**. Show the formula and the source tags. | "Every score shows its formula, its inputs and a cited source. If a value has no source, we skip it instead of guessing." |
| 1:40–1:55 | Click **Niamey area, Niger**. Show **Rainy season length** (76 → 86 days) and **Longest dry spell** (4.3 → 6.6). Click **Get recommendations**; show #1 cowpea → pearl millet. | "It works anywhere. Near Niamey there is no frost, so Field Shift tracks the rainy season instead: ten days longer, but with longer dry breaks. It suggests adding cowpea, a legume, to pearl millet." |
| 1:55–2:00 | Last slide of the deck (team and next steps). | "Field Shift: crop rotations for the climate your field has now, from NASA data." |

## Shot list (in recording order)

1. Deck title slide, 3 s.
2. App, empty map, 2 s.
3. Click "Ames, Iowa, USA"; hold on the Climate shift cards about 20 s (slow cursor over the three cards).
4. Right panel close-up: soil and "What you grow now", 5 s.
5. Click "Get recommendations"; hold on the #1 card, 20 s.
6. Scroll to "Swap a crop"; change year 4 to Soybean; hold on the rank line, 10 s.
7. Expand "Water demand" in "How each score is computed", 10 s.
8. Click "Niamey area, Niger"; rainy-season cards, 5 s; "Get recommendations"; #1 card, 10 s.
9. Deck closing slide, 5 s.

## Backup plan

- If the live demo fails on stage, play this video.
- If only the internet fails, keep going: the demo fields run from saved snapshots.
- Clicking anywhere other than a demo field offline shows "Offline demo mode: … Pick a demo field." Say
  "online, this works for any point on Earth" and click a demo field.
