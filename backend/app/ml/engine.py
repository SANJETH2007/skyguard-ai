"""
SkyGuard AI - Ensemble Anomaly Detection Engine
-------------------------------------------------
Combines three signals into a single explainable Trust Score (0-100):

  1. Statistical model   - rolling Z-score / MAD against each station's own recent history
  2. Isolation Forest     - multivariate outlier detection across all parameters at once
  3. Spatial cross-check  - compares a station's reading against its nearest neighbors;
                            large disagreement + neighbors normal => sensor fault, not weather

A lightweight rule-based Root-Cause Classifier turns the combined signal pattern
into a human-readable category, which the explanation layer narrates.

This is intentionally dependency-light (numpy + scikit-learn only) so it runs
instantly in a hackathon environment, while the interfaces mirror what a
production LSTM-autoencoder / spatial-GNN version would expose (see comments).
"""
from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from sklearn.ensemble import IsolationForest

from ..simulator import PARAMETERS  # noqa: F401 (kept for parity with simulator param list)

HISTORY_LEN = 60  # readings kept per station per parameter for the rolling baseline


@dataclass
class AnomalyResult:
    station_id: str
    parameter: str
    raw_value: Optional[float]
    corrected_value: Optional[float]
    trust_score: float
    root_cause: str
    model_votes: dict
    is_anomaly: bool


