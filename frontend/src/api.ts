import { useEffect, useRef, useState, useCallback } from 'react';
import type { Station, Anomaly, DashboardSummary, LiveFeedMessage, Reading } from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE = API_BASE.replace('http', 'ws');

export async function fetchStations(): Promise<Station[]> {
  const res = await fetch(`${API_BASE}/api/stations`);
  return res.json();
}

export async function fetchAnomalies(): Promise<Anomaly[]> {
  const res = await fetch(`${API_BASE}/api/anomalies`);
  return res.json();
}

export async function fetchSummary(): Promise<DashboardSummary> {
  const res = await fetch(`${API_BASE}/api/dashboard/summary`);
  return res.json();
}

export async function fetchStationReadings(stationId: string, limit = 60): Promise<Reading[]> {
  const res = await fetch(`${API_BASE}/api/stations/${stationId}/readings?limit=${limit}`);
  return res.json();
}

export async function injectFault(body: {
  station_id: string;
  fault_type: string;
  parameter: string;
  magnitude?: number;
  duration_ticks?: number;
}) {
  const res = await fetch(`${API_BASE}/api/simulate/inject-fault`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function resetSimulation() {
  const res = await fetch(`${API_BASE}/api/simulate/reset`, { method: 'POST' });
  return res.json();
}

export async function submitFeedback(anomalyId: string, verdict: 'CONFIRMED' | 'FALSE_POSITIVE') {
  const res = await fetch(`${API_BASE}/api/anomalies/${anomalyId}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ anomaly_id: anomalyId, verdict }),
  });
  return res.json();
}

/** Live WebSocket feed with auto-reconnect. */
export function useLiveFeed(onMessage: (msg: LiveFeedMessage) => void) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/live-feed`);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      setTimeout(connect, 2000);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as LiveFeedMessage;
        onMessageRef.current(data);
      } catch {
        /* ignore malformed frame */
      }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { connected };
}
