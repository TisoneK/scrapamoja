"""
Infobox processor for Wikipedia articles.
"""

from typing import Dict, Any, Optional
import re
from datetime import datetime, date


class WikipediaInfoboxProcessor:
    """Wikipedia-specific infobox processor and validator."""
    
    def __init__(self):
        self.coordinate_patterns = [
            r'(\d+\.?\d*)[°\s]*([NS])\s*(\d+\.?\d*)[°\s]*([EW])',
            r'(-?\d+\.?\d+),\s*(-?\d+\.?\d+)',
        ]
    
    def validate_infobox_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate infobox data structure and content."""
        errors = []
        warnings = []
        
        # Validate numeric fields
        numeric_fields = ['population', 'area', 'elevation']
        for field in numeric_fields:
            value = data.get(field)
            if value is not None:
                if not isinstance(value, (int, float)) or value < 0:
                    errors.append(f"{field} must be a non-negative number")
        
        # Validate date fields
        date_fields = ['established', 'founded', 'independence']
        for field in date_fields:
            value = data.get(field)
            if value is not None:
                if not isinstance(value, (datetime, date)):
                    errors.append(f"{field} must be a valid datetime or date object")
        
        # Validate coordinates
        coords = data.get('coordinates')
        if coords is not None:
            coord_validation = self.validate_coordinates(coords)
            errors.extend(coord_validation['errors'])
            warnings.extend(coord_validation['warnings'])
        
        score = max(0.0, 1.0 - (len(errors) * 0.2) - (len(warnings) * 0.05))
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'score': score
        }
    
    def parse_coordinates(self, coord_string: str) -> Optional[Dict[str, float]]:
        """Parse coordinate string into latitude and longitude."""
        if not coord_string:
            return None
        
        coord_string = coord_string.strip()
        
        for pattern in self.coordinate_patterns:
            match = re.search(pattern, coord_string, re.IGNORECASE)
            if match:
                return self._convert_coordinate_match(match)
        
        return None
    
    def validate_coordinates(self, coords: Any) -> Dict[str, List[str]]:
        """Validate coordinate data."""
        errors = []
        warnings = []
        
        if not isinstance(coords, dict):
            errors.append("Coordinates must be a dictionary")
            return {'errors': errors, 'warnings': warnings}
        
        lat = coords.get('lat')
        lon = coords.get('lon')
        
        if lat is not None and not (-90 <= lat <= 90):
            errors.append("Latitude must be between -90 and 90")
        
        if lon is not None and not (-180 <= lon <= 180):
            errors.append("Longitude must be between -180 and 180")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _convert_coordinate_match(self, match) -> Dict[str, float]:
        """Convert regex match to coordinate dictionary."""
        groups = match.groups()
        
        if len(groups) >= 4:
            # DMS format
            lat = float(groups[0])
            lat_dir = groups[1].upper()
            lon = float(groups[2])
            lon_dir = groups[3].upper()
            
            if lat_dir == 'S':
                lat = -lat
            if lon_dir == 'W':
                lon = -lon
        else:
            # Decimal degrees
            lat = float(groups[0])
            lon = float(groups[1])
        
        return {'lat': lat, 'lon': lon}
    
    def get_default_values(self) -> Dict[str, Any]:
        """Get default values for missing infobox fields."""
        return {
            'title': None,
            'image': None,
            'caption': None,
            'population': None,
            'area': None,
            'elevation': None,
            'established': None,
            'founded': None,
            'independence': None,
            'coordinates': None,
            'location': None,
            'government_type': None,
            'leader_title': None,
            'population_density': None,
            'timezone': None,
            'website': None
        }
