# Architecture

## Data flow

```
Virtual AWS Stations (backend/app/simulator.py)
        │  in-process, 1.5s tick — swap for MQTT subscriber against real hardware
        ▼
Ensemble Anomaly Engine (backend/app/ml/engine.py)
   ├─ Statistical: rolling MAD/Z-score per station per parameter
   ├─ Isolation Forest: multivariate outlier detection, refit periodically
   └─ Spatial cross-check: disagreement vs. 3 nearest neighboring stations
        │  weighted vote → Trust Score (0-100)
        ▼
Root-Cause Classifier (rule-based, in engine.py)
   → HARDWARE_FAULT | SENSOR_DRIFT | COMMS_LOSS | EXTREME_WEATHER | CALIBRATION_ERROR
        ▼
Explanation Layer (backend/app/ml/explain.py)
   → plain-English narration + recommended action (LLM hook available, off by default)
        ▼
REST API + WebSocket broadcast (backend/app/main.py)
        ▼
React Dashboard (frontend/src) — live map, anomaly feed, station detail, fault injector
```

## Current implementation vs. production target

| Component | Hackathon prototype | Production target |
|---|---|---|
| Data ingestion | In-process simulator | MQTT broker (Mosquitto) + real AWS telemetry |
| Storage | In-memory Python dicts | TimescaleDB (Postgres extension for time-series) |
| Statistical detection | MAD/Z-score | Same, kept as a fast first-pass filter |
| Multivariate detection | Isolation Forest (per-station, refit every 10 ticks) | LSTM Autoencoder trained per station/cluster |
| Spatial validation | Nearest-3-neighbor Euclidean disagreement | Graph Neural Network over the full station network |
| Explanation | Rule-based templates | LLM-narrated (Groq/Gemini — hook in `explain.py`) |
| Root-cause classification | Hand-written rules on model outputs | Trained classifier (Random Forest / gradient boosted) on labeled fault data |

## Why this design

The seams above are intentional: every "prototype" component has the exact same input/output contract as its "production" replacement, so swapping one out doesn't require touching the rest of the pipeline. This was deliberate for the hackathon timeline — the ensemble/root-cause/explanation architecture is fully demonstrable end-to-end even though individual models are simplified.
