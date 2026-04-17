"""
Visual Preview Service for generating visual previews of selector failures.

This implements Story 7.2 (Technical and Non-Technical Views) requirements:
- Visual-only selector previews with highlight overlays
- Base64 encoded visual previews for non-technical users
"""

import base64
import io
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import logging

from src.observability.logger import get_logger


class VisualPreviewService:
    """
    Service for generating visual previews of selector failures.
    
    This service creates visual representations of failed selectors
    with highlight overlays to help non-technical users understand
    what went wrong.
    """
    
    def __init__(self):
        """Initialize the visual preview service."""
        self._logger = get_logger("visual_preview_service")
    
    def generate_selector_preview(
        self,
        selector: str,
        page_content: Optional[str] = None,
        highlight_color: str = "#FF6B6B",
        width: int = 800,
        height: int = 600,
    ) -> str:
        """
        Generate a visual preview for a failed selector.
        
        Args:
            selector: The CSS selector that failed
            page_content: Optional HTML content (for mock generation)
            highlight_color: Color for highlighting failed elements
            width: Preview width in pixels
            height: Preview height in pixels
            
        Returns:
            Base64 encoded PNG image
        """
        try:
            # Create a mock preview image
            image = self._create_mock_selector_preview(
                selector=selector,
                highlight_color=highlight_color,
                width=width,
                height=height
            )
            
            # Convert to base64
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            
            base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            self._logger.info(f"Generated visual preview for selector: {selector}")
            return base64_image
            
        except Exception as e:
            self._logger.error(f"Failed to generate visual preview: {e}")
            # Return a simple error image
            return self._generate_error_preview(selector)
    
    def _create_mock_selector_preview(
        self,
        selector: str,
        highlight_color: str,
        width: int,
        height: int
    ) -> Image.Image:
        """
        Create a mock preview image showing the selector context.
        
        Args:
            selector: The CSS selector
            highlight_color: Color for highlighting
            width: Image width
            height: Image height
            
        Returns:
            PIL Image object
        """
        # Create white background
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Try to load a font, fallback to default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 16)
            title_font = ImageFont.truetype("arial.ttf", 20)
        except Exception:
            font = ImageFont.load_default()
            title_font = ImageFont.load_default()
        
        # Draw header
        header_text = f"Selector Preview: {selector}"
        draw.text((20, 20), header_text, fill='black', font=title_font)
        
        # Draw mock page structure
        self._draw_mock_page_structure(draw, font, width, height)
        
        # Highlight the failed selector area
        self._highlight_selector_area(draw, selector, highlight_color, width, height)
        
        # Draw error message
        error_text = "Element not found"
        draw.text((20, height - 60), error_text, fill=highlight_color, font=font)
        
        # Draw footer
        footer_text = "Visual Preview - Non-Technical View"
        draw.text((20, height - 30), footer_text, fill='gray', font=font)
        
        return image
    
    def _draw_mock_page_structure(
        self,
        draw: ImageDraw.Draw,
        font: Any,
        width: int,
        height: int
    ) -> None:
        """Draw a mock page structure."""
        # Draw header area
        draw.rectangle([20, 60, width - 20, 100], outline='black', width=1)
        draw.text((30, 70), "Page Header", fill='gray', font=font)
        
        # Draw navigation area
        draw.rectangle([20, 110, width - 20, 150], outline='black', width=1)
        draw.text((30, 120), "Navigation Menu", fill='gray', font=font)
        
        # Draw content area
        draw.rectangle([20, 160, width - 20, height - 100], outline='black', width=1)
        draw.text((30, 170), "Main Content Area", fill='gray', font=font)
        
        # Draw some mock elements
        draw.rectangle([50, 200, 200, 230], outline='blue', width=2)
        draw.text((60, 205), "Team Name", fill='blue', font=font)
        
        draw.rectangle([250, 200, 400, 230], outline='green', width=2)
        draw.text((260, 205), "Score", fill='green', font=font)
        
        draw.rectangle([450, 200, 600, 230], outline='purple', width=2)
        draw.text((460, 205), "Time", fill='purple', font=font)
    
    def _highlight_selector_area(
        self,
        draw: ImageDraw.Draw,
        selector: str,
        highlight_color: str,
        width: int,
        height: int
    ) -> None:
        """Highlight the area where the selector should have matched."""
        # Parse the selector to determine what to highlight
        if ".team-name" in selector or "team" in selector.lower():
            # Highlight team name area
            draw.rectangle([45, 195, 205, 235], outline=highlight_color, width=3)
            # Draw X to indicate failure
            draw.line([45, 195, 205, 235], fill=highlight_color, width=3)
            draw.line([45, 235, 205, 195], fill=highlight_color, width=3)
        elif ".score" in selector or "score" in selector.lower():
            # Highlight score area
            draw.rectangle([245, 195, 405, 235], outline=highlight_color, width=3)
            # Draw X to indicate failure
            draw.line([245, 195, 405, 235], fill=highlight_color, width=3)
            draw.line([245, 235, 405, 195], fill=highlight_color, width=3)
        else:
            # Generic highlight in content area
            draw.rectangle([100, 250, width - 100, 350], outline=highlight_color, width=3)
            # Draw X to indicate failure
            draw.line([100, 250, width - 100, 350], fill=highlight_color, width=3)
            draw.line([100, 350, width - 100, 250], fill=highlight_color, width=3)
    
    def _generate_error_preview(self, selector: str) -> str:
        """Generate a simple error preview when preview generation fails."""
        try:
            # Create a simple error image
            image = Image.new('RGB', (400, 200), color='#FFE5E5')
            draw = ImageDraw.Draw(image)
            
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except Exception:
                font = ImageFont.load_default()
            
            # Draw error message
            error_text = f"Preview unavailable for:\n{selector}"
            draw.text((20, 50), error_text, fill='red', font=font)
            draw.text((20, 100), "Element could not be visualized", fill='black', font=font)
            
            # Convert to base64
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except Exception:
            # Return a minimal base64 error indicator
            return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    def create_comparison_preview(
        self,
        failed_selector: str,
        alternative_selectors: list[Dict[str, Any]],
        width: int = 800,
        height: int = 400
    ) -> str:
        """
        Create a comparison preview showing failed and alternative selectors.
        
        Args:
            failed_selector: The selector that failed
            alternative_selectors: List of alternative selector dictionaries
            width: Total width of the comparison image
            height: Height of the comparison image
            
        Returns:
            Base64 encoded PNG image
        """
        try:
            # Calculate individual preview width
            num_previews = len(alternative_selectors) + 1  # +1 for failed selector
            preview_width = width // num_previews
            
            # Create canvas
            image = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(image)
            
            try:
                font = ImageFont.truetype("arial.ttf", 12)
            except Exception:
                font = ImageFont.load_default()
            
            # Draw failed selector preview
            x_offset = 0
            failed_preview = self._create_mini_preview(
                failed_selector, preview_width, height - 40, "#FF6B6B"
            )
            image.paste(failed_preview, (x_offset, 40))
            draw.text((x_offset + 10, 10), "Failed", fill='red', font=font)
            
            # Draw alternative selector previews
            for i, alt in enumerate(alternative_selectors[:3]):  # Limit to 3 alternatives
                x_offset += preview_width
                alt_selector = alt.get('selector', '')
                confidence = alt.get('confidence_score', 0.0)
                
                alt_preview = self._create_mini_preview(
                    alt_selector, preview_width, height - 40, "#4CAF50"
                )
                image.paste(alt_preview, (x_offset, 40))
                draw.text((x_offset + 10, 10), f"Alt {i+1} ({confidence:.2f})", fill='green', font=font)
            
            # Convert to base64
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except Exception as e:
            self._logger.error(f"Failed to create comparison preview: {e}")
            return self._generate_error_preview(failed_selector)
    
    def _create_mini_preview(
        self,
        selector: str,
        width: int,
        height: int,
        color: str
    ) -> Image.Image:
        """Create a small preview for comparison."""
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.truetype("arial.ttf", 10)
        except Exception:
            font = ImageFont.load_default()
        
        # Draw simplified mock structure
        draw.rectangle([10, 10, width - 10, 40], outline='gray', width=1)
        draw.rectangle([10, 50, width - 10, height - 10], outline='gray', width=1)
        
        # Highlight selector area
        if "team" in selector.lower():
            draw.rectangle([20, 60, width // 2, 80], outline=color, width=2)
        elif "score" in selector.lower():
            draw.rectangle([width // 2 + 10, 60, width - 20, 80], outline=color, width=2)
        else:
            draw.rectangle([20, height // 2, width - 20, height // 2 + 30], outline=color, width=2)
        
        return image


# Global instance for dependency injection
_visual_preview_service: Optional[VisualPreviewService] = None


def get_visual_preview_service() -> VisualPreviewService:
    """Get or create the global visual preview service instance."""
    global _visual_preview_service
    if _visual_preview_service is None:
        _visual_preview_service = VisualPreviewService()
    return _visual_preview_service
