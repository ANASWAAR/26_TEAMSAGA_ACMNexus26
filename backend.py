import asyncio
import datetime
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from data_fetch import prepare_fused_data
from risk_analysis import prepare_risk_series, forecast_risk, generate_recommendation, format_status

load_dotenv()
API_KEY = os.getenv("STORMGLASS_API_KEY")

app = FastAPI(title="Coastal Risk API", version="1.0.0")

# In-memory cache that gets refreshed every 2 minutes
REALTIME_CACHE = {
    "updated_at": None,
    "payload": None,
    "lat": 9.9312,
    "lon": 76.2673,
    "hours": 8,
    "user_type": "Fishermen",
}

REFRESH_INTERVAL_SECONDS = 120


async def refresh_risk_data_loop() -> None:
    """Continuously refresh fused risk data every REFRESH_INTERVAL_SECONDS."""
    while True:
        try:
            location = REALTIME_CACHE
            fused_payload = prepare_fused_data(API_KEY, location["lat"], location["lon"], location["hours"])
            fused = fused_payload.get("fused", [])

            if fused:
                risk_series = prepare_risk_series(fused)
                forecast = forecast_risk(risk_series, horizon=min(6, len(risk_series) - 1))

                recommendations = []
                for item in risk_series[:3]:
                    recommendations.append(
                        {
                            "time": item["time"],
                            "riskLabel": item["riskLabel"],
                            "action": generate_recommendation(
                                item["riskLabel"], location["user_type"], item["spike"], int(item["riskScore"] * 100)
                            ),
                        }
                    )

                REALTIME_CACHE.update(
                    {
                        "updated_at": datetime.datetime.utcnow(),
                        "payload": {
                            "location": {"lat": location["lat"], "lon": location["lon"], "sources": fused_payload.get("sources", [])},
                            "status": format_status(data_age_mins=0.0, lat=location["lat"], lon=location["lon"]),
                            "risk_series": risk_series,
                            "forecast": forecast,
                            "recommendations": recommendations,
                        },
                    }
                )

        except Exception:
            # Keep last valid cache if refresh fails.
            pass

        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


@app.on_event("startup")
async def startup_event():
    if not API_KEY:
        return

    # start the background refresh loop
    app.state.refresh_task = asyncio.create_task(refresh_risk_data_loop())


@app.on_event("shutdown")
async def shutdown_event():
    refresh_task = getattr(app.state, "refresh_task", None)
    if refresh_task:
        refresh_task.cancel()


class RiskResponse(BaseModel):
    location: dict
    status: str
    risk_series: list
    forecast: list
    recommendations: list


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Coastal Risk Backend is running"}


@app.get("/risk", response_model=RiskResponse)
def risk_analysis(
    lat: float = Query(9.9312, description="Latitude"),
    lon: float = Query(76.2673, description="Longitude"),
    hours: int = Query(8, ge=4, le=24, description="Hours of forecast"),
    user_type: Optional[str] = Query("Fishermen", description="User type for recommendation"),
    force_refresh: bool = Query(False, description="Force an immediate backend refresh"),
):
    if not API_KEY:
        raise HTTPException(500, detail="Stormglass API key is missing in environment")

    # if query location is same as cache, return cached payload for low latency
    cache_age = None
    if REALTIME_CACHE["payload"]:
        dt = REALTIME_CACHE["updated_at"]
        cache_age = (datetime.datetime.utcnow() - dt).total_seconds() if dt else None

    same_location = lat == REALTIME_CACHE["lat"] and lon == REALTIME_CACHE["lon"] and hours == REALTIME_CACHE["hours"]

    if force_refresh or not same_location or not REALTIME_CACHE["payload"] or (cache_age is not None and cache_age > REFRESH_INTERVAL_SECONDS + 60):
        # direct sync update when needed (e.g., 2-minute real-time guarantee)
        fused_payload = prepare_fused_data(API_KEY, lat, lon, hours)
        fused = fused_payload.get("fused", [])

        if not fused:
            raise HTTPException(502, detail="Failed to fetch fused data from upstream sources")

        risk_series = prepare_risk_series(fused)
        forecast = forecast_risk(risk_series, horizon=min(6, len(risk_series) - 1))

        recommendations = []
        for item in risk_series[:3]:
            recommendations.append(
                {
                    "time": item["time"],
                    "riskLabel": item["riskLabel"],
                    "action": generate_recommendation(item["riskLabel"], user_type, item["spike"], int(item["riskScore"] * 100)),
                }
            )

        status = format_status(data_age_mins=0.0, lat=lat, lon=lon) if risk_series else "Offline"

        # update on-demand cache when same location selected so loop can catch up in background too
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

    # return cached response
    return REALTIME_CACHE["payload"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)
