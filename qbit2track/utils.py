"""
Utility functions for qbit2track
"""
import json
from datetime import datetime
from dataclasses import asdict


class TMDBObject:
    """Wrapper class to allow dict-like access with attribute syntax for TMDB objects"""
    def __init__(self, data):
        self._data = data if isinstance(data, dict) else {}
    
    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __contains__(self, key):
        return key in self._data
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def keys(self):
        return self._data.keys()
    
    def values(self):
        return self._data.values()
    
    def items(self):
        return self._data.items()


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects, dataclasses, and TMDB objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dataclass_fields__'):  # Handle dataclasses
            return asdict(obj)
        elif hasattr(obj, '__dict__') and not hasattr(obj, '__dataclass_fields__'):  # Handle TMDB objects
            return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        return super().default(obj)


def custom_json_decoder(obj):
    """Custom JSON decoder for datetime objects and dataclasses"""
    # Handle datetime objects
    for key, value in obj.items():
        if key == 'created_at' and isinstance(value, str):
            try:
                obj[key] = datetime.fromisoformat(value)
            except ValueError:
                pass  # Keep original value if parsing fails
    
    # Convert TMDB object dicts back to TMDBObject for attribute access
    for key in ['episode_data', 'season_data']:
        if key in obj and isinstance(obj[key], dict):
            obj[key] = TMDBObject(obj[key])
    
    return obj
