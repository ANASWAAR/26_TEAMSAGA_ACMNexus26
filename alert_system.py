from typing import Dict

# Alert generation and delivery simulation

ALERT_COLORS = {
    "SAFE": "green",
    "CAUTION": "yellow",
    "DANGER": "red",
    "EXTREME": "darkred",
}


def build_priority_message(risk_label: str, probability: int, forecast_hour: int) -> str:
    """Create a short alert headline for the UI."""
    return (
        f"{probability}% chance of {risk_label.lower()} conditions in {forecast_hour} hour(s)."
        if forecast_hour > 0
        else f"Current status is {risk_label.lower()}."
    )


def simulate_delivery(message: str, channel: str = "SMS") -> str:
    """Return a simulated delivery message for low-network alert delivery."""
    return f"[{channel}] {message}"


def offline_alert_text(risk_label: str, user_type: str, emergency: bool = False) -> str:
    """Generate an offline-friendly alert summary."""
    prefix = "EMERGENCY:" if emergency else "ALERT:"
    return (
        f"{prefix} {risk_label} risk for {user_type}. "
        f"Send this message by voice call or text if the network is weak."
    )


def get_display_style(risk_label: str) -> Dict[str, str]:
    """Return display metadata based on current risk."""
    return {
        "label": risk_label,
        "color": ALERT_COLORS.get(risk_label, "gray"),
    }

def format_status(lat: float, lon: float, age_minutes: float) -> str:
    """Return a readable data status string."""
    if age_minutes < 10:
        status = "Live"
    elif age_minutes < 60:
        status = "Recent"
    else:
        status = "Stale"

    return f"{status} ({int(age_minutes)} min ago)"