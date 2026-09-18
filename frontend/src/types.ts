export interface Reading {
  station_id: string;
  timestamp: number;
  temperature: number | null;
  humidity: number | null;
  pressure: number | null;
  wind_speed: number | null;
  wind_direction: number | null;
  rainfall: number | null;
  solar_radiation: number | null;
  battery_voltage: number | null;
  fault_injected: string | null;
}

export interface Station {
  station_id: string;
  name: string;
  latitude: number;
  longitude: number;
  elevation_m: number;
  latest_reading: Reading | null;
  trust_score: number;
  has_active_fault: boolean;
}

export interface Anomaly {
  id: string;
  time: number;
  station_id: string;
  station_name: string;
  parameter: string;
  raw_value: number | null;
  corrected_value: number | null;
  trust_score: number;
  root_cause: string;
  explanation: string;
  model_votes: { z_score: number; isolation_forest: number; spatial_disagreement: number };
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
}

export interface DashboardSummary {
  total_stations: number;
  healthy_stations: number;
  active_alerts: number;
  avg_trust_score: number;
  root_cause_breakdown: Record<string, number>;
}

export interface LiveFeedMessage {
  type: 'reading';
  station_id: string;
  station_name: string;
  reading: Reading;
  results: Anomaly[];
}

export const ROOT_CAUSE_LABELS: Record<string, string> = {
  HARDWARE_FAULT: 'Hardware Fault',
  SENSOR_DRIFT: 'Sensor Drift',
  COMMS_LOSS: 'Comms Loss',
  EXTREME_WEATHER: 'Extreme Weather',
  CALIBRATION_ERROR: 'Calibration Error',
  NORMAL: 'Normal',
};

export const FAULT_TYPES = ['SPIKE', 'DRIFT', 'FLATLINE', 'DROPOUT', 'NOISE_BURST'] as const;
export const PARAMETERS = ['temperature', 'humidity', 'pressure', 'wind_speed', 'solar_radiation'] as const;
