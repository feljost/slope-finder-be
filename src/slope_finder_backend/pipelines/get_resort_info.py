from concurrent.futures import ThreadPoolExecutor

from slope_finder_backend.models import Location
from slope_finder_backend.services.routing import get_driving_distances_batch
from slope_finder_backend.services.snow_report import scrape_snow_reports_batch
from slope_finder_backend.services.weather import get_weather_data


def enrich_resorts_with_info(
    lat: float,
    lng: float,
    page_resorts: list[dict],
    date: str | None = None
) -> list[dict]:
    """
    Enrich resort data with driving distances, snow reports, and weather information.

    This function performs the following operations:
    1. Fetches driving distances, snow reports, and weather data in parallel
    2. Combines all data into enriched resort objects

    Args:
        location: User's location (lat, lng)
        page_resorts: List of resorts with metadata (resort data and air_distance_km)
        date: Optional date for weather data in YYYY-MM-DD format

    Returns:
        List of enriched resort dictionaries with distance, duration, snow reports, and weather
    """
    # Prepare destinations for routing
    destinations = [
        {"lat": r["resort"]["location"]["lat"], "lng": r["resort"]["location"]["lng"]}
        for r in page_resorts
    ]

    def fetch_driving_distances():
        return get_driving_distances_batch(lat, lng, destinations)

    def fetch_weather_data():
        weather_data = {}
        if date:
            for item in page_resorts:
                resort_lat = item["resort"]["location"]["lat"]
                resort_lng = item["resort"]["location"]["lng"]
                try:
                    weather = get_weather_data(resort_lat, resort_lng, date)
                    weather_data[item["resort"]["name"]] = weather.dict()
                except Exception:
                    weather_data[item["resort"]["name"]] = None
        return weather_data

    def fetch_snow_reports():
        return scrape_snow_reports_batch(
            [r["resort"]["snowreport_url"] for r in page_resorts]
        )

    # Execute all data fetching in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        driving_future = executor.submit(fetch_driving_distances)
        weather_future = executor.submit(fetch_weather_data)
        snow_reports_future = executor.submit(fetch_snow_reports)

        route_infos = driving_future.result()
        weather_data = weather_future.result()
        snow_reports = snow_reports_future.result()

    # Build enriched resort data
    enriched_resorts = []
    for i, item in enumerate(page_resorts):
        route_info = route_infos[i]
        if route_info:
            resort_data = {
                **item["resort"],
                "air_distance_km": round(item["air_distance_km"], 2),
                "distance_km": route_info["distance_km"],
                "duration_minutes": route_info["duration_minutes"],
                "snow_report": snow_reports[item["resort"]["snowreport_url"]]["data"],
            }
            # Add weather data if available
            if date and item["resort"]["name"] in weather_data:
                resort_data["weather"] = weather_data[item["resort"]["name"]]

            enriched_resorts.append(resort_data)

    return enriched_resorts
