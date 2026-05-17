"""
VitalGuard v2 — Location Intelligence Service
Fetches REAL nearby hospitals using OpenStreetMap Overpass API.
Falls back to static DB if API is unavailable.
"""

import math
import logging
import httpx
from typing import Any, List, Dict, Optional, Tuple

logger = logging.getLogger("vitalguard.location")

# ── Cache to avoid spamming Overpass API ──────────────────────────
_cache: Dict[str, List[Dict]] = {}

DEMO_OR_PLACEHOLDER_COORDS = {
    (0.0, 0.0),
    (17.385, 78.487),
    (17.412, 78.435),
    (17.362, 78.475),
    (28.6139, 77.209),
    (28.62, 77.215),
    (28.61, 77.205),
    (28.625, 77.22),
    (28.618, 77.212),
}


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        converted = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(converted):
        return None
    return converted


def _decimal_places(value: Any) -> int:
    text = str(value)
    if "e" in text.lower():
        return 6
    if "." not in text:
        return 0
    return len(text.rstrip("0").split(".")[1])


def get_alert_safe_coordinates(lat: Any, lng: Any) -> Optional[Tuple[float, float]]:
    """
    Return coordinates only when they are safe to send in emergency messages.
    Demo seed/default coords are useful for maps, but must not be mistaken for
    a patient's live GPS location in Twilio alerts.
    """
    lat_float = _to_float(lat)
    lng_float = _to_float(lng)
    if lat_float is None or lng_float is None:
        return None
    if not (-90 <= lat_float <= 90 and -180 <= lng_float <= 180):
        return None
    if (round(lat_float, 6), round(lng_float, 6)) in DEMO_OR_PLACEHOLDER_COORDS:
        return None
    if _decimal_places(lat) < 4 or _decimal_places(lng) < 4:
        return None
    return lat_float, lng_float


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great circle distance in km between two points."""
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def _round_coords(lat: float, lng: float, precision: int = 2) -> str:
    """Round coords to cache key — avoids re-fetching for tiny GPS drift."""
    return f"{round(lat, precision)},{round(lng, precision)}"


def fetch_real_hospitals(lat: float, lng: float, radius_m: int = 10000, limit: Optional[int] = None) -> List[Dict]:
    """
    Fetch REAL hospitals near a location using OpenStreetMap Overpass API.
    Returns hospitals with name, lat, lng, distance_km.
    Caches results per rounded coordinate to avoid API spam.
    """
    cache_key = _round_coords(lat, lng)
    if cache_key in _cache:
        return _cache[cache_key][:limit]

    query = f"""
    [out:json][timeout:10];
    (
      node["amenity"="hospital"](around:{radius_m},{lat},{lng});
      way["amenity"="hospital"](around:{radius_m},{lat},{lng});
    );
    out center body;
    """

    OVERPASS_URLS = [
        "https://lz4.overpass-api.de/api/interpreter",
        "https://z.overpass-api.de/api/interpreter",
        "https://overpass-api.de/api/interpreter",
    ]

    resp = None
    for url in OVERPASS_URLS:
        try:
            resp = httpx.post(url, data={"data": query}, timeout=12.0)
            resp.raise_for_status()
            break
        except Exception:
            continue

    if resp is None:
        logger.warning("All Overpass mirrors failed")
        return []

    try:
        data = resp.json()

        hospitals = []
        seen_names = set()

        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name", tags.get("name:en", ""))
            if not name or name in seen_names:
                continue
            seen_names.add(name)

            # Get coordinates (node has lat/lng directly, way has center)
            h_lat = element.get("lat")
            if h_lat is None:
                h_lat = element.get("center", {}).get("lat")
            h_lng = element.get("lon")
            if h_lng is None:
                h_lng = element.get("center", {}).get("lon")
            if h_lat is None or h_lng is None:
                continue

            dist = haversine_distance(lat, lng, h_lat, h_lng)

            hospitals.append({
                "name": name,
                "lat": h_lat,
                "lng": h_lng,
                "specialization": tags.get("healthcare:speciality", tags.get("healthcare", "Hospital")),
                "phone": tags.get("phone", tags.get("contact:phone", "")),
                "distance_km": round(dist, 2),
            })

        hospitals.sort(key=lambda x: x["distance_km"])

        # Cache
        _cache[cache_key] = hospitals
        logger.info(f"Fetched {len(hospitals)} real hospitals near ({lat}, {lng})")
        return hospitals[:limit]

    except Exception as e:
        logger.warning(f"Overpass API failed: {e} — using fallback")
        return []


# ── Static Fallback (if Overpass fails) ───────────────────────────

FALLBACK_HOSPITALS = [
    {"name": "Apollo Hospitals", "lat": 17.4121, "lng": 78.4347,
     "specialization": "Multi-specialty", "phone": "+91-40-23607777"},
    {"name": "KIMS Hospital", "lat": 17.4156, "lng": 78.4525,
     "specialization": "Cardiac Center", "phone": "+91-40-44885000"},
    {"name": "Yashoda Hospitals", "lat": 17.4065, "lng": 78.4728,
     "specialization": "Emergency Care", "phone": "+91-40-45678999"},
]


def get_nearest_hospitals(lat: float, lng: float, limit: Optional[int] = None) -> List[Dict]:
    """
    Find nearest hospitals — tries real Overpass API first,
    falls back to static list.
    """
    if lat is None or lng is None:
        return []

    # Try real hospitals first
    real = fetch_real_hospitals(lat, lng, radius_m=10000, limit=limit)
    if real:
        return real

    # Fallback
    results = []
    for hospital in FALLBACK_HOSPITALS:
        dist = haversine_distance(lat, lng, hospital["lat"], hospital["lng"])
        results.append({**hospital, "distance_km": round(dist, 2)})
    results.sort(key=lambda x: x["distance_km"])
    return results[:limit]


# Keep old name for backward compat
HOSPITALS = FALLBACK_HOSPITALS


def format_location_for_alert(lat: Optional[float], lng: Optional[float]) -> str:
    """Format location as Google Maps link for SMS/alerts."""
    coords = get_alert_safe_coordinates(lat, lng)
    if coords:
        safe_lat, safe_lng = coords
        return f"https://www.google.com/maps?q={safe_lat},{safe_lng}"
    return "Location unknown"


def get_location_context(lat: Optional[float], lng: Optional[float]) -> Dict:
    """
    Build a full location context for agents:
    - Google Maps link
    - Nearest hospitals with distance
    """
    if lat is None or lng is None:
        return {
            "available": False,
            "maps_link": None,
            "nearest_hospitals": [],
        }

    hospitals = get_nearest_hospitals(lat, lng, limit=None)
    return {
        "available": True,
        "lat": lat,
        "lng": lng,
        "maps_link": format_location_for_alert(lat, lng),
        "nearest_hospitals": hospitals,
    }
