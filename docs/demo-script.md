# Demo Script

A suggested walkthrough for judges or stakeholders, roughly 2 minutes.

1. **Open the dashboard.** Point out the live map — all stations green, KPI bar showing network health, "Live" indicator confirming the WebSocket connection.
2. **State the problem in one line.** "AWS sensor networks silently feed bad data into forecasts — this system catches it in real time and explains why."
3. **Open the fault-injection panel.** Pick a station, choose `HARDWARE_FAULT`-style fault (e.g. `SPIKE` or `FLATLINE`), pick a parameter (e.g. `temperature`), and click **Inject Fault**.
4. **Watch it happen live.** Within a couple of seconds: the station's trust score drops on the map, a new card appears in the anomaly feed with the root cause and a plain-English explanation, and the KPI bar's active-alert count increments.
5. **Show root-cause diversity.** Inject a second fault of a different type (e.g. `DROPOUT` for comms loss) on a different station to show it isn't a one-trick detector.
6. **Click into a station.** Show the live time-series chart and the historical readings.
7. **Use the feedback buttons.** Click "Confirm" or "False positive" on an anomaly card to show the human-in-the-loop feedback path.
8. **Close on impact.** Emphasize: works with existing AWS hardware (protocol-agnostic ingestion), scales from 10 to thousands of stations (TimescaleDB target), and turns maintenance from reactive to proactive.
