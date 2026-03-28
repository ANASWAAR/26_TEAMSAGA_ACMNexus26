# ai_helper.py

def generate_ai_response(current, user_type="Fishermen"):
    wave = current["waveHeight"]
    wind = current["windSpeed"]
    risk = current["riskLabel"]
    spike = current.get("spike", 0)

    # ---------------- BASE MESSAGE ----------------
    base = f"""
🌊 Coastal Risk Analysis

• Wave Height: {wave:.2f} m  
• Wind Speed: {wind:.2f} m/s  
• Risk Level: {risk}
"""

    # ---------------- RISK LOGIC ----------------
    if risk == "EXTREME":
        advice = "🚨 Extreme danger. Avoid all coastal and sea activity immediately."
    elif risk == "DANGER":
        advice = "⚠️ Dangerous conditions. Do NOT go to sea."
    elif risk == "CAUTION":
        advice = "⚠️ Moderate risk. Stay alert and monitor conditions."
    else:
        advice = "✅ Safe conditions. Normal activities can continue."

    # ---------------- USER-SPECIFIC ----------------
    if user_type == "Fishermen":
        user_advice = "👨‍✈️ Fishermen: Delay trips and secure boats."
    else:
        user_advice = "🏠 Residents: Stay indoors near coastal areas if conditions worsen."

    # ---------------- SPIKE DETECTION ----------------
    spike_msg = ""
    if spike > 0.3:
        spike_msg = "⚡ Sudden increase in risk detected. Conditions may worsen quickly."

    # ---------------- FINAL RESPONSE ----------------
    response = f"""
{base}

🧠 AI Recommendation:
{advice}

{user_advice}

{spike_msg}
"""

    return response