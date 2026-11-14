# Field Shift: 30-second demo video

**Hard limit: 30 seconds or less.** A longer video makes the project ineligible for Global Judging.
Aim for **28 seconds** to leave a margin. The beats follow the Space Apps submission guide (0:00 /
0:02 / 0:05 / 0:10 / 0:20–0:30). The narration is about 65 words (around 26 seconds at a normal pace);
read it aloud with a timer and cut words if it runs over 27 seconds.

Rules from the guide: the video must be in English, or have English subtitles if spoken in another
language. No images, video or voices of anyone under 18. No NASA logos or branding. Host it on YouTube
or Google Drive with a public link (no sign-in) and test the link in a private window.

## Script

| Time | On screen | Narration |
|---|---|---|
| 0:00–0:02 | Deck cover slide (team name visible) | "Hi, we're [Team name]." |
| 0:02–0:05 | Deck problem slide | "Our challenge: [challenge title]. Farmers plan crops on yesterday's climate." |
| 0:05–0:10 | App, empty world map, title bar "Field Shift" | "Field Shift gives them crop rotations for the climate their field has *now*." |
| 0:10–0:20 | Click **Ames, Iowa, USA** → climate cards; hover **First fall frost: Oct 10 → Oct 19**. Cut to the results: #1 card, **71.6 vs 22.9**. | "Drop a pin: 44 years of NASA weather show your field's shift. Here, frost comes nine days later. Rank what matters; get rotations with reasons." |
| 0:20–0:30 | Quick cut: Niamey climate cards, then the deck's last slide with the link | "Any field on Earth, every number cited, for farms ready for the climate ahead." |

## Shot list (record in this order, then trim)

1. Deck cover slide, 2 s.
2. Deck problem slide, 3 s.
3. App: empty map, 5 s (the page already loaded).
4. Click "Ames, Iowa, USA"; climate cards appear; move the cursor to the "First fall frost" card, 5 s.
5. Results tab, already loaded: the #1 card with 71.6 and the line "continuous maize, scores 22.9", 5 s.
6. Click "Niamey area, Niger": rainy-season cards, 3 s.
7. Deck last slide ("Any field on Earth…", live link), 7 s.

## Recording tips

- **Prepare everything first, then record.** Real loading takes several seconds, which a 30-second video
  can't afford. Open the app, click Ames, run "Get recommendations" once, then record shots 4–5 and cut
  out any waiting.
- Use the default priority ranking (Soil health 1st), so the numbers match the deck (22.9 → 71.6).
- Full-screen browser at 1920×1080, zoom 100%, no other tabs or bookmarks bar.
- Running offline (`.\run_demo.ps1`) makes Ames and Niamey load instantly; the live site works too.
- Speak a little faster than normal, and record the narration separately if that's easier, then lay it
  over the clips.

## Backup plan

- If the live demo fails on stage, play this video.
- If only the internet fails, keep going with `.\run_demo.ps1`: the demo fields run from saved
  snapshots.
