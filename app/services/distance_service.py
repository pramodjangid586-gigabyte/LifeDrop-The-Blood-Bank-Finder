import math
from typing import Tuple, Dict, Optional

# Pre-mapped coordinates for common emergency search hubs (manual location fallback)
KNOWN_LOCATIONS: Dict[str, Tuple[float, float]] = {
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "central delhi": (28.6304, 77.2177),
    "south delhi": (28.5355, 77.2410),
    "saket": (28.5244, 77.2167),
    "aiims": (28.5672, 77.2100),
    "safdarjung": (28.5684, 77.2066),
    "connaught place": (28.6315, 77.2167),
    "dwarka": (28.5921, 77.0460),
    "rohini": (28.7166, 77.1147),
    "noida": (28.5355, 77.3910),
    "gurugram": (28.4595, 77.0266),
    "gurgaon": (28.4595, 77.0266),
    "mumbai": (19.0760, 72.8777),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    # Pune Metropolitan Region & PCMC
    "pune": (18.5204, 73.8567),
    "pimpri-chinchwad": (18.6250, 73.8210),
    "pimpri chinchwad": (18.6250, 73.8210),
    "pcmc": (18.6250, 73.8210),
    "pimpri": (18.6250, 73.8210),
    "chinchwad": (18.6298, 73.7997),
    "shivajinagar": (18.5314, 73.8446),
    "kothrud": (18.5074, 73.8077),
    "swargate": (18.5018, 73.8586),
    "hadapsar": (18.5089, 73.9259),
    "viman nagar": (18.5679, 73.9143),
    "hinjawadi": (18.5913, 73.7389),
    "hinjewadi": (18.5913, 73.7389),
    "baner": (18.5590, 73.7868),
    "wakad": (18.5987, 73.7680),
    "aundh": (18.5580, 73.8075),
    "camp": (18.5158, 73.8787),
    "pune camp": (18.5158, 73.8787),
    "wanowrie": (18.5071, 73.8920),
    "erandwane": (18.5020, 73.8322),
    "sadashiv peth": (18.5106, 73.8420),
    "rasta peth": (18.5203, 73.8671),
    "saras baug": (18.5062, 73.8403),
    "deccan": (18.5134, 73.8407),
    "thergaon": (18.6289, 73.7744),
    "sassoon": (18.5257, 73.8719),
    "kharadi": (18.5515, 73.9348),
    "katraj": (18.4575, 73.8677),
}

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees), returned in kilometers.
    """
    R = 6371.0  # Earth's radius in km

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = R * c
    return round(distance, 2)

def get_bounding_box(lat: float, lon: float, radius_km: float) -> Tuple[float, float, float, float]:
    """
    Returns (min_lat, max_lat, min_lon, max_lon) for rapid spatial indexing queries.
    """
    lat_change = radius_km / 111.0
    lon_change = radius_km / (111.0 * math.cos(math.radians(lat)))
    return (
        lat - lat_change,
        lat + lat_change,
        lon - abs(lon_change),
        lon + abs(lon_change)
    )

def resolve_location_name(query: str) -> Optional[Tuple[float, float, str]]:
    """
    Fuzzy resolve textual location string to approximate coordinates.
    Prioritizes exact matches, then full token matches, then partial matches.
    """
    if not query:
        return None
    clean_query = query.strip().lower()

    # 1. Exact match priority (e.g. "pune" -> Pune center, "delhi" -> Delhi center)
    if clean_query in KNOWN_LOCATIONS:
        coords = KNOWN_LOCATIONS[clean_query]
        return (coords[0], coords[1], clean_query.title())

    # 2. Known location token contained within search text (e.g. "pune, maharashtra" or "near kothrud")
    for name in sorted(KNOWN_LOCATIONS.keys(), key=lambda k: len(k), reverse=True):
        if name in clean_query:
            coords = KNOWN_LOCATIONS[name]
            return (coords[0], coords[1], name.title())

    # 3. Partial substring within known name
    for name in sorted(KNOWN_LOCATIONS.keys(), key=lambda k: len(k), reverse=True):
        if clean_query in name:
            coords = KNOWN_LOCATIONS[name]
            return (coords[0], coords[1], name.title())

    return None

def resolve_search_coordinates(
    lat: Optional[float],
    lng: Optional[float],
    location: Optional[str],
    default_lat: float,
    default_lng: float,
    default_name: str = "Central Delhi (Default Hub)"
) -> Tuple[float, float, str]:
    """
    Intelligently resolve search center coordinates and area label.
    1. If location text matches a known hub (e.g. 'Pune', 'Kothrud', 'Saket'):
       - If lat/lng was omitted or is the system fallback default, prioritize the resolved location.
       - Otherwise, if lat/lng is a non-default custom coordinate (e.g. from GPS), use that coordinate.
    2. If location text is unknown but lat/lng is provided, use given lat/lng.
    3. Fallback to default coordinates.
    """
    resolved = resolve_location_name(location) if location else None

    if resolved:
        res_lat, res_lng, res_name = resolved
        if lat is None or lng is None:
            return res_lat, res_lng, res_name
        
        # Check if coordinates sent match the default Delhi hub
        is_default = (abs(lat - default_lat) < 0.01 and abs(lng - default_lng) < 0.01)
        delhi_keywords = ["delhi", "saket", "aiims", "safdarjung", "connaught", "dwarka", "rohini", "noida", "gurgaon", "gurugram"]
        is_delhi_query = any(k in (location or "").lower() for k in delhi_keywords)
        
        if is_default and not is_delhi_query:
            return res_lat, res_lng, res_name
        return lat, lng, res_name

    if lat is not None and lng is not None:
        return lat, lng, location.strip().title() if location else default_name

    return default_lat, default_lng, default_name
