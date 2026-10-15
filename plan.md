# 🌾 Field Shift: NASA Data-Driven Crop Rotation Decision Support System

> **Space Apps Challenge 2026 Strategy & Implementation Roadmap**

---

## 📌 1. Project Overview

### Problem Statement
Farmers worldwide face shifting temperatures, unpredictable rainfall patterns, water shortages, and severe soil degradation. Choosing optimal crop rotation strategies that simultaneously conserve water, restore soil nutrients, and protect yield is increasingly complex without actionable environmental insights.

### Proposed Solution
**Field Shift** is a web-based decision-support platform designed for farmers and agricultural planners. By combining **NASA Earth observations** (meteorological history, soil moisture trends, precipitation patterns) with local soil characteristics and farmer priorities (e.g., water conservation vs. soil restoration vs. yield stability), Field Shift evaluates crop rotation strategies and simulates 3-to-5-year soil health and climate-resilience outcomes.

---

## 🎯 2. Core Features

1. **Interactive Farm Location Selector**
   * Map-based interface (Mapbox / Leaflet) allowing farmers to pinpoint their exact fields via latitude/longitude.

2. **NASA Environmental Risk Assessment**
   * Pulls multi-year historical climate and soil moisture data (NASA POWER, SMAP, GPM) to compute a localized **Drought & Soil Health Index**.

3. **Multi-Objective Rotation Recommender**
   * Suggests optimized crop rotation sequences based on farmer goals:
     * 🟢 *Soil Regeneration*: Legume-heavy rotations (e.g., Corn ➡️ Soybeans ➡️ Rye cover crop) for nitrogen fixation.
     * 🔵 *Water Conservation*: Drought-tolerant options to reduce irrigation demand.
     * 🟡 *Economic / Yield Stability*: Balanced rotations minimizing risk during extreme weather events.

4. **Visual Outcome Simulator**
   * Side-by-side comparison charts evaluating "Business as Usual (Monoculture)" vs. "Recommended Rotation Strategy" across a 3–5 year trajectory (Soil Organic Matter %, Water Savings, Risk Reduction Score).

---

## 🛰️ 3. NASA Data & API Integration Strategy

| NASA Data Source / API | Parameters / Indicators | Application in Field Shift |
| :--- | :--- | :--- |
| **NASA POWER API** | Daily Temperature, Precipitation, Solar Radiation | Historical baseline & weather risk index calculation |
| **NASA SMAP** *(via Earthdata / GEE)* | Soil Moisture Active Passive | Current soil moisture levels & drought vulnerability assessment |
| **NASA GPM** | Precipitation Measurement | Rainfall variability & extreme storm hazard frequency |
| **NASA EONET API** | Natural Event Tracker | Real-time / historical climate hazard alerts (droughts, floods) |

---

## 👥 4. Team Roles & Responsibilities (3 Members)

### **Member A: Domain Strategy, UI/UX & Pitch Deck**
* **Responsibilities**:
  * Agricultural domain research (crop properties, crop rotation logic, nutrient dynamics).
  * Designing user workflows and UI/UX wireframes (Figma / layout specs).
  * Authoring project documentation, presentation pitch deck, and video demo script.

### **Member B: Data Engineering & Backend / Recommendation Logic**
* **Responsibilities**:
  * Fetching and processing data from NASA POWER API & EONET API.
  * Building backend services (Python FastAPI / Node.js) to compute climate risk scores and soil health metrics.
  * Implementing the decision algorithm for crop rotation scoring.

### **Member C: Frontend Development & Data Visualization**
* **Responsibilities**:
  * Developing the web application UI (React / Next.js / HTML5).
  * Integrating interactive map views (Mapbox GL JS or Leaflet.js).
  * Implementing visual comparison graphs (Chart.js / Recharts) for rotation simulations.

---

## 🚀 5. Actionable Implementation Roadmap

```
[Phase 1] Requirements & API Validation  ➜  [Phase 2] Core Dev & Algorithm  ➜  [Phase 3] Integration & UI Polish  ➜  [Phase 4] Pitch & Submission
```

### Phase 1: Setup & API Validation (Days 1–2)
- [ ] Member A: Finalize crop database schema (e.g., Corn, Soybean, Wheat, Rye, Alfalfa) and rotation rules.
- [ ] Member B: Test NASA POWER API endpoint retrieval for sample field coordinates.
- [ ] Member C: Set up frontend repository with map integration skeleton.

### Phase 2: Core Development (Days 3–4)
- [ ] Member A: Draft Figma/wireframe mockups and prepare slide deck outline.
- [ ] Member B: Build recommendation engine script linking climate risk metrics with crop scoring.
- [ ] Member C: Build input form UI (location, goal selectors, soil type) and result presentation views.

### Phase 3: System Integration & Visualization (Days 5–6)
- [ ] Connect frontend form submission with backend API responses.
- [ ] Render NASA weather trend line charts and rotation simulation comparisons.
- [ ] Perform end-to-end testing using real-world agricultural test cases (e.g., Iowa, US or drought-prone region).

### Phase 4: Pitch Deck & Hackathon Submission (Day 7)
- [ ] Produce 7-slide Pitch Deck (Problem, Solution, NASA Data Integration, Demo, Impact).
- [ ] Record a 1-2 minute project demonstration video.
- [ ] Submit project page on the official Space Apps Challenge platform.