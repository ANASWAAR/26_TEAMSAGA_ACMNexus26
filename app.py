import os
import time
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
from geopy.distance import geodesic

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Climate Intelligence System", page_icon="🌊", layout="wide")

load_dotenv()
BACKEND_URL = os.getenv("RISK_API_URL", "http://127.0.0.1:8000")

# ---------------- COAST CHECK ----------------
COAST_POINTS = [
    (9.9312, 76.2673),
    (8.5241, 76.9366),
    (11.2588, 75.7804)
]

def is_near_coast(lat, lon, threshold_km=50):
    user_location = (lat, lon)
    for coast in COAST_POINTS:
        if geodesic(user_location, coast).km <= threshold_km:
            return True
    return False

# ---------------- AI ----------------
try:
    from ai_helper import generate_ai_response
    AI_AVAILABLE = True
except:
    AI_AVAILABLE = False

# ---------------- SMS ----------------
try:
    from sms_alert import send_sms_alert
    SMS_AVAILABLE = True
except:
    SMS_AVAILABLE = False

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

# ✅ CACHED GEOCODING (FIXED)
@st.cache_data(ttl=3600)
def get_location(name):
    time.sleep(1)  # prevent rapid calls
    try:
        return geolocator.geocode(name)
    except:
        return None

location_name = st.text_input("🔍 Search location")

# ✅ BUTTON-BASED SEARCH (prevents spam)
if location_name and st.button("Search"):
    name = location_name.lower().strip()

    if name in CITY_DB:
        st.session_state["lat"], st.session_state["lon"] = CITY_DB[name]
        st.success(f"📍 Loaded {location_name.title()}")
        st.rerun()
    else:
        try:
            location = get_location(location_name)
            if location:
                st.session_state["lat"] = location.latitude
                st.session_state["lon"] = location.longitude
                st.success(f"📍 {location.address}")
                st.rerun()
            else:
                st.warning("Location not found")
        except (GeocoderUnavailable, GeocoderTimedOut):
            st.warning("⚠️ Search service unavailable")
        except Exception:
            st.error("⚠️ Too many requests. Please wait and try again.")

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
            timeout=20
        )

        if res.status_code == 200:
            return res.json()
        else:
            st.error(f"Backend error: {res.status_code}")
            return None

    except Exception as e:
        st.error(f"Connection error: {e}")
        return None

data = fetch_data(lat, lon, forecast_hours, profile)

# ---------------- COAST FILTER ----------------
near_coast = is_near_coast(lat, lon)

if not near_coast:
    st.warning("🌍 Inland Region Detected")

    st.subheader("📊 Conditions")
    col1, col2, col3 = st.columns(3)
    col1.metric("Wave Height", "N/A")
    col2.metric("Wind Speed", "N/A")
    col3.metric("Risk", "LOW")

    st.subheader("🧭 Recommendation")
    st.info("This location is inland. Coastal wave risk is not applicable.")

    st.stop()

# ---------------- DATA CHECK ----------------
if not data or not data.get("risk_series"):
    st.error("No data received from backend")
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
st.subheader("🤖 AI Advisor")

if AI_AVAILABLE:
    ai_response = generate_ai_response(current, profile)
    st.info(ai_response)
else:
    st.info("AI module not available")

# ---------------- FORECAST ----------------
st.subheader("🔮 Forecast")

for item in forecast:
    st.write(f"{item['time'][11:16]} → {item['predictedLabel']} ({item['probability']}%)")

# ---------------- RECOMMENDATION ----------------
st.subheader("🧭 Recommendation")
st.info(data["recommendations"][0]["action"])

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