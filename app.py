import requests
import streamlit as st
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import os

# 🔐 Load environment variables
load_dotenv()
API_KEY = os.getenv("STORMGLASS_API_KEY")

if not API_KEY:
    st.error("API key not found. Check your .env file.")
    st.stop()

# 🌍 API URL (Kochi, Kerala, India)
url = "https://api.stormglass.io/v2/weather/point?lat=9.9312&lng=76.2673&params=waveHeight,windSpeed"

headers = {
    "Authorization": API_KEY
}

# 📡 Fetch data
response = requests.get(url, headers=headers)

# ❗ Handle API errors
if response.status_code != 200:
    st.error(f"API Error: {response.status_code}")
    st.write(response.text)
    st.stop()

# ✅ Convert to JSON
json_data = response.json()

# ✅ Safely get 'hours'
data = json_data.get('hours', [])

if not data:
    st.error("No 'hours' data found in API response")
    st.write(json_data)
    st.stop()

processed_data = []

# 🔄 Process data
for entry in data:
    time = entry.get('time', 'N/A')
    wave = entry.get('waveHeight', {}).get('sg', 0)
    wind = entry.get('windSpeed', {}).get('sg', 0)

    processed_data.append({
        "time": time,
        "waveHeight": wave,
        "windSpeed": wind
    })

# 🎯 Risk logic
def get_risk(wave, wind):
    if wave > 1.5 or wind > 10:
        return "HIGH RISK", "🔴"
    elif wave > 1.0 or wind > 7:
        return "MEDIUM RISK", "🟡"
    else:
        return "LOW RISK", "🟢"

# Add risk values
for entry in processed_data:
    risk, emoji = get_risk(entry["waveHeight"], entry["windSpeed"])
    entry["risk"] = risk
    entry["emoji"] = emoji

# 📊 Limit data
short_data = processed_data[:8]

if len(short_data) < 4:
    st.error("Not enough data for prediction")
    st.stop()

current = short_data[0]
future = short_data[3]

# 🚨 Smart alerts
def smart_alert(entry):
    if entry["risk"] == "HIGH RISK":
        return "🚨 High risk of capsizing. Avoid sea travel."
    elif entry["risk"] == "MEDIUM RISK":
        return "⚠️ Moderate risk. Stay alert."
    else:
        return "✅ Safe for fishing."

# 🧭 Recommendation
def recommendation(entry):
    if entry["risk"] == "HIGH RISK":
        return "Secure boats, avoid sailing"
    elif entry["risk"] == "MEDIUM RISK":
        return "Proceed with caution"
    else:
        return "Safe to operate"

# 🌊 STREAMLIT UI
st.set_page_config(page_title="Coastal Risk Alert System", page_icon="🌊", layout="wide")

st.title("🌊 Coastal Risk Alert System")
st.markdown("**Location:** Kochi, Kerala, India")
st.markdown("---")

# Sidebar for additional info
with st.sidebar:
    st.header("ℹ️ About")
    st.write("This app provides real-time coastal risk assessment based on wave height and wind speed data.")
    st.write("Data source: Stormglass API")
    if st.button("🔄 Refresh Data"):
        st.rerun()

# 📌 Metrics (better UI)
st.subheader("📊 Current Conditions")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Wave Height (m)", f"{current['waveHeight']:.2f}")
with col2:
    st.metric("Wind Speed (m/s)", f"{current['windSpeed']:.2f}")
with col3:
    st.metric("Risk Level", f"{current['emoji']} {current['risk']}")

st.markdown("---")

# Current Status and Prediction
col1, col2 = st.columns(2)
with col1:
    st.subheader("🏠 Current Status")
    st.write(f"**Time:** {current['time']}")
    st.write(f"**Wave Height:** {current['waveHeight']:.2f} m")
    st.write(f"**Wind Speed:** {current['windSpeed']:.2f} m/s")
    st.write(f"**Risk:** {current['emoji']} {current['risk']}")

with col2:
    st.subheader("🔮 Prediction (Next 3 Hours)")
    st.write(f"**Time:** {future['time']}")
    st.write(f"**Wave Height:** {future['waveHeight']:.2f} m")
    st.write(f"**Wind Speed:** {future['windSpeed']:.2f} m/s")
    st.write(f"**Risk:** {future['emoji']} {future['risk']}")

st.markdown("---")

# Alert
st.subheader("🚨 Alert")
if current["risk"] == "HIGH RISK":
    st.error(smart_alert(current))
elif current["risk"] == "MEDIUM RISK":
    st.warning(smart_alert(current))
else:
    st.success(smart_alert(current))

st.markdown("---")

# 📈 Graph
st.subheader("📈 Trends (Next 8 Hours)")
fig, ax = plt.subplots(figsize=(10, 5))
times = [e['time'][11:16] for e in short_data]  # Show time only
waves = [e['waveHeight'] for e in short_data]
winds = [e['windSpeed'] for e in short_data]

ax.plot(times, waves, label="Wave Height (m)", marker='o', color='blue')
ax.plot(times, winds, label="Wind Speed (m/s)", marker='s', color='red')
ax.set_xlabel("Time (HH:MM)")
ax.set_ylabel("Value")
ax.legend()
ax.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()

st.pyplot(fig)

st.markdown("---")

# Recommendation
st.subheader("🧭 Recommendation")
st.info(recommendation(current))

# Data Table
st.subheader("📋 Detailed Data")
st.dataframe(short_data)