import datetime
import os

import matplotlib.pyplot as plt
import streamlit as st
from dotenv import load_dotenv

from alert_system import (
    build_priority_message,
    format_status,
    offline_alert_text,
    simulate_delivery,
)
from data_fetch import prepare_fused_data
from risk_analysis import (
    forecast_risk,
    generate_recommendation,
    prepare_risk_series,
)

# Load API key from environment.
load_dotenv()
API_KEY = os.getenv("STORMGLASS_API_KEY")

st.set_page_config(
    page_title="Climate Intelligence System",
    page_icon="🌊",
    layout="wide",
)

if not API_KEY:
    st.title("Climate Intelligence System")
    st.error("API key not found. Please add STORMGLASS_API_KEY to your .env file.")
    st.stop()


@st.cache_data(ttl=300)
def load_weather_data(api_key: str, lat: float, lon: float, hours: int):
    """Fetch fused weather and risk data for the requested location."""
    return prepare_fused_data(api_key, lat, lon, hours)


def parse_timestamp(timestamp: str) -> datetime.datetime:
    """Parse an ISO timestamp string into a datetime object."""
    if timestamp.endswith("Z"):
        timestamp = timestamp.replace("Z", "+00:00")
    return datetime.datetime.fromisoformat(timestamp)


def get_data_age_minutes(timestamp: str) -> float:
    """Return the age of the latest data in minutes."""
    try:
        data_time = parse_timestamp(timestamp)
        age = datetime.datetime.utcnow() - data_time.replace(tzinfo=None)
        return age.total_seconds() / 60.0
    except Exception:
        return 999.0


st.title("🌊 Coastal Climate Intelligence System")
st.markdown(
    "This system combines multi-source coastal data, prediction, anomaly detection, and actionable alerts."
)

with st.sidebar:
    st.header("Settings")
    lat = st.number_input("Latitude", value=9.9312, format="%.4f")
    lon = st.number_input("Longitude", value=76.2673, format="%.4f")
    profile = st.radio("User profile", ["Fishermen", "Residents"])
    forecast_hours = st.slider("Forecast horizon (hours)", 3, 9, 6)
    refresh = st.button("🔄 Refresh Data")
    st.markdown("---")
    st.write("**This version supports:**")
    st.write("- Multi-source fusion (StormGlass, NOAA, ECMWF)")
    st.write("- Dynamic risk classification")
    st.write("- Prediction probabilities")
    st.write("- Offline-friendly alert text")

if refresh:
    st.experimental_rerun()

weather_bundle = load_weather_data(API_KEY, lat, lon, forecast_hours)
fused_data = weather_bundle.get("fused", [])

if not fused_data:
    st.error("Unable to load fused weather data. Please try again later.")
    st.stop()

risk_series = prepare_risk_series(fused_data)
current = risk_series[0]
forecast = forecast_risk(risk_series, horizon=forecast_hours)

status_age = get_data_age_minutes(current["time"])
status_label = format_status(lat, lon, status_age)

st.markdown("---")

# Top summary cards
st.subheader("📌 Summary")
metric_cols = st.columns(4)
metric_cols[0].metric("Location", f"{lat:.4f}, {lon:.4f}")
metric_cols[1].metric("Data Status", status_label)
metric_cols[2].metric("Risk", f"{current['riskEmoji']} {current['riskLabel']}")
metric_cols[3].metric("Age", f"{int(status_age)} min")

st.markdown("---")

# Alert section
alert_text = f"Current conditions are {current['riskLabel']}."
if current["spike"] > 0.2:
    alert_text += " A sudden spike has been detected in recent readings."

if current["riskLabel"] == "SAFE":
    st.success(alert_text)
elif current["riskLabel"] == "CAUTION":
    st.warning(alert_text)
elif current["riskLabel"] == "DANGER":
    st.error(alert_text)
else:
    st.error(alert_text)

with st.expander("🔮 Forecast alert timeline"):
    for index, item in enumerate(forecast, start=1):
        message = build_priority_message(item["predictedLabel"], item["probability"], index)
        st.write(f"**{item['time'][11:16]}** — {message}")

st.markdown("---")

# Recommendations and alert delivery
rec_col1, rec_col2 = st.columns([2, 1])
with rec_col1:
    st.subheader("🧭 Recommendation")
    estimate_probability = forecast[0]["probability"] if forecast else 0
    recommendation_text = generate_recommendation(
        current["riskLabel"], profile, current["spike"], estimate_probability
    )
    st.info(recommendation_text)

with rec_col2:
    st.subheader("📱 Notification simulation")
    st.write(simulate_delivery(recommendation_text, channel="SMS"))
    st.write(offline_alert_text(current["riskLabel"], profile, emergency=current["riskLabel"] in ["DANGER", "EXTREME"]))

st.markdown("---")

# Graphs
st.subheader("📈 Risk trend and forecast timeline")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
trend_hours = min(len(risk_series), forecast_hours)
trend_times = [entry["time"][11:16] for entry in risk_series[:trend_hours]]
trend_scores = [entry["riskScore"] for entry in risk_series[:trend_hours]]

ax1.plot(trend_times, trend_scores, marker="o", color="navy")
for index, entry in enumerate(risk_series[:trend_hours]):
    if entry["riskLabel"] in ["DANGER", "EXTREME"]:
        ax1.axvspan(index - 0.4, index + 0.4, color="red", alpha=0.1)
ax1.set_title("Risk score trend")
ax1.set_ylabel("Risk score")
ax1.set_ylim(0, 1)
ax1.grid(True)

wave_line = [entry["waveHeight"] for entry in risk_series[:trend_hours]]
wind_line = [entry["windSpeed"] for entry in risk_series[:trend_hours]]
ax2.plot(trend_times, wave_line, label="Wave Height (m)", marker="o", color="royalblue")
ax2.plot(trend_times, wind_line, label="Wind Speed (m/s)", marker="s", color="crimson")
ax2.set_title("Wave and wind forecast")
ax2.set_xlabel("Time")
ax2.set_ylabel("Measurement")
ax2.legend()
ax2.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()

st.pyplot(fig)

st.markdown("---")

# Detailed table
st.subheader("📋 Detailed fused risk data")
st.dataframe(risk_series[:trend_hours])

st.markdown("---")

st.subheader("🌐 Multi-source fusion")
st.write(
    "This system blends observations from StormGlass, NOAA, and ECMWF using a weighted average model "
    "to improve coastal decision intelligence."
)
