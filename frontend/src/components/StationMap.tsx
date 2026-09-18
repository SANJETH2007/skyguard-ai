import type { Station } from '../types';
import './StationMap.css';

function trustColor(score: number) {
  if (score >= 80) return '#35d493';
  if (score >= 60) return '#f0b429';
  return '#ff5470';
}

// Project lat/lon onto the SVG viewport based on the network's own bounding box,
// so the map always frames the simulated stations regardless of region.
function makeProjector(stations: Station[]) {
  const pad = 0.4;
  const lats = stations.map((s) => s.latitude);
  const lons = stations.map((s) => s.longitude);
  const minLat = Math.min(...lats) - pad;
  const maxLat = Math.max(...lats) + pad;
  const minLon = Math.min(...lons) - pad;
  const maxLon = Math.max(...lons) + pad;
  return (lat: number, lon: number) => {
    const x = ((lon - minLon) / (maxLon - minLon || 1)) * 640 + 20;
    const y = (1 - (lat - minLat) / (maxLat - minLat || 1)) * 380 + 20;
    return [x, y] as const;
  };
}

export default function StationMap({
  stations,
  selectedId,
  onSelect,
}: {
  stations: Station[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  if (stations.length === 0) {
    return <div className="map-empty">Loading station network…</div>;
  }
  const project = makeProjector(stations);

  return (
    <svg viewBox="0 0 680 420" className="station-map" role="img" aria-label="Live map of AWS station network">
      <defs>
        <pattern id="grid" width="34" height="34" patternUnits="userSpaceOnUse">
          <path d="M 34 0 L 0 0 0 34" fill="none" stroke="#152029" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="680" height="420" fill="url(#grid)" />

      {stations.map((s) => {
        const [x, y] = project(s.latitude, s.longitude);
        const color = trustColor(s.trust_score);
        const selected = s.station_id === selectedId;
        return (
          <g
            key={s.station_id}
            transform={`translate(${x}, ${y})`}
            className="station-marker"
            onClick={() => onSelect(s.station_id)}
          >
            {s.trust_score < 80 && (
              <circle r="14" fill={color} opacity="0.18">
                <animate attributeName="r" values="10;20;10" dur="2.2s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.28;0;0.28" dur="2.2s" repeatCount="indefinite" />
              </circle>
            )}
            <circle r={selected ? 8 : 6} fill={color} stroke="#06090d" strokeWidth="2" />
            {selected && <circle r="12" fill="none" stroke={color} strokeWidth="1.5" opacity="0.7" />}
            <text y="-14" textAnchor="middle" className="marker-label">
              {s.name.replace('AWS-', '')}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
