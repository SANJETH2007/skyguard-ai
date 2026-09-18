import { useCallback, useEffect, useState } from 'react';
import KpiBar from './components/KpiBar';
import StationMap from './components/StationMap';
import AnomalyFeed from './components/AnomalyFeed';
import FaultPanel from './components/FaultPanel';
import StationDetail from './components/StationDetail';
import { fetchStations, fetchAnomalies, fetchSummary, submitFeedback, useLiveFeed } from './api';
import type { Station, Anomaly, DashboardSummary, Reading } from './types';
import './App.css';

export default function App() {
  const [stations, setStations] = useState<Station[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [liveReading, setLiveReading] = useState<Reading | null>(null);

  const refreshAll = useCallback(async () => {
    const [s, a, sum] = await Promise.all([fetchStations(), fetchAnomalies(), fetchSummary()]);
    setStations(s);
    setAnomalies(a);
    setSummary(sum);
  }, []);

  useEffect(() => {
    refreshAll();
    const interval = setInterval(refreshAll, 4000);
    return () => clearInterval(interval);
  }, [refreshAll]);

  const { connected } = useLiveFeed((msg) => {
    setLiveReading(msg.reading);
    if (msg.results.length > 0) {
      setAnomalies((prev) => [...msg.results, ...prev].slice(0, 200));
    }
  });

  const handleFeedback = async (id: string, verdict: 'CONFIRMED' | 'FALSE_POSITIVE') => {
    setAnomalies((prev) => prev.map((a) => (a.id === id ? { ...a, status: verdict === 'CONFIRMED' ? 'ACKNOWLEDGED' : 'RESOLVED' } : a)));
    await submitFeedback(id, verdict);
  };

  const selectedStation = stations.find((s) => s.station_id === selectedId) ?? null;
  const openAnomalies = anomalies.filter((a) => a.status === 'OPEN');

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>SkyGuard AI</h1>
          <p>Intelligent Anomaly Detection for Automatic Weather Stations</p>
        </div>
      </header>

      <KpiBar summary={summary} connected={connected} />

      <div className="app-grid">
        <div className="app-col app-col-map">
          <StationMap stations={stations} selectedId={selectedId} onSelect={setSelectedId} />
          <StationDetail station={selectedStation} liveReading={liveReading} />
          <FaultPanel stations={stations} />
        </div>
        <div className="app-col app-col-feed">
          <AnomalyFeed anomalies={openAnomalies} onFeedback={handleFeedback} />
        </div>
      </div>
    </div>
  );
}
