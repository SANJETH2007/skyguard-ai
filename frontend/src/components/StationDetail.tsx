import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { Reading, Station } from '../types';
import { fetchStationReadings } from '../api';
import './StationDetail.css';

export default function StationDetail({ station, liveReading }: { station: Station | null; liveReading: Reading | null }) {
  const [history, setHistory] = useState<Reading[]>([]);

  useEffect(() => {
    if (!station) return;
    fetchStationReadings(station.station_id, 60).then(setHistory);
  }, [station?.station_id]);

  useEffect(() => {
    if (liveReading && station && liveReading.station_id === station.station_id) {
      setHistory((prev) => [...prev.slice(-59), liveReading]);
    }
  }, [liveReading, station?.station_id]);

  if (!station) {
    return <div className="detail-panel detail-empty">Select a station on the map to see live telemetry.</div>;
  }

  const chartData = history.map((r) => ({
    time: new Date(r.timestamp * 1000).toLocaleTimeString([], { minute: '2-digit', second: '2-digit' }),
    temperature: r.temperature,
    humidity: r.humidity,
  }));

  return (
    <div className="detail-panel">
      <div className="detail-header">
        <div>
          <div className="detail-name">{station.name}</div>
          <div className="detail-meta">
            {station.latitude.toFixed(2)}°, {station.longitude.toFixed(2)}° · {station.elevation_m}m elevation
          </div>
        </div>
        <div className="detail-trust" style={{ color: station.trust_score >= 80 ? 'var(--signal-good)' : station.trust_score >= 60 ? 'var(--signal-warn)' : 'var(--signal-bad)' }}>
          {station.trust_score}%
        </div>
      </div>

      {station.latest_reading && (
        <div className="detail-metrics">
          <Metric label="Temp" value={`${station.latest_reading.temperature ?? '—'}°C`} />
          <Metric label="Humidity" value={`${station.latest_reading.humidity ?? '—'}%`} />
          <Metric label="Pressure" value={`${station.latest_reading.pressure ?? '—'} hPa`} />
          <Metric label="Wind" value={`${station.latest_reading.wind_speed ?? '—'} m/s`} />
        </div>
      )}

      <div className="detail-chart">
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={chartData}>
            <CartesianGrid stroke="#152029" strokeDasharray="3 3" />
            <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#7c8b99' }} minTickGap={30} />
            <YAxis tick={{ fontSize: 10, fill: '#7c8b99' }} width={30} />
            <Tooltip contentStyle={{ background: '#0d131a', border: '1px solid #1e2933', fontSize: 12 }} />
            <Line type="monotone" dataKey="temperature" stroke="#ff5470" dot={false} strokeWidth={2} isAnimationActive={false} />
            <Line type="monotone" dataKey="humidity" stroke="#4fc3ff" dot={false} strokeWidth={2} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
        <div className="chart-legend">
          <span><i style={{ background: '#ff5470' }} /> Temperature (°C)</span>
          <span><i style={{ background: '#4fc3ff' }} /> Humidity (%)</span>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
    </div>
  );
}
