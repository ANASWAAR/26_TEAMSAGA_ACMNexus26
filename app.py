import datetime
import os
import matplotlib.pyplot as plt
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
import requests

# ✅ AI IMPORT (SAFE)
try:
    from ai_helper import generate_ai_response
    AI_AVAILABLE = True
except:
    AI_AVAILABLE = False

# ✅ MUST BE FIRST
st.set_page_config(page_title="Climate Intelligence System", page_icon="🌊", layout="wide")

# 🔐 Load ENV
load_dotenv()
API_KEY = os.getenv("STORMGLASS_API_KEY")
BACKEND_URL = os.getenv("RISK_API_URL", "http://localhost:8000")

if not API_KEY:
    st.error("API key missing")
    st.stop()

# 🌊 TITLE
st.title("🌊 Coastal Climate Intelligence System")

# 📌 DEFAULT LOCATION
DEFAULT_LAT = 9.9312
DEFAULT_LON = 76.2673

# 🧠 SESSION STATE
if "lat" not in st.session_state:
    st.session_state["lat"] = DEFAULT_LAT
if "lon" not in st.session_state:
    st.session_state["lon"] = DEFAULT_LON

lat = st.session_state["lat"]
lon = st.session_state["lon"]

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut

# 🌍 Fast fallback city database (NO API needed)
CITY_DB = {
    "kochi": (9.9312, 76.2673),
    "chennai": (13.0827, 80.2707),
    "mumbai": (19.0760, 72.8777),
    "goa": (15.2993, 74.1240),
    "delhi": (28.6139, 77.2090),
}

# Geolocator with timeout
geolocator = Nominatim(user_agent="coastal_app", timeout=5)

st.subheader("📍 Location Controls")

location_name = st.text_input("🔍 Search location (e.g., Kochi, Chennai)")

if location_name:
    name = location_name.lower().strip()

    # ⚡ 1. Instant local DB (FAST + RELIABLE)
    if name in CITY_DB:
        lat, lon = CITY_DB[name]
        st.session_state["lat"] = lat
        st.session_state["lon"] = lon
        st.success(f"📍 Loaded {location_name.title()} instantly")
        st.rerun()

    # 🌍 2. Try online geocoding
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
            st.warning("⚠️ Search service slow/unavailable. Try again.")

        except Exception:
            st.error("Unexpected error during search")

# 📌 SIDEBAR
with st.sidebar:
    st.header("Settings")

    lat = st.number_input("Latitude", value=st.session_state["lat"])
    lon = st.number_input("Longitude", value=st.session_state["lon"])
    profile = st.radio("User", ["Fishermen", "Residents"])
    forecast_hours = st.slider("Forecast Hours", 3, 9, 6)

    st.session_state["lat"] = lat
    st.session_state["lon"] = lon

# 📡 BACKEND CALL
@st.cache_data(ttl=120)
def fetch_backend(lat, lon, hours, user):
    try:
        res = requests.get(
            f"{BACKEND_URL}/risk",
            params={
                "lat": lat,
                "lon": lon,
                "hours": hours,
                "user_type": user
            },
            timeout=10
        )
        if res.status_code == 200:
            return res.json()
        return None
    except:
        return None

backend_data = fetch_backend(lat, lon, forecast_hours, profile)

if not backend_data:
    st.error("Backend not reachable")
    st.stop()

risk_series = backend_data["risk_series"]
forecast = backend_data["forecast"]
current = risk_series[0]

# 🗺️ MAP
st.subheader("🗺️ Coastal Risk Map")

m = folium.Map(location=[lat, lon], zoom_start=7)

color_map = {
    "SAFE": "green",
    "CAUTION": "orange",
    "DANGER": "red",
    "EXTREME": "black"
}

folium.Marker(
    [lat, lon],
    popup=f"{current['riskLabel']}"
).add_to(m)

folium.Circle(
    location=[lat, lon],
    radius=20000,
    color=color_map[current["riskLabel"]],
    fill=True,
    fill_opacity=0.4
).add_to(m)

# 🔥 REAL GRID HEATMAP
import numpy as np
grid = []
for dlat in np.linspace(-0.3, 0.3, 5):
    for dlon in np.linspace(-0.3, 0.3, 5):
        grid.append([lat + dlat, lon + dlon, current["riskScore"]])

HeatMap(grid).add_to(m)

map_data = st_folium(m, height=400, width=700)

# 📍 CLICK UPDATE
if map_data and map_data.get("last_clicked"):
    st.session_state["lat"] = map_data["last_clicked"]["lat"]
    st.session_state["lon"] = map_data["last_clicked"]["lng"]
    st.rerun()

# 🚨 ALERT
if current["riskLabel"] in ["DANGER", "EXTREME"]:
    st.error("🚨 EXTREME RISK")
elif current["riskLabel"] == "CAUTION":
    st.warning("⚠️ CAUTION")
else:
    st.success("✅ SAFE")

# 📊 METRICS
st.subheader("📊 Conditions")
col1, col2, col3 = st.columns(3)

col1.metric("Wave", f"{current['waveHeight']:.2f} m")
col2.metric("Wind", f"{current['windSpeed']:.2f} m/s")
col3.metric("Risk", current["riskLabel"])

# 🤖 AI SECTION
st.subheader("🤖 AI Coastal Advisor")

if AI_AVAILABLE:
    ai_text = generate_ai_response(current)
    st.info(ai_text)
else:
    st.warning("AI not enabled")

# 🔮 FORECAST
st.subheader("🔮 Forecast")

for item in forecast:
    st.write(f"{item['time'][11:16]} → {item['predictedLabel']} ({item['probability']}%)")

# 🧭 RECOMMENDATION
st.subheader("🧭 Recommendation")
st.info(backend_data["recommendations"][0]["action"])

# 📈 GRAPH
st.subheader("📈 Risk Trend")

fig, ax = plt.subplots()
times = [e["time"][11:16] for e in risk_series[:forecast_hours]]
scores = [e["riskScore"] for e in risk_series[:forecast_hours]]

ax.plot(times, scores, marker="o")
ax.axhspan(0.6, 1, alpha=0.2, color='red')
ax.axhspan(0.3, 0.6, alpha=0.2, color='yellow')
ax.axhspan(0, 0.3, alpha=0.2, color='green')

ax.set_ylim(0, 1)
ax.grid(True)

st.pyplot(fig)

# 📋 TABLE
st.subheader("📋 Data")
st.dataframe(risk_series[:forecast_hours])