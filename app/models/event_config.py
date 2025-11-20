"""
Event configuration for GeoEvent application
Contains maximum lengths for different event types
"""

# Maximum lengths for events in meters
MAX_EVENT_LENGTHS = {
    "Bridge": 400,
    "Cattle Grid": 50,
    "Detour": 500,
    "Pavers": 150,
    "Railway Crossing": 100,
    "Road Works": 500,
    "Speed Hump": 120,
    "Surface Contamination": 500,
    "Unsealed Road": 1000,
    "Wet surface": 200,
    "Railway Crossing": 100
}

def get_max_length_for_event(event_name: str) -> int:
    """
    Get maximum allowed length for an event type
    Returns the max length if found, otherwise None
    """
    return MAX_EVENT_LENGTHS.get(event_name)

def is_event_length_exceeded(event_name: str, length_meters: float) -> bool:
    """
    Check if event length exceeds the maximum allowed
    """
    max_length = get_max_length_for_event(event_name)
    if max_length is None:
        return False
    return length_meters > max_length