class AnomalyEngine:
    def __init__(self):
        # station_id -> parameter -> deque of recent values
        self.history: dict[str, dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=HISTORY_LEN)))
        # station_id -> IsolationForest (refit periodically once enough history exists)
        self._iso_models: dict[str, IsolationForest] = {}
        self._iso_refit_counter: dict[str, int] = defaultdict(int)
        self.station_positions: dict[str, tuple[float, float]] = {}
        self.latest_reading: dict[str, dict] = {}

    def register_station(self, station_id: str, lat: float, lon: float):
        self.station_positions[station_id] = (lat, lon)

    # ---------- helpers -------------------------------------------------

    def _nearest_neighbors(self, station_id: str, k: int = 3) -> list[str]:
        if station_id not in self.station_positions:
            return []
        lat0, lon0 = self.station_positions[station_id]
        dists = []
        for sid, (lat, lon) in self.station_positions.items():
            if sid == station_id:
                continue
            d = math.hypot(lat - lat0, lon - lon0)
            dists.append((d, sid))
        dists.sort(key=lambda x: x[0])
        return [sid for _, sid in dists[:k]]

    def _z_score(self, values: deque, x: float) -> float:
        if len(values) < 8:
            return 0.0
        arr = np.array(values)
        med = np.median(arr)
        mad = np.median(np.abs(arr - med)) or 1e-6
        return abs(0.6745 * (x - med) / mad)  # modified Z-score (MAD-based)

    def _isolation_forest_score(self, station_id: str, reading: dict) -> float:
        vec_params = ["temperature", "humidity", "pressure", "wind_speed", "solar_radiation"]
        hist = self.history[station_id]
        rows = []
        n = min(len(hist[p]) for p in vec_params) if all(len(hist[p]) for p in vec_params) else 0
        if n < 15:
            return 0.0
        for i in range(-n, 0):
            rows.append([list(hist[p])[i] for p in vec_params])
        X = np.array(rows)

        self._iso_refit_counter[station_id] += 1
        if station_id not in self._iso_models or self._iso_refit_counter[station_id] % 10 == 0:
            model = IsolationForest(n_estimators=80, contamination=0.05, random_state=42)
            model.fit(X)
            self._iso_models[station_id] = model
        model = self._iso_models[station_id]

        x_vec = np.array([[reading.get(p) if reading.get(p) is not None else np.nan for p in vec_params]])
        if np.isnan(x_vec).any():
            return 1.0  # missing multivariate data is itself suspicious
        raw_score = -model.score_samples(x_vec)[0]  # higher = more anomalous
        return float(np.clip(raw_score * 3, 0, 3))  # rescale roughly onto same range as z-score

    def _spatial_disagreement(self, station_id: str, parameter: str, value: Optional[float]) -> float:
        """Return 0..1: how much this station disagrees with its neighbors' current readings."""
        if value is None:
            return 0.5
        neighbor_ids = self._nearest_neighbors(station_id)
        neighbor_vals = []
        for nid in neighbor_ids:
            r = self.latest_reading.get(nid)
            if r and r.get(parameter) is not None:
                neighbor_vals.append(r[parameter])
        if len(neighbor_vals) < 2:
            return 0.0
        neighbor_mean = float(np.mean(neighbor_vals))
        neighbor_std = float(np.std(neighbor_vals)) or 1.0
        disagreement = abs(value - neighbor_mean) / (neighbor_std * 3 + 1e-6)
        return float(np.clip(disagreement, 0, 1))

    # ---------- root-cause classifier ------------------------------------

    def _classify_root_cause(self, z: float, iso: float, spatial: float, value: Optional[float],
                              recent: deque) -> str:
        if value is None:
            return "COMMS_LOSS"
        if len(recent) >= 6:
            last_vals = list(recent)[-6:]
            if len(set(round(v, 2) for v in last_vals)) == 1:
                return "HARDWARE_FAULT"  # flatlined sensor
        if z > 3.5 and spatial < 0.3:
            # station itself is extreme, but neighbors agree/nearby -> genuine event
            return "EXTREME_WEATHER"
        if z > 3.0 and spatial > 0.6:
            return "HARDWARE_FAULT"  # this station diverges hard from its own baseline AND neighbors
        if 1.5 < z <= 3.0 and spatial > 0.5:
            return "SENSOR_DRIFT"
        if iso > 1.8 and spatial < 0.3:
            return "EXTREME_WEATHER"
        if iso > 1.2:
            return "CALIBRATION_ERROR"
        return "NORMAL"

    # ---------- main entrypoint -------------------------------------------

    def process(self, reading: dict) -> list[AnomalyResult]:
        station_id = reading["station_id"]
        self.latest_reading[station_id] = reading
        results = []

        for param in ["temperature", "humidity", "pressure", "wind_speed", "solar_radiation"]:
            value = reading.get(param)
            hist = self.history[station_id][param]
            warmed_up = len(hist) >= 20  # avoid false positives before a real baseline exists

            z = self._z_score(hist, value) if value is not None else 4.0
            iso = self._isolation_forest_score(station_id, reading) if warmed_up else 0.0
            spatial = self._spatial_disagreement(station_id, param, value)

            # weighted ensemble vote -> combined severity 0..~5
            combined = 0.5 * z + 0.3 * iso + 0.2 * (spatial * 5)
            trust_score = float(np.clip(100 - combined * 14, 0, 100))
            is_anomaly = warmed_up and trust_score < 65 and (value is None or z > 1.2 or iso > 0.8)

            root_cause = self._classify_root_cause(z, iso, spatial, value, hist) if is_anomaly else "NORMAL"

            corrected_value = value
            if is_anomaly and root_cause in ("HARDWARE_FAULT", "SENSOR_DRIFT", "CALIBRATION_ERROR", "COMMS_LOSS"):
                # simple auto-correction: fall back to robust median of recent history
                # (production version: spatiotemporal Kriging / GNN reconstruction)
                if len(hist) >= 5:
                    corrected_value = round(float(np.median(hist)), 2)

            if value is not None:
                hist.append(value)

            results.append(
                AnomalyResult(
                    station_id=station_id,
                    parameter=param,
                    raw_value=value,
                    corrected_value=corrected_value,
                    trust_score=round(trust_score, 1),
                    root_cause=root_cause,
                    model_votes={"z_score": round(z, 2), "isolation_forest": round(iso, 2), "spatial_disagreement": round(spatial, 2)},
                    is_anomaly=is_anomaly,
                )
            )
        return results
