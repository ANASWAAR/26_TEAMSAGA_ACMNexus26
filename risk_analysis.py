import datetime
import math
import statistics
from typing import Dict, List, Tuple

# Risk scoring and prediction logic

RISK_STYLES = {
    "SAFE": {"emoji": "🟢", "color": "green"},
    "CAUTION": {"emoji": "🟡", "color": "yellow"},
    "DANGER": {"emoji": "🔴", "color": "red"},
    "EXTREME": {"emoji": "⚫", "color": "darkred"},
}

def get_dynamic_thresholds(data: List[Dict]) -> Dict[str, float]:
    """
    Hybrid thresholds: combines real-world marine limits + dynamic scaling
    """

    waves = [entry["waveHeight"] for entry in data]
    winds = [entry["windSpeed"] for entry in data]

    avg_wave = max(0.5, statistics.mean(waves))
    avg_wind = max(4.0, statistics.mean(winds))

    return {
        # REAL BASELINE + dynamic adjustment
        "safe_wave": max(0.8, avg_wave * 0.7),
        "caution_wave": max(1.2, avg_wave * 1.1),
        "danger_wave": max(1.8, avg_wave * 1.6),
        "extreme_wave": max(2.5, avg_wave * 2.2),

        "safe_wind": max(5.0, avg_wind * 0.7),
        "caution_wind": max(8.0, avg_wind * 1.0),
        "danger_wind": max(12.0, avg_wind * 1.4),
        "extreme_wind": max(15.0, avg_wind * 1.8),
    }

def compute_spike_score(history: List[Dict], current: Dict) -> float:
    """Detect sudden recent spikes in wave or wind."""
    if len(history) < 2:
        return 0.0

    previous = history[-2]
    wave_delta = current["waveHeight"] - previous["waveHeight"]
    wind_delta = current["windSpeed"] - previous["windSpeed"]
    average_wave = statistics.mean([entry["waveHeight"] for entry in history[-4:]])
    average_wind = statistics.mean([entry["windSpeed"] for entry in history[-4:]])

    wave_spike = max(0.0, wave_delta / max(average_wave, 0.5))
    wind_spike = max(0.0, wind_delta / max(average_wind, 1.0))
    return round(min(1.0, (wave_spike + wind_spike) / 2.0), 2)


def compute_risk_score(entry: Dict, thresholds: Dict[str, float], spike_score: float = 0.0) -> float:
    """
    Hybrid risk scoring using real thresholds + normalization
    """

    wave = entry["waveHeight"]
    wind = entry["windSpeed"]

    # Normalize against REAL danger levels
    wave_score = min(wave / thresholds["danger_wave"], 1.0)
    wind_score = min(wind / thresholds["danger_wind"], 1.0)

    # Weighted importance
    base_score = (0.6 * wave_score) + (0.4 * wind_score)

    # Spike boost
    spike_bonus = spike_score * 0.25

    # Final score
    return round(min(1.0, base_score + spike_bonus), 2)


def classify_risk(score: float) -> Tuple[str, Dict[str, str]]:
    """Map a risk score to a named category and style metadata."""
    if score < 0.35:
        label = "SAFE"
    elif score < 0.6:
        label = "CAUTION"
    elif score < 0.85:
        label = "DANGER"
    else:
        label = "EXTREME"

    return label, RISK_STYLES[label]


def detect_anomaly(history: List[Dict], current: Dict) -> bool:
    """Detect whether current measurements are unusually high compared to history."""
    if len(history) < 3:
        return False

    waves = [entry["waveHeight"] for entry in history]
    winds = [entry["windSpeed"] for entry in history]
    wave_mean = statistics.mean(waves)
    wind_mean = statistics.mean(winds)
    wave_std = statistics.pstdev(waves)
    wind_std = statistics.pstdev(winds)

    return (
        current["waveHeight"] > wave_mean + 2.0 * max(wave_std, 0.1)
        or current["windSpeed"] > wind_mean + 2.0 * max(wind_std, 0.1)
    )


def prepare_risk_series(fused_data: List[Dict]) -> List[Dict]:
    """Add risk metadata to each fused hourly record."""
    history = []
    thresholds = get_dynamic_thresholds(fused_data[:6] if len(fused_data) >= 6 else fused_data)
    risk_series = []

    for entry in fused_data:
        spike = compute_spike_score(history + [entry], entry)
        score = compute_risk_score(entry, thresholds, spike)
        label, style = classify_risk(score)
        anomaly = detect_anomaly(history[-6:] + [entry], entry)

        risk_series.append(
            {
                "time": entry["time"],
                "waveHeight": entry["waveHeight"],
                "windSpeed": entry["windSpeed"],
                "riskScore": score,
                "riskLabel": label,
                "riskEmoji": style["emoji"],
                "riskColor": style["color"],
                "spike": spike,
                "anomaly": anomaly,
            }
        )
        history.append(entry)

    return risk_series


def forecast_risk(risk_series: List[Dict], horizon: int = 6) -> List[Dict]:
    """Produce a simple probability forecast for the next few hours."""
    forecast = []
    current_score = risk_series[0]["riskScore"] if risk_series else 0.0

    for index in range(1, min(horizon + 1, len(risk_series))):
        entry = risk_series[index]
        trend = 0.1 * index
        probability = min(1.0, entry["riskScore"] + trend)
        forecast.append(
            {
                "time": entry["time"],
                "predictedLabel": entry["riskLabel"],
                "probability": int(probability * 100),
                "waveHeight": entry["waveHeight"],
                "windSpeed": entry["windSpeed"],
            }
        )

    return forecast


def generate_recommendation(risk_label: str, user_type: str, spike: float, probability: int) -> str:
    """Return a dynamic recommendation message for a user type."""
    base_actions = {
        "SAFE": "normal coastal activity is allowed.",
        "CAUTION": "prepare for changing conditions and keep a watch on equipment.",
        "DANGER": "limit exposure and move non-essential gear inland.",
        "EXTREME": "avoid all coastal operations and stay indoors immediately.",
    }

    user_messages = {
        "Fishermen": "Avoid sailing and delay trips until conditions improve.",
        "Residents": "Secure boats, stay indoors, and keep emergency contacts ready.",
    }

    spike_text = "" if spike < 0.2 else " A sudden spike has been detected in the latest measurements."
    chance_text = f" Estimated {probability}% chance of this risk level in the near term."

    return (
        f"{user_messages.get(user_type, base_actions[risk_label])} "
        f"Current state: {risk_label}. {base_actions[risk_label]}" + spike_text + chance_text
    )


def format_status(lat: float, lon: float, data_age_mins: float) -> str:
    """Return a human-friendly status indicator for live or delayed data."""
    if data_age_mins < 20:
        return "Live"
    if data_age_mins < 60:
        return "Delayed"
    return "Offline-Friendly"
