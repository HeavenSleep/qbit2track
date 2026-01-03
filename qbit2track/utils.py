"""
Utility functions for qbit2track
"""
import json
from datetime import datetime
from dataclasses import asdict


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects and dataclasses"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dataclass_fields__'):  # Handle dataclasses
            return asdict(obj)
        return super().default(obj)


def custom_json_decoder(obj):
    """Custom JSON decoder for datetime objects and dataclasses"""
    for key, value in obj.items():
        if key == 'created_at' and isinstance(value, str):
            try:
                obj[key] = datetime.fromisoformat(value)
            except ValueError:
                pass  # Keep original value if parsing fails
    return obj
