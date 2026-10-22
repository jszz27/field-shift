"use client";

import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, TileLayer, useMapEvents } from "react-leaflet";
import type { Point } from "@/lib/api";

type Props = {
  point: Point | null;
  onPick: (point: Point) => void;
};

// Two decimals (~1 km) matches how the backend caches NASA POWER requests
const round = (value: number) => Math.round(value * 100) / 100;

function ClickToPick({ onPick }: { onPick: Props["onPick"] }) {
  useMapEvents({
    click: (e) => onPick({ lat: round(e.latlng.lat), lon: round(e.latlng.wrap().lng) }),
  });
  return null;
}

export default function MapPicker({ point, onPick }: Props) {
  return (
    <MapContainer center={[20, 0]} zoom={2} minZoom={2} worldCopyJump className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClickToPick onPick={onPick} />
      {point && (
        <CircleMarker
          center={[point.lat, point.lon]}
          radius={9}
          pathOptions={{ color: "#166534", fillColor: "#22c55e", fillOpacity: 0.9, weight: 2 }}
        />
      )}
    </MapContainer>
  );
}
