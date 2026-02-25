from __future__ import annotations

from typing import Optional, Tuple, Dict, Any
import os
import time
import requests

# Simple in-process cache to avoid burning API quota
# key: (origin, destination, mode) -> (expires_at, minutes)
_CACHE: Dict[Tuple[str, str, str], Tuple[float, Optional[int]]] = {}
CACHE_TTL_SECONDS = 180  # 3 min


def _cache_get(origin: str, destination: str, mode: str) -> Optional[int]:
    k = (origin, destination, mode)
    v = _CACHE.get(k)
    if not v:
        return None
    exp, minutes = v
    if time.time() > exp:
        _CACHE.pop(k, None)
        return None
    return minutes


def _cache_set(origin: str, destination: str, mode: str, minutes: Optional[int]) -> None:
    _CACHE[(origin, destination, mode)] = (time.time() + CACHE_TTL_SECONDS, minutes)


def get_eta_minutes(origin: str, destination: str, mode: str) -> Optional[int]:
    """Returns ETA in minutes using Google Directions API.

    mode: driving | transit | bicycling | walking
    For driving: tries duration_in_traffic, falls back to duration.
    """
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not key:
        return None

    origin = (origin or "").strip()
    destination = (destination or "").strip()
    mode = (mode or "").strip().lower()
    if not origin or not destination or mode not in {"driving", "transit", "bicycling", "walking"}:
        return None

    cached = _cache_get(origin, destination, mode)
    if cached is not None:
        return cached

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params: Dict[str, Any] = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "key": key,
    }

    # "live" component
    # - driving: traffic-aware if departure_time=now
    # - transit: schedules/real-time when available
    if mode in {"driving", "transit"}:
        params["departure_time"] = "now"
    if mode == "driving":
        params["traffic_model"] = "best_guess"

    try:
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()
    except Exception:
        _cache_set(origin, destination, mode, None)
        return None

    if not isinstance(data, dict) or data.get("status") not in {"OK", "ZERO_RESULTS"}:
        _cache_set(origin, destination, mode, None)
        return None

    if data.get("status") != "OK":
        _cache_set(origin, destination, mode, None)
        return None

    routes = data.get("routes") or []
    if not routes:
        _cache_set(origin, destination, mode, None)
        return None

    legs = (routes[0].get("legs") or [])
    if not legs:
        _cache_set(origin, destination, mode, None)
        return None

    leg0 = legs[0]
    seconds = None

    if mode == "driving" and isinstance(leg0, dict):
        dit = leg0.get("duration_in_traffic")
        if isinstance(dit, dict) and isinstance(dit.get("value"), (int, float)):
            seconds = int(dit["value"])

    if seconds is None and isinstance(leg0, dict):
        dur = leg0.get("duration")
        if isinstance(dur, dict) and isinstance(dur.get("value"), (int, float)):
            seconds = int(dur["value"])

    if seconds is None:
        _cache_set(origin, destination, mode, None)
        return None

    minutes = max(1, int(round(seconds / 60.0)))
    _cache_set(origin, destination, mode, minutes)
    return minutes
