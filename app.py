import requests

# 🔑 Replace with your actual API URL + key
url = "https://api.stormglass.io/v2/weather/point?lat=9.9312&lng=76.2673&params=waveHeight,windSpeed"
headers = {
    "Authorization": "439f6cb2-29e1-11f1-beac-0242ac120004-439f6da2-29e1-11f1-beac-0242ac120004"
}

# 📡 Fetch data
response = requests.get(url, headers=headers)

# ✅ Convert response to JSON
json_data = response.json()

# ✅ Extract hours data
data = json_data['hours']

processed_data = []

# 🔄 Process data
for entry in data:
    time = entry['time']
    wave = entry.get('waveHeight', {}).get('sg', 0)
    wind = entry.get('windSpeed', {}).get('sg', 0)

    processed_data.append({
        "time": time,
        "waveHeight": wave,
        "windSpeed": wind
    })

# 🖨️ Print sample output
print(processed_data[:5])

def get_risk(wave, wind):
    if wave > 1.5 or wind > 10:
        return "HIGH RISK"
    elif wave > 1.0 or wind > 7:
        return "MEDIUM RISK"
    else:
        return "LOW RISK"

for entry in processed_data:
    entry["risk"] = get_risk(entry["waveHeight"], entry["windSpeed"])

print(processed_data[:10])

short_data = processed_data[:8]

current = short_data[0]
future = short_data[3]

print("🌊 CURRENT STATUS")
print(current)

print("\n⏳ NEXT 3 HOURS PREDICTION")
print(future)

def smart_alert(entry):
    if entry["risk"] == "HIGH RISK":
        return "🚨 High risk of capsizing. Avoid sea travel."
    elif entry["risk"] == "MEDIUM RISK":
        return "⚠️ Moderate risk. Stay alert."
    else:
        return "✅ Safe for fishing."

print(smart_alert(current))
print(smart_alert(future))

import streamlit as st

st.title("🌊 Coastal Risk Alert System")

st.subheader("Current Status")
st.write(current)

st.subheader("Prediction (Next Hours)")
st.write(future)

st.subheader("Alert")
st.success(smart_alert(current))

import matplotlib.pyplot as plt

times = [e['time'][:13] for e in short_data]
waves = [e['waveHeight'] for e in short_data]
winds = [e['windSpeed'] for e in short_data]

plt.plot(times, waves, label="Wave Height")
plt.plot(times, winds, label="Wind Speed")
plt.legend()
plt.xticks(rotation=45)

st.pyplot(plt)

def recommendation(entry):
    if entry["risk"] == "HIGH RISK":
        return "Secure boats, avoid sailing"
    elif entry["risk"] == "MEDIUM RISK":
        return "Proceed with caution"
    else:
        return "Safe to operate"

st.warning(recommendation(current))