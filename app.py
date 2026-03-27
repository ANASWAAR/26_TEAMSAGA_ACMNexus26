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

# 🌍 API URL
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
        return "HIGH RISK"
    elif wave > 1.0 or wind > 7:
        return "MEDIUM RISK"
    else:
        return "LOW RISK"

# Add risk values
for entry in processed_data:
    entry["risk"] = get_risk(entry["waveHeight"], entry["windSpeed"])

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
st.title("🌊 Coastal Risk Alert System")

# 📌 Metrics (better UI)
col1, col2 = st.columns(2)
col1.metric("Wave Height (m)", f"{current['waveHeight']}")
col2.metric("Wind Speed (m/s)", f"{current['windSpeed']}")

st.subheader("Current Status")
st.write(current)

st.subheader("Prediction (Next 3 Hours)")
st.write(future)

st.subheader("Alert")
st.success(smart_alert(current))

# 📈 Graph
times = [e['time'][:13] for e in short_data]
waves = [e['waveHeight'] for e in short_data]
winds = [e['windSpeed'] for e in short_data]

plt.figure()
plt.plot(times, waves, label="Wave Height")
plt.plot(times, winds, label="Wind Speed")
plt.legend()
plt.xticks(rotation=45)

st.pyplot(plt)

st.subheader("Recommendation")
st.warning(recommendation(current))