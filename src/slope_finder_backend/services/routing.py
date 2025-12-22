import os

from datetime import datetime
from math import radians
from math import sin
from math import cos
from math import sqrt
from math import atan2

import requests
from dotenv import load_dotenv

load_dotenv()

MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")
GOOGLE_ROUTES_API_KEY = os.getenv("GOOGLE_ROUTES_API_KEY")


def calculate_air_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the distance between two coordinates using the Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Earth's radius in kilometers

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lng = radians(lng2 - lng1)

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def get_driving_distances_batch(
    origin_lat: float, origin_lng: float, destinations: list[dict]
) -> list[dict]:
    """
    Get driving distances and durations from origin to multiple destinations using Mapbox Directions Matrix API.
    Processes up to 25 destinations at a time.

    destinations should be a list of dicts with 'lat' and 'lng' keys.
    Returns list of dicts with distance_km and duration_minutes, or None for unreachable destinations.
    """
    if not MAPBOX_API_KEY:
        raise ValueError("MAPBOX_API_KEY not set in environment variables")

    # Limit to first 25 destinations
    destinations = destinations[:10]

    # Format coordinates: origin first, then all destinations
    coords = f"{origin_lng},{origin_lat}"
    for dest in destinations:
        coords += f";{dest['lng']},{dest['lat']}"

    url = f"https://api.mapbox.com/directions-matrix/v1/mapbox/driving/{coords}"

    params = {
        "access_token": MAPBOX_API_KEY,
        "sources": "0",
        "destinations": ";".join([str(i) for i in range(1, len(destinations) + 1)]),
        "annotations": "distance,duration",
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    print(data)

    if not data.get("durations") or not data.get("distances"):
        return [None] * len(destinations)

    # Extract the first row (origin to all destinations)
    durations = data["durations"][0]
    distances = data["distances"][0]

    results = []
    for i in range(len(destinations)):
        if durations[i] is not None and distances[i] is not None:
            results.append(
                {
                    "distance_km": round(distances[i] / 1000, 2),
                    "duration_minutes": round(durations[i] / 60, 1),
                }
            )
        else:
            results.append(None)

    return results


def get_routes_batch_google(
    origin_lat: float,
    origin_lng: float,
    destinations: list[dict],
    departure_time: datetime,
) -> list[dict]:
    """
    Get driving and transit routes from origin to multiple destinations using Google Routes Matrix API.
    Makes 2 API calls total (one for DRIVE mode, one for TRANSIT mode) for all destinations.

    Args:
        origin_lat: Origin latitude
        origin_lng: Origin longitude
        destinations: List of dicts with 'lat' and 'lng' keys
        departure_time: Datetime object for departure time

    Returns:
        List of dicts with driving and transit information, or None for unreachable destinations.
        Each dict contains:
        {
            "driving": {"distance_km": float, "duration_minutes": float},
            "transit": {"distance_km": float, "duration_minutes": float}
        }
        If a mode is not available, it will be None.
    """
    if not GOOGLE_ROUTES_API_KEY:
        raise ValueError("GOOGLE_ROUTES_API_KEY not set in environment variables")

    url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_ROUTES_API_KEY,
        "X-Goog-FieldMask": "originIndex,destinationIndex,distanceMeters,duration,condition",
    }

    # Prepare origins and destinations
    origins = [
        {
            "waypoint": {
                "location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}
            }
        }
    ]

    destination_list = [
        {
            "waypoint": {
                "location": {"latLng": {"latitude": dest["lat"], "longitude": dest["lng"]}}
            }
        }
        for dest in destinations
    ]

    # Initialize results with None for each destination
    results = [{"driving": None, "transit": None} for _ in destinations]

    # Get driving routes
    driving_body = {
        "origins": origins,
        "destinations": destination_list,
        "travelMode": "DRIVE",
    }

    try:
        response = requests.post(url, json=driving_body, headers=headers)
        response.raise_for_status()
        data_list = response.json()

        for data in data_list:
            # Check if route was successful
            if data.get("condition") == "ROUTE_EXISTS":
                dest_index = data.get("destinationIndex", 0)
                distance_meters = data.get("distanceMeters")
                duration_str = data.get("duration")

                if distance_meters is not None and duration_str is not None:
                    # Parse duration string (format: "123s")
                    duration_seconds = float(duration_str.rstrip("s"))
                    results[dest_index]["driving"] = {
                        "distance_km": round(distance_meters / 1000, 2),
                        "duration_minutes": round(duration_seconds / 60, 1),
                    }
    except Exception as e:
        print(f"Error fetching driving routes: {e}")

    # Get transit routes
    # Convert datetime to ISO 8601 format with Z suffix
    departure_time_str = departure_time.isoformat() + "Z"
    transit_body = {
        "origins": origins,
        "destinations": destination_list,
        "travelMode": "TRANSIT",
        "departureTime": departure_time_str,
    }

    try:
        response = requests.post(url, json=transit_body, headers=headers)
        response.raise_for_status()
        data_list = response.json()

        for data in data_list:
            # Check if route was successful
            if data.get("condition") == "ROUTE_EXISTS":
                dest_index = data.get("destinationIndex", 0)
                distance_meters = data.get("distanceMeters")
                duration_str = data.get("duration")

                if distance_meters is not None and duration_str is not None:
                    # Parse duration string (format: "123s")
                    duration_seconds = float(duration_str.rstrip("s"))
                    results[dest_index]["transit"] = {
                        "distance_km": round(distance_meters / 1000, 2),
                        "duration_minutes": round(duration_seconds / 60, 1),
                    }
    except Exception as e:
        print(f"Error fetching transit routes: {e}")

    # Convert to None if both modes failed for a destination
    final_results = []
    for result in results:
        if result["driving"] is None and result["transit"] is None:
            final_results.append(None)
        else:
            final_results.append(result)

    return final_results