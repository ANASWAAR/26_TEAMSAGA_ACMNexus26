import os
import requests
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut

# Optional AI
try:
    from ai_helper import generate_ai_response
    AI_AVAILABLE = True
except:
    AI_AVAILABLE = False

# SMS Simulation
from sms_alert import send_sms_alert

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Climate Intelligence System", page_icon="🌊", layout="wide")

load_dotenv()
BACKEND_URL = os.getenv("RISK_API_URL", "http://127.0.0.1:8000")

# ---------------- DEFAULT STATE ----------------
DEFAULT_LAT = 9.9312
DEFAULT_LON = 76.2673

if "lat" not in st.session_state:
    st.session_state["lat"] = DEFAULT_LAT
if "lon" not in st.session_state:
    st.session_state["lon"] = DEFAULT_LON

lat = st.session_state["lat"]
lon = st.session_state["lon"]

# ---------------- TITLE ----------------
st.title("🌊 Coastal Climate Intelligence System")

# ---------------- SEARCH ----------------
st.subheader("📍 Location Controls")

CITY_DB = {
    "kochi": (9.9312, 76.2673),
    "chennai": (13.0827, 80.2707),
    "mumbai": (19.0760, 72.8777),
    "goa": (15.2993, 74.1240),
}

geolocator = Nominatim(user_agent="coastal_app", timeout=5)

location_name = st.text_input("🔍 Search location")

if location_name:
    name = location_name.lower().strip()

    if name in CITY_DB:
        st.session_state["lat"], st.session_state["lon"] = CITY_DB[name]
        st.success(f"📍 Loaded {location_name.title()}")
        st.rerun()
    else:
        try:
            location = geolocator.geocode(location_name)
            if location:
                st.session_state["lat"] = location.latitude
                st.session_state["lon"] = location.longitude
                st.success(f"📍 {location.address}")
                st.rerun()
            else:
                st.warning("Location not found")
        except (GeocoderUnavailable, GeocoderTimedOut):
            st.warning("⚠️ Search service unavailable")

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("Settings")
    lat = st.number_input("Latitude", value=st.session_state["lat"])
    lon = st.number_input("Longitude", value=st.session_state["lon"])
    profile = st.radio("User", ["Fishermen", "Residents"])
    forecast_hours = st.slider("Forecast Hours", 3, 9, 6)

    st.session_state["lat"] = lat
    st.session_state["lon"] = lon

# ---------------- BACKEND ----------------
@st.cache_data(ttl=120)
def fetch_data(lat, lon, hours, user):
    try:
        res = requests.get(
            f"{BACKEND_URL}/risk",
            params={"lat": lat, "lon": lon, "hours": hours, "user_type": user},
            timeout=10
        )
        if res.status_code == 200:
            return res.json()
        return None
    except:
        return None

data = fetch_data(lat, lon, forecast_hours, profile)

if not data:
    st.error("Backend not reachable")
    st.stop()

risk_series = data["risk_series"]
forecast = data["forecast"]
current = risk_series[0]

# ---------------- MAP ----------------
st.subheader("🗺️ Coastal Risk Map")

m = folium.Map(location=[lat, lon], zoom_start=7)

color_map = {
    "SAFE": "green",
    "CAUTION": "orange",
    "DANGER": "red",
    "EXTREME": "black"
}

folium.Marker([lat, lon], popup=current["riskLabel"]).add_to(m)

folium.Circle(
    [lat, lon],
    radius=20000,
    color=color_map[current["riskLabel"]],
    fill=True,
    fill_opacity=0.4
).add_to(m)

# Heatmap (grid)
grid = []
for dlat in np.linspace(-0.3, 0.3, 5):
    for dlon in np.linspace(-0.3, 0.3, 5):
        grid.append([lat + dlat, lon + dlon, current["riskScore"]])

HeatMap(grid).add_to(m)

map_data = st_folium(m, height=400)

if map_data and map_data.get("last_clicked"):
    st.session_state["lat"] = map_data["last_clicked"]["lat"]
    st.session_state["lon"] = map_data["last_clicked"]["lng"]
    st.rerun()

# ---------------- ALERT ----------------
st.subheader("🚨 Risk Status")

if current["riskLabel"] in ["DANGER", "EXTREME"]:
    st.error("🚨 HIGH RISK DETECTED")

    msg = f"⚠️ {current['riskLabel']} conditions. Avoid sea travel."

    result = send_sms_alert("+911234567890", msg)
    st.success(result)

elif current["riskLabel"] == "CAUTION":
    st.warning("⚠️ Moderate risk")
else:
    st.success("✅ Safe")

# ---------------- METRICS ----------------
st.subheader("📊 Conditions")

col1, col2, col3 = st.columns(3)
col1.metric("Wave Height", f"{current['waveHeight']:.2f} m")
col2.metric("Wind Speed", f"{current['windSpeed']:.2f} m/s")
col3.metric("Risk", current["riskLabel"])

# ---------------- AI ----------------
# ---------------- AI ----------------
st.subheader("🤖 AI Advisor")

from ai_helper import generate_ai_response

ai_response = generate_ai_response(current, profile)
st.info(ai_response)

# ---------------- FORECAST ----------------
st.subheader("🔮 Forecast")

for item in forecast:
    st.write(f"{item['time'][11:16]} → {item['predictedLabel']} ({item['probability']}%)")

# ---------------- RECOMMENDATION ----------------
st.subheader("🧭 Recommendation")
st.info(data["recommendations"][0]["action"])

# ---------------- MANUAL ALERT ----------------
st.subheader("📱 Manual Alert")

if st.button("Send Alert"):
    msg = f"⚠️ Risk: {current['riskLabel']}"
    st.success(send_sms_alert("+911234567890", msg))

# ---------------- GRAPH ----------------
st.subheader("📈 Risk Trend")

fig, ax = plt.subplots()

times = [e["time"][11:16] for e in risk_series[:forecast_hours]]
scores = [e["riskScore"] for e in risk_series[:forecast_hours]]

ax.plot(times, scores, marker="o")
ax.set_ylim(0, 1)
ax.grid(True)

st.pyplot(fig)

# ---------------- TABLE ----------------
st.subheader("📋 Data")
st.dataframe(risk_series[:forecast_hours])