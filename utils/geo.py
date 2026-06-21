"""
WanderHUB Backend — Geo Utilities (Haversine distance)
"""

import math


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth (km)."""
    R = 6371.0  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def estimate_travel_minutes(distance_km: float, mode: str = "car") -> int:
    """Estimate travel time in minutes based on distance and mode.

    Assumes average speeds in HCMC urban traffic:
    - car/ride: ~20 km/h during peak, ~30 km/h off-peak → avg 25 km/h
    - walk: ~4.5 km/h
    - motorbike: ~22 km/h
    """
    speeds = {
        "car": 25.0,
        "ride": 25.0,
        "walk": 4.5,
        "motorbike": 22.0,
    }
    speed = speeds.get(mode, 25.0)
    minutes = (distance_km / speed) * 60
    return max(1, round(minutes))
