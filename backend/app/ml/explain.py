"""
Explanation Layer
------------------
Turns an AnomalyResult into a plain-English explanation + recommended action.

Ships as a fast, free, offline rule-based template engine so the demo never
depends on network/API-key availability. If you want the LLM-narrated version
for extra WOW factor, set GROQ_API_KEY (or GEMINI_API_KEY) in your .env and
flip USE_LLM=True below - the call site (routes/anomalies.py) is already wired
for it via `explain_with_llm()`.
"""
from __future__ import annotations

import os

USE_LLM = False  # flip to True once you add an API key in .env

TEMPLATES = {
    "HARDWARE_FAULT": (
        "The {param} reading diverged sharply from both the station's own recent history "
        "and its neighboring stations, and shows signs of a stuck or malfunctioning sensor. "
        "Likely cause: physical sensor/hardware fault. Recommended action: schedule a field "
        "inspection of the {param} sensor."
    ),
    "SENSOR_DRIFT": (
        "The {param} reading has been steadily diverging from its historical baseline while "
        "nearby stations remain stable, consistent with gradual sensor calibration drift. "
        "Recommended action: flag for recalibration during the next maintenance cycle."
    ),
    "COMMS_LOSS": (
        "No {param} reading was received from this station. This looks like a communications "
        "or power interruption rather than a weather event. Recommended action: check station "
        "connectivity and battery status."
    ),
    "EXTREME_WEATHER": (
        "The {param} reading is unusual for this station, but neighboring stations show a "
        "similar shift, suggesting this reflects a genuine extreme weather event rather than "
        "a sensor problem. Recommended action: no maintenance needed - flag for forecaster review."
    ),
    "CALIBRATION_ERROR": (
        "The {param} reading pattern is statistically unusual across multiple parameters at once, "
        "consistent with a calibration or configuration issue rather than a single-sensor fault. "
        "Recommended action: review station calibration settings."
    ),
    "NORMAL": "Reading is within expected bounds for this station and time.",
}


def explain(root_cause: str, parameter: str, raw_value, corrected_value, trust_score: float) -> str:
    template = TEMPLATES.get(root_cause, TEMPLATES["NORMAL"])
    text = template.format(param=parameter)
    if corrected_value is not None and raw_value is not None and corrected_value != raw_value:
        text += f" Value auto-corrected from {raw_value} to an estimated {corrected_value} for downstream use."
    return text


async def explain_with_llm(root_cause: str, parameter: str, raw_value, trust_score: float) -> str:
    """
    Optional upgrade: call a free LLM API (Groq/Gemini) for a richer, more natural narration.
    Left as a clearly-marked stub so you can drop in a real call during the hackathon:

        from groq import Groq
        client = Groq(api_key=os.environ["GROQ_API_KEY"])
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": f"..."}],
        )
        return resp.choices[0].message.content
    """
    return explain(root_cause, parameter, raw_value, None, trust_score)
