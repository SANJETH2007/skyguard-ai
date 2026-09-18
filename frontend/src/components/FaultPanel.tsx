import { useState } from 'react';
import type { Station } from '../types';
import { FAULT_TYPES, PARAMETERS } from '../types';
import { injectFault, resetSimulation } from '../api';
import './FaultPanel.css';

const FAULT_DESCRIPTIONS: Record<string, string> = {
  SPIKE: 'Sudden implausible jump — e.g. lightning-induced transient',
  DRIFT: 'Slow calibration drift over time',
  FLATLINE: 'Sensor stuck reporting the same value',
  DROPOUT: 'Communications / power loss — missing readings',
  NOISE_BURST: 'High-variance noisy readings — loose connector',
};

export default function FaultPanel({ stations }: { stations: Station[] }) {
  const [stationId, setStationId] = useState('');
  const [faultType, setFaultType] = useState<typeof FAULT_TYPES[number]>('SPIKE');
  const [parameter, setParameter] = useState<typeof PARAMETERS[number]>('temperature');
  const [busy, setBusy] = useState(false);
  const [lastMessage, setLastMessage] = useState<string | null>(null);

  const handleInject = async () => {
    if (!stationId) return;
    setBusy(true);
    try {
      const res = await injectFault({ station_id: stationId, fault_type: faultType, parameter, magnitude: 1.0, duration_ticks: 40 });
      setLastMessage(res.message ?? 'Fault injected.');
    } finally {
      setBusy(false);
    }
  };

  const handleReset = async () => {
    setBusy(true);
    try {
      await resetSimulation();
      setLastMessage('Simulation reset — all faults cleared.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fault-panel">
      <div className="fault-panel-header">⚡ Demo: Inject Live Fault</div>
      <div className="fault-panel-grid">
        <label>
          Station
          <select value={stationId} onChange={(e) => setStationId(e.target.value)}>
            <option value="">Select station…</option>
            {stations.map((s) => (
              <option key={s.station_id} value={s.station_id}>{s.name}</option>
            ))}
          </select>
        </label>
        <label>
          Parameter
          <select value={parameter} onChange={(e) => setParameter(e.target.value as typeof parameter)}>
            {PARAMETERS.map((p) => (
              <option key={p} value={p}>{p.replace('_', ' ')}</option>
            ))}
          </select>
        </label>
        <label>
          Fault type
          <select value={faultType} onChange={(e) => setFaultType(e.target.value as typeof faultType)}>
            {FAULT_TYPES.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </label>
      </div>
      <p className="fault-desc">{FAULT_DESCRIPTIONS[faultType]}</p>
      <div className="fault-actions">
        <button className="fault-btn-inject" disabled={!stationId || busy} onClick={handleInject}>
          Inject Fault
        </button>
        <button className="fault-btn-reset" disabled={busy} onClick={handleReset}>
          Reset Simulation
        </button>
      </div>
      {lastMessage && <div className="fault-message">{lastMessage}</div>}
    </div>
  );
}
