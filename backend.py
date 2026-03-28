import datetime
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from dotenv import load_dotenv
from geopy.distance import geodesic

# ---------------- ENV ----------------
load_dotenv()
API_KEY = os.getenv("STORMGLASS_API_KEY")

# ✅ DEFINE APP FIRST (IMPORTANT)
app = FastAPI()

# ---------------- HEALTH ROUTE ----------------
@app.get("/health")
def health_check():
    return {"status": "ok"}

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

# ---------------- RESPONSE MODEL ----------------
class RiskResponse(BaseModel):
    location: dict
    status: str
    risk_series: list
    forecast: list
    recommendations: list

# ---------------- CACHE ----------------
REALTIME_CACHE = {
    "updated_at": None,
    "payload": None,
    "lat": 9.9312,
    "lon": 76.2673,
    "hours": 8,
    "user_type": "Fishermen",
}

REFRESH_INTERVAL_SECONDS = 120

# ---------------- IMPORT LOGIC ----------------
from data_fetch import prepare_fused_data
from risk_analysis import prepare_risk_series, forecast_risk, generate_recommendation, format_status

# ---------------- MAIN API ----------------
@app.get("/risk", response_model=RiskResponse)
def risk_analysis(
    lat: float = Query(9.9312),
    lon: float = Query(76.2673),
    hours: int = Query(8, ge=4, le=24),
    user_type: Optional[str] = Query("Fishermen"),
    force_refresh: bool = Query(False),
):
    if not API_KEY:
        raise HTTPException(500, detail="Stormglass API key missing")

    # 🌊 Coastal Check
    near_coast = is_near_coast(lat, lon)

    if not near_coast:
        return {
            "location": {"lat": lat, "lon": lon, "sources": []},
            "status": "Inland Region - No Coastal Risk",
            "risk_series": [
                {
                    "time": datetime.datetime.utcnow().isoformat(),
                    "riskLabel": "SAFE",
                    "riskScore": 0.1,
                    "waveHeight": 0,
                    "windSpeed": 0,
                    "spike": False
                }
            ],
            "forecast": [
                {
                    "time": datetime.datetime.utcnow().isoformat(),
                    "predictedLabel": "SAFE",
                    "probability": 100
                }
            ],
            "recommendations": [
                {
                    "time": "Now",
                    "riskLabel": "SAFE",
                    "action": "This is an inland region. Coastal wave risk is not applicable."
                }
            ]
        }

    # ---------------- CACHE LOGIC ----------------
    cache_age = None
    if REALTIME_CACHE["payload"]:
        dt = REALTIME_CACHE["updated_at"]
        cache_age = (datetime.datetime.utcnow() - dt).total_seconds() if dt else None

    same_location = (
        lat == REALTIME_CACHE["lat"] and
        lon == REALTIME_CACHE["lon"] and
        hours == REALTIME_CACHE["hours"]
    )

    if force_refresh or not same_location or not REALTIME_CACHE["payload"] or (
        cache_age is not None and cache_age > REFRESH_INTERVAL_SECONDS + 60
    ):

        fused_payload = prepare_fused_data(API_KEY, lat, lon, hours)
        fused = fused_payload.get("fused", [])

        if not fused:
            raise HTTPException(502, detail="Failed to fetch data")

        risk_series = prepare_risk_series(fused)
        forecast = forecast_risk(risk_series, horizon=min(6, len(risk_series) - 1))

        recommendations = []
        for item in risk_series[:3]:
            recommendations.append({
                "time": item["time"],
                "riskLabel": item["riskLabel"],
                "action": generate_recommendation(
                    item["riskLabel"], user_type, item["spike"], int(item["riskScore"] * 100)
                ),
            })

        status = format_status(0.0, lat, lon)

        if same_location:
            REALTIME_CACHE.update({
                "lat": lat,
                "lon": lon,
                "hours": hours,
                "user_type": user_type,
                "updated_at": datetime.datetime.utcnow(),
                "payload": {
                    "location": {"lat": lat, "lon": lon, "sources": fused_payload.get("sources", [])},
                    "status": status,
                    "risk_series": risk_series,
                    "forecast": forecast,
                    "recommendations": recommendations,
                },
            })

        return {
            "location": {"lat": lat, "lon": lon, "sources": fused_payload.get("sources", [])},
            "status": status,
            "risk_series": risk_series,
            "forecast": forecast,
            "recommendations": recommendations,
        }

    return REALTIME_CACHE["payload"]