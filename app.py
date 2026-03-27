import datetime
import os
import matplotlib.pyplot as plt
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
from dotenv import load_dotenv
from geopy.geocoders import Nominatim

# Safe geolocation
try:
    from streamlit_js_eval import get_geolocation
    GEO_AVAILABLE = True
except:
    GEO_AVAILABLE = False

from alert_system import format_status, simulate_delivery
from data_fetch import prepare_fused_data
from risk_analysis import forecast_risk, generate_recommendation, prepare_risk_series

# ✅ MUST BE FIRST
st.set_page_config(page_title="Climate Intelligence System", page_icon="🌊", layout="wide")

# 🔐 Load API
load_dotenv()
API_KEY = os.getenv("STORMGLASS_API_KEY")

if not API_KEY:
    st.error("API key not found")
    st.stop()

# 🌊 TITLE
st.title("🌊 Coastal Climate Intelligence System")

# 📌 DEFAULT LOCATION
DEFAULT_LAT = 9.9312
DEFAULT_LON = 76.2673

# 🧠 SESSION STATE (IMPORTANT)
if "lat" not in st.session_state:
    st.session_state["lat"] = DEFAULT_LAT
if "lon" not in st.session_state:
    st.session_state["lon"] = DEFAULT_LON

lat = st.session_state["lat"]
lon = st.session_state["lon"]

# 📍 LOCATION CONTROLS
st.subheader("📍 Location Controls")

# 🔍 SEARCH
geolocator = Nominatim(user_agent="coastal_app")
location_name = st.text_input("🔍 Search location (e.g., Kochi, Chennai)")

if location_name:
    location = geolocator.geocode(location_name)
    if location:
        st.session_state["lat"] = location.latitude
        st.session_state["lon"] = location.longitude
        lat, lon = location.latitude, location.longitude
        st.success(f"📍 {location.address}")
    else:
        st.error("Location not found")

# 📍 CURRENT LOCATION
if GEO_AVAILABLE:
    if st.button("📍 Use My Current Location"):
        loc = get_geolocation()
        if loc:
            st.session_state["lat"] = loc["coords"]["latitude"]
            st.session_state["lon"] = loc["coords"]["longitude"]
            lat, lon = st.session_state["lat"], st.session_state["lon"]
            st.success(f"Using: {lat:.4f}, {lon:.4f}")

# 📌 SIDEBAR
with st.sidebar:
    st.header("Settings")
    lat = st.number_input("Latitude", value=st.session_state["lat"])
    lon = st.number_input("Longitude", value=st.session_state["lon"])
    profile = st.radio("User profile", ["Fishermen", "Residents"])
    forecast_hours = st.slider("Forecast hours", 3, 9, 6)

    st.session_state["lat"] = lat
    st.session_state["lon"] = lon

# 📡 DATA
@st.cache_data(ttl=300)
def load_weather_data(api_key, lat, lon, hours):
    return prepare_fused_data(api_key, lat, lon, hours)

weather_bundle = load_weather_data(API_KEY, lat, lon, forecast_hours)
fused_data = weather_bundle.get("fused", [])

if not fused_data:
    st.error("Failed to load data")
    st.stop()

risk_series = prepare_risk_series(fused_data)
current = risk_series[0]
forecast = forecast_risk(risk_series, forecast_hours)

# 🗺️ MAP
st.subheader("🗺️ Coastal Risk Map")

m = folium.Map(location=[lat, lon], zoom_start=7)

color_map = {
    "SAFE": "green",
    "CAUTION": "orange",
    "DANGER": "red",
    "EXTREME": "black"
}

# Marker
folium.Marker(
    [lat, lon],
    popup=f"Risk: {current['riskLabel']}"
).add_to(m)

# Danger Zone
folium.Circle(
    location=[lat, lon],
    radius=20000,
    color=color_map[current["riskLabel"]],
    fill=True,
    fill_opacity=0.4
).add_to(m)

# Heatmap
heat_data = [[lat, lon, e["riskScore"]] for e in risk_series[:6]]
HeatMap(heat_data).add_to(m)

map_data = st_folium(m, height=400, width=700)

# 📌 CLICK UPDATE
if map_data and map_data.get("last_clicked"):
    st.session_state["lat"] = map_data["last_clicked"]["lat"]
    st.session_state["lon"] = map_data["last_clicked"]["lng"]
    st.rerun()

# 🚨 ALERT
if current["riskLabel"] in ["DANGER", "EXTREME"]:
    st.error("🚨 EXTREME RISK: Avoid sea travel")
elif current["riskLabel"] == "CAUTION":
    st.warning("⚠️ Moderate risk")
else:
    st.success("✅ Safe")

# 📊 METRICS
st.subheader("📊 Current Conditions")
col1, col2, col3 = st.columns(3)

col1.metric("Wave Height", f"{current['waveHeight']:.2f} m")
col2.metric("Wind Speed", f"{current['windSpeed']:.2f} m/s")
col3.metric("Risk", f"{current['riskEmoji']} {current['riskLabel']}")

# 🔮 FORECAST
st.subheader("🔮 Forecast")
for item in forecast:
    st.write(f"{item['time'][11:16]} → {item['predictedLabel']} ({item['probability']}%)")

# 🧭 RECOMMENDATION
st.subheader("🧭 Recommendation")
rec = generate_recommendation(
    current["riskLabel"],
    profile,
    current["spike"],
    forecast[0]["probability"] if forecast else 0,
)
st.info(rec)

# 📱 ALERT LOGS
st.subheader("📱 Alerts")
st.code(simulate_delivery(rec, "SMS"))

# 📈 GRAPH
st.subheader("📈 Risk Trend")

fig, ax = plt.subplots()
times = [e["time"][11:16] for e in risk_series[:forecast_hours]]
scores = [e["riskScore"] for e in risk_series[:forecast_hours]]

ax.plot(times, scores, marker="o")
ax.set_ylim(0, 1)
ax.grid(True)

st.pyplot(fig)

# 📋 TABLE
st.subheader("📋 Data")
st.dataframe(risk_series[:forecast_hours])

# 🧭 LEGEND
st.markdown("""
### 🧭 Risk Legend
- 🟢 SAFE  
- 🟡 CAUTION  
- 🔴 DANGER  
- ⚫ EXTREME  
""")