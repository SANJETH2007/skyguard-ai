"""
Virtual AWS Station Simulator
------------------------------
Generates realistic weather telemetry for N virtual stations and supports
live fault injection for demo purposes. Designed to stand in for a real
MQTT-connected Automatic Weather Station network.

Fault types modeled:
  - SPIKE            : sudden, physically implausible jump in one parameter
  - DRIFT             : slow, monotonic sensor calibration drift
  - FLATLINE          : sensor stuck reporting the same value (stuck ADC / frozen probe)
  - DROPOUT           : missing / null readings (comms loss)
  - NOISE_BURST       : sudden high-variance noisy readings (loose connector)
"""
from __future__ import annotations

import math
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


PARAMETERS = [
    "temperature", "humidity", "pressure",
    "wind_speed", "wind_direction", "rainfall", "solar_radiation",
]


@dataclass
class FaultState:
    fault_type: str
    parameter: str
    started_at: float
    magnitude: float = 1.0
    ticks_remaining: int = 40  # how many readings the fault persists for


@dataclass
class Station:
    station_id: str
    name: str
    latitude: float
    longitude: float
    elevation_m: float
    # base climatology (varies smoothly with a diurnal cycle)
    base_temp: float = 27.0
    base_humidity: float = 60.0
    base_pressure: float = 1012.0
    active_fault: Optional[FaultState] = None
    drift_offset: float = 0.0
    tick: int = 0

    def neighbors_hint(self) -> str:
        return f"{self.latitude:.2f},{self.longitude:.2f}"

    def inject_fault(self, fault_type: str, parameter: str, magnitude: float = 1.0, duration_ticks: int = 40):
        self.active_fault = FaultState(
            fault_type=fault_type,
            parameter=parameter,
            started_at=time.time(),
            magnitude=magnitude,
            ticks_remaining=duration_ticks,
        )

    def clear_fault(self):
        self.active_fault = None
        self.drift_offset = 0.0

    def read(self) -> dict:
        """Produce one telemetry reading, applying any active fault."""
        self.tick += 1
        hour = (time.time() / 3600.0) % 24
        diurnal = math.sin((hour - 9) / 24 * 2 * math.pi)

        reading = {
            "station_id": self.station_id,
            "timestamp": time.time(),
            "temperature": round(self.base_temp + diurnal * 6 + random.gauss(0, 0.3), 2),
            "humidity": round(min(100, max(5, self.base_humidity - diurnal * 15 + random.gauss(0, 2))), 2),
            "pressure": round(self.base_pressure + random.gauss(0, 0.5), 2),
            "wind_speed": round(max(0, 3 + random.gauss(0, 1.5)), 2),
            "wind_direction": round(random.uniform(0, 360), 1),
            "rainfall": round(max(0, random.gauss(0, 0.2)) if random.random() > 0.85 else 0.0, 2),
            "solar_radiation": round(max(0, 600 * max(0, math.sin(hour / 24 * math.pi)) + random.gauss(0, 20)), 1),
            "battery_voltage": round(12.4 + random.gauss(0, 0.05), 2),
            "fault_injected": None,
        }

        fault = self.active_fault
        if fault and fault.ticks_remaining > 0:
            p = fault.parameter
            if fault.fault_type == "SPIKE":
                reading[p] = reading[p] + fault.magnitude * random.choice([-1, 1]) * abs(reading[p] or 10) * 1.5
            elif fault.fault_type == "DRIFT":
                self.drift_offset += 0.15 * fault.magnitude
                reading[p] = reading[p] + self.drift_offset
            elif fault.fault_type == "FLATLINE":
                reading[p] = getattr(self, f"_frozen_{p}", reading[p])
                setattr(self, f"_frozen_{p}", reading[p])
            elif fault.fault_type == "DROPOUT":
                reading[p] = None
            elif fault.fault_type == "NOISE_BURST":
                reading[p] = reading[p] + random.gauss(0, 1) * 8 * fault.magnitude

            reading["fault_injected"] = fault.fault_type
            fault.ticks_remaining -= 1
            if fault.ticks_remaining <= 0:
                self.clear_fault()

        return reading


def make_default_network(n_stations: int = 15) -> list[Station]:
    """Create a realistic spread of virtual stations across a region (default: south India bounding box)."""
    random.seed(42)
    names = [
        "Coimbatore", "Chennai", "Madurai", "Salem", "Trichy", "Ooty",
        "Kochi", "Bengaluru", "Mysuru", "Mangaluru", "Vellore", "Tirupati",
        "Puducherry", "Kozhikode", "Thanjavur", "Erode", "Hosur", "Nagercoil",
        "Kanyakumari", "Coorg",
    ]
    stations = []
    for i in range(min(n_stations, len(names))):
        lat = 8.0 + random.random() * 5.0
        lon = 76.5 + random.random() * 4.5
        stations.append(
            Station(
                station_id=str(uuid.uuid4()),
                name=f"AWS-{names[i]}",
                latitude=round(lat, 4),
                longitude=round(lon, 4),
                elevation_m=round(random.uniform(10, 900), 1),
                base_temp=round(random.uniform(24, 32), 1),
                base_humidity=round(random.uniform(50, 75), 1),
                base_pressure=round(random.uniform(1008, 1015), 1),
            )
        )
    return stations
