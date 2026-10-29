"use client";

import "leaflet/dist/leaflet.css";
import type { FeatureCollection } from "geojson";
import { useEffect, useState } from "react";
import { CircleMarker, GeoJSON, MapContainer, Pane, TileLayer, useMap, useMapEvents } from "react-leaflet";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import countries110m from "world-atlas/countries-110m.json";
import type { Point } from "@/lib/api";

type Props = {
  point: Point | null;
  onPick: (point: Point) => void;
};

// Natural Earth country outlines bundled with the app, drawn under the tiles: if the
// OpenStreetMap tiles cannot load (no internet at the venue), the map still shows land
const topology = countries110m as unknown as Topology<{ countries: GeometryCollection }>;

// Russia, Fiji and Antarctica cross the 180° meridian; Leaflet would draw those edges across
// the whole map. Shift each point by 360° so a ring never jumps more than 180° in longitude.
function unwrap(ring: number[][]) {
  let offset = 0;
  return ring.map(([lon, lat], i) => {
    if (i > 0) {
      const jump = lon - ring[i - 1][0];
      if (jump > 180) offset -= 360;
      else if (jump < -180) offset += 360;
    }
    return [lon + offset, lat];
  });
}

const COUNTRIES = feature(topology, topology.objects.countries) as FeatureCollection;
for (const f of COUNTRIES.features) {
  const g = f.geometry;
  if (g.type === "Polygon") g.coordinates = g.coordinates.map(unwrap);
  if (g.type === "MultiPolygon") g.coordinates = g.coordinates.map((poly) => poly.map(unwrap));
}
const OUTLINE_STYLE = { color: "#9ca3af", weight: 1, fillColor: "#f2efe9", fillOpacity: 1 };

// Two decimals (~1 km) matches how the backend caches NASA POWER requests
const round = (value: number) => Math.round(value * 100) / 100;

function ClickToPick({ onPick }: { onPick: Props["onPick"] }) {
  useMapEvents({
    click: (e) => onPick({ lat: round(e.latlng.lat), lon: round(e.latlng.wrap().lng) }),
  });
  return null;
}

// Leaflet only measures its container on load; redraw when the layout resizes it
function FollowResize() {
  const map = useMap();
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  return null;
}

// Move the view to a point picked outside the map (the demo-field buttons)
function FollowPoint({ point }: { point: Point | null }) {
  const map = useMap();
  useEffect(() => {
    if (point && !map.getBounds().contains([point.lat, point.lon])) map.setView([point.lat, point.lon], 6);
  }, [map, point]);
  return null;
}

export default function MapPicker({ point, onPick }: Props) {
  const [tilesFailed, setTilesFailed] = useState(false);
  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={[20, 0]} zoom={2} minZoom={2} worldCopyJump className="h-full w-full"
        style={{ background: "#aad3df" }}
      >
        {/* Below the tile pane (z-index 200), so loaded tiles cover the outlines */}
        <Pane name="outlines" style={{ zIndex: 150 }}>
          <GeoJSON data={COUNTRIES} style={OUTLINE_STYLE} interactive={false} />
        </Pane>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          eventHandlers={{ tileerror: () => setTilesFailed(true), tileload: () => setTilesFailed(false) }}
        />
        <ClickToPick onPick={onPick} />
        <FollowResize />
        <FollowPoint point={point} />
        {point && (
          <CircleMarker
            center={[point.lat, point.lon]}
            radius={9}
            pathOptions={{ color: "#166534", fillColor: "#22c55e", fillOpacity: 0.9, weight: 2 }}
          />
        )}
      </MapContainer>
      {tilesFailed && (
        <p className="pointer-events-none absolute bottom-6 left-2 z-[1000] rounded bg-amber-100 px-2 py-1 text-xs font-medium text-amber-900">
          Offline: simplified map (country outlines)
        </p>
      )}
    </div>
  );
}
