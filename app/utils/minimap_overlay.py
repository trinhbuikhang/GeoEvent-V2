"""
Minimap Overlay Module for GeoEvent Application
Handles drawing path overlays on the minimap using GPS data from .driveiri files
"""

from typing import Optional
from ..models.gps_model import GPSData

class MinimapOverlay:
    """
    Generates JavaScript code for drawing path overlays on Leaflet minimap
    """

    @staticmethod
    def generate_path_overlay(gps_data: Optional[GPSData]) -> str:
        """
        Generate JavaScript code to add a dashed path overlay to the minimap
        Returns empty string if no GPS data available
        """
        if not gps_data or not gps_data.points:
            return ""

        # Extract coordinates from GPS points
        coordinates = []
        for point in gps_data.points:
            coordinates.append([point.latitude, point.longitude])

        if len(coordinates) < 2:
            return ""

        # Convert coordinates to JavaScript array format
        coords_js = ",\n                ".join([f"[{lat:.6f}, {lon:.6f}]" for lat, lon in coordinates])

        # Generate JavaScript code for dashed polyline
        overlay_js = f"""
            // Add path overlay
            var pathCoordinates = [
                {coords_js}
            ];

            var pathPolyline = L.polyline(pathCoordinates, {{
                color: '#000080',
                weight: 3,
                opacity: 0.9,
                lineCap: 'round',
                lineJoin: 'round'
            }}).addTo(map);

            // Optionally fit map to show entire path (commented out to keep current zoom)
            // if (pathCoordinates.length > 1) {{
            //     map.fitBounds(pathPolyline.getBounds(), {{padding: [20, 20]}});
            // }}
        """

        return overlay_js