"use client";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

const MapContainer = dynamic(() => import("react-leaflet").then(m => m.MapContainer), { ssr: false });
const TileLayer = dynamic(() => import("react-leaflet").then(m => m.TileLayer), { ssr: false });
const Circle = dynamic(() => import("react-leaflet").then(m => m.Circle), { ssr: false });
// Removed Marker and Tooltip to avoid stray default markers
const Popup = dynamic(() => import("react-leaflet").then(m => m.Popup), { ssr: false });

type Zone = { center_lat: number; center_lon: number; zone_name?: string; population?: number; radius_km?: number };

export function MapView({ zones, center }: { zones: Zone[]; center?: { lat: number; lon: number } }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const ctr = useMemo(() => ({ lat: center?.lat ?? 37.7749, lon: center?.lon ?? -122.4194 }), [center]);
  if (!mounted) return null;
  return (
    <div className="rounded overflow-hidden border border-white/10">
      <MapContainer center={[ctr.lat, ctr.lon]} zoom={11} style={{ height: 360, width: "100%" }}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {zones.map((z, i) => (
          <Circle
            key={i}
            center={[z.center_lat, z.center_lon]}
            radius={Math.max(100, Math.min(1000, (z.population || 0) / 2))}
            pathOptions={{ color: "#10b981", fillOpacity: 0.2 }}
          >
            <Popup>
              <div className="text-sm">
                <div className="font-semibold">{z.zone_name || `Zone ${i + 1}`}</div>
                <div>Population: {z.population ?? 0}</div>
              </div>
            </Popup>
          </Circle>
        ))}
      </MapContainer>
    </div>
  );
}


