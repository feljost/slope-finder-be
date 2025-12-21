from fastapi import FastAPI

from slope_check_backend.constants import ski_resorts
from slope_check_backend.models import LocationQuery
from slope_check_backend.utils import calculate_air_distance

app = FastAPI(title="Slope Check Backend")


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/ski-resorts/by-distance")
async def get_ski_resorts_by_distance(location: LocationQuery):
    """
    Get all ski resorts ordered by distance from the given location.
    """
    resorts_with_distance = []

    for resort in ski_resorts:
        distance = calculate_air_distance(
            location.lat,
            location.lng,
            resort["location"]["lat"],
            resort["location"]["lng"],
        )
        resorts_with_distance.append({**resort, "distance_km": round(distance, 2)})

    resorts_with_distance.sort(key=lambda x: x["distance_km"])

    return {"location": location.dict(), "resorts": resorts_with_distance}
