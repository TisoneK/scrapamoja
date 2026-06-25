"""
Output formatting utilities.

Handles different output formats for CLI results.
"""

import json
import csv
import xml.etree.ElementTree as ET
from typing import Any, Dict, List
from io import StringIO


class OutputFormatter:
    """Formats output in different formats."""
    
    def __init__(self):
        self.formatters = {
            'json': self._format_json,
            'csv': self._format_csv,
            'xml': self._format_xml
        }
    
    def format(self, data: Any, format_type: str) -> str:
        """Format data in specified format."""
        if format_type not in self.formatters:
            raise ValueError(f"Unsupported format: {format_type}")
        
        return self.formatters[format_type](data)
    
    def _format_json(self, data: Any) -> str:
        """Format data as JSON."""
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def _format_csv(self, data: Any) -> str:
        """Format data as CSV."""
        output = StringIO()
        
        if isinstance(data, dict):
            if 'matches' in data:
                # Format match data
                matches = data['matches']
                if matches:
                    writer = csv.DictWriter(output, fieldnames=matches[0].keys())
                    writer.writeheader()
                    writer.writerows(matches)
            else:
                # Format generic dict
                writer = csv.DictWriter(output, fieldnames=data.keys())
                writer.writeheader()
                writer.writerow(data)
        elif isinstance(data, list):
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        else:
            output.write(str(data))
        
        return output.getvalue()
    
    def _format_xml(self, data: Any) -> str:
        """Format data as XML."""
        root = ET.Element('flashscore_data')
        
        if isinstance(data, dict):
            self._dict_to_xml(data, root)
        elif isinstance(data, list):
            for item in data:
                item_element = ET.SubElement(root, 'item')
                self._dict_to_xml(item, item_element)
        else:
            root.text = str(data)
        
        return ET.tostring(root, encoding='unicode')
    
    def _dict_to_xml(self, data: Dict[str, Any], parent: ET.Element):
        """Convert dictionary to XML elements."""
        for key, value in data.items():
            if isinstance(value, dict):
                child = ET.SubElement(parent, key)
                self._dict_to_xml(value, child)
            elif isinstance(value, list):
                for item in value:
                    child = ET.SubElement(parent, key)
                    if isinstance(item, dict):
                        self._dict_to_xml(item, child)
                    else:
                        child.text = str(item)
            else:
                child = ET.SubElement(parent, key)
                child.text = str(value)


class ColorOutput:
    """Adds color to console output."""
    
    COLORS = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'reset': '\033[0m'
    }
    
    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Add color to text."""
        if color not in cls.COLORS:
            return text
        return f"{cls.COLORS[color]}{text}{cls.COLORS['reset']}"
    
    @classmethod
    def success(cls, text: str) -> str:
        """Format success message."""
        return cls.colorize(text, 'green')
    
    @classmethod
    def error(cls, text: str) -> str:
        """Format error message."""
        return cls.colorize(text, 'red')
    
    @classmethod
    def warning(cls, text: str) -> str:
        """Format warning message."""
        return cls.colorize(text, 'yellow')
    
    @classmethod
    def info(cls, text: str) -> str:
        """Format info message."""
        return cls.colorize(text, 'blue')
