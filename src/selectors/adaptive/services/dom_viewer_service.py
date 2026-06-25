"""
DOM Viewer Service for technical view DOM structure analysis.

This implements Story 7.2 (Technical and Non-Technical Views) requirements:
- DOM structure viewer with interactive element inspection
- Path tracing from root to selected element
- Element attributes and relationships
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import logging

from src.observability.logger import get_logger


@dataclass
class DOMElement:
    """Represents a DOM element with its properties."""
    tag_name: str
    element_id: Optional[str] = None
    classes: List[str] = None
    attributes: Dict[str, str] = None
    text_content: Optional[str] = None
    xpath: Optional[str] = None
    css_path: Optional[str] = None
    parent_xpath: Optional[str] = None
    children: List['DOMElement'] = None
    
    def __post_init__(self):
        if self.classes is None:
            self.classes = []
        if self.attributes is None:
            self.attributes = {}
        if self.children is None:
            self.children = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tag_name": self.tag_name,
            "element_id": self.element_id,
            "classes": self.classes,
            "attributes": self.attributes,
            "text_content": self.text_content,
            "xpath": self.xpath,
            "css_path": self.css_path,
            "parent_xpath": self.parent_xpath,
            "children": [child.to_dict() for child in self.children],
            "child_count": len(self.children),
        }


@dataclass
class DOMAnalysis:
    """Results of DOM structure analysis."""
    root_element: DOMElement
    failed_element: Optional[DOMElement] = None
    total_elements: int = 0
    max_depth: int = 0
    element_density: Dict[str, int] = None
    potential_alternatives: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.element_density is None:
            self.element_density = {}
        if self.potential_alternatives is None:
            self.potential_alternatives = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "root_element": self.root_element.to_dict() if self.root_element else None,
            "failed_element": self.failed_element.to_dict() if self.failed_element else None,
            "total_elements": self.total_elements,
            "max_depth": self.max_depth,
            "element_density": self.element_density,
            "potential_alternatives": self.potential_alternatives,
        }


class DOMViewerService:
    """
    Service for DOM structure analysis and visualization.
    
    This service provides technical users with detailed DOM structure
    information, element inspection, and path tracing capabilities.
    """
    
    def __init__(self):
        """Initialize the DOM viewer service."""
        self._logger = get_logger("dom_viewer_service")
    
    def analyze_dom_structure(
        self,
        selector: str,
        page_content: Optional[str] = None,
        snapshot_data: Optional[Dict[str, Any]] = None
    ) -> DOMAnalysis:
        """
        Analyze DOM structure for a failed selector.
        
        Args:
            selector: The CSS selector that failed
            page_content: Optional HTML content (for mock analysis)
            snapshot_data: Optional snapshot data from browser
            
        Returns:
            DOM analysis results
        """
        try:
            # Create mock DOM structure for demonstration
            dom_structure = self._create_mock_dom_structure(selector)
            
            # Analyze the structure
            analysis = self._analyze_structure(dom_structure, selector)
            
            self._logger.info(f"DOM analysis completed for selector: {selector}")
            return analysis
            
        except Exception as e:
            self._logger.error(f"DOM analysis failed: {e}")
            # Return minimal analysis
            return self._create_minimal_analysis(selector)
    
    def _create_mock_dom_structure(self, failed_selector: str) -> DOMElement:
        """
        Create a mock DOM structure for demonstration purposes.
        
        In a real implementation, this would parse actual HTML content
        or extract structure from browser snapshots.
        """
        # Create root element
        root = DOMElement(
            tag_name="html",
            xpath="/html",
            css_path="html"
        )
        
        # Create head
        head = DOMElement(
            tag_name="head",
            xpath="/html/head",
            css_path="head",
            parent_xpath="/html"
        )
        root.children.append(head)
        
        # Create body
        body = DOMElement(
            tag_name="body",
            xpath="/html/body",
            css_path="body",
            parent_xpath="/html"
        )
        root.children.append(body)
        
        # Create container div
        container = DOMElement(
            tag_name="div",
            element_id="container",
            classes=["container", "main-content"],
            attributes={"data-testid": "main-container"},
            xpath="/html/body/div[1]",
            css_path="body > div.container",
            parent_xpath="/html/body"
        )
        body.children.append(container)
        
        # Create header
        header = DOMElement(
            tag_name="header",
            classes=["header", "site-header"],
            xpath="/html/body/div[1]/header",
            css_path="body > div.container > header",
            parent_xpath="/html/body/div[1]"
        )
        container.children.append(header)
        
        # Create navigation
        nav = DOMElement(
            tag_name="nav",
            classes=["navigation", "main-nav"],
            xpath="/html/body/div[1]/nav",
            css_path="body > div.container > nav",
            parent_xpath="/html/body/div[1]"
        )
        container.children.append(nav)
        
        # Create main content area
        main = DOMElement(
            tag_name="main",
            classes=["main", "content"],
            xpath="/html/body/div[1]/main",
            css_path="body > div.container > main",
            parent_xpath="/html/body/div[1]"
        )
        container.children.append(main)
        
        # Create score container
        score_container = DOMElement(
            tag_name="div",
            classes=["scores", "game-scores"],
            xpath="/html/body/div[1]/main/div[1]",
            css_path="body > div.container > main > div.scores",
            parent_xpath="/html/body/div[1]/main"
        )
        main.children.append(score_container)
        
        # Create team elements (this would be the failed selector target)
        team_div = DOMElement(
            tag_name="div",
            classes=["team", "team-home"],
            xpath="/html/body/div[1]/main/div[1]/div[1]",
            css_path="body > div.container > main > div.scores > div.team",
            parent_xpath="/html/body/div[1]/main/div[1]"
        )
        score_container.children.append(team_div)
        
        # Create team name element (the actual failed target)
        team_name = DOMElement(
            tag_name="span",
            classes=["team-name", "name"],
            text_content="Team A",
            xpath="/html/body/div[1]/main/div[1]/div[1]/span[1]",
            css_path="body > div.container > main > div.scores > div.team > span.team-name",
            parent_xpath="/html/body/div[1]/main/div[1]/div[1]"
        )
        team_div.children.append(team_name)
        
        # Create score element
        team_score = DOMElement(
            tag_name="span",
            classes=["score", "team-score"],
            text_content="42",
            xpath="/html/body/div[1]/main/div[1]/div[1]/span[2]",
            css_path="body > div.container > main > div.scores > div.team > span.score",
            parent_xpath="/html/body/div[1]/main/div[1]/div[1]"
        )
        team_div.children.append(team_score)
        
        return root
    
    def _analyze_structure(self, root: DOMElement, failed_selector: str) -> DOMAnalysis:
        """Analyze the DOM structure and find relevant elements."""
        # Count total elements and calculate depth
        total_elements, max_depth = self._calculate_metrics(root)
        
        # Calculate element density
        element_density = self._calculate_element_density(root)
        
        # Find the failed element
        failed_element = self._find_failed_element(root, failed_selector)
        
        # Generate potential alternatives
        alternatives = self._generate_alternatives(root, failed_element, failed_selector)
        
        return DOMAnalysis(
            root_element=root,
            failed_element=failed_element,
            total_elements=total_elements,
            max_depth=max_depth,
            element_density=element_density,
            potential_alternatives=alternatives
        )
    
    def _calculate_metrics(self, root: DOMElement) -> Tuple[int, int]:
        """Calculate total elements and maximum depth."""
        total_elements = 0
        max_depth = 0
        
        def traverse(element: DOMElement, depth: int):
            nonlocal total_elements, max_depth
            total_elements += 1
            max_depth = max(max_depth, depth)
            for child in element.children:
                traverse(child, depth + 1)
        
        traverse(root, 0)
        return total_elements, max_depth
    
    def _calculate_element_density(self, root: DOMElement) -> Dict[str, int]:
        """Calculate density of different element types."""
        density = {}
        
        def traverse(element: DOMElement):
            tag = element.tag_name
            density[tag] = density.get(tag, 0) + 1
            for child in element.children:
                traverse(child)
        
        traverse(root)
        return density
    
    def _find_failed_element(self, root: DOMElement, selector: str) -> Optional[DOMElement]:
        """Find the element that matches the failed selector."""
        # Simple selector matching for demonstration
        if ".team-name" in selector:
            return self._find_element_by_class(root, "team-name")
        elif ".team-score" in selector:
            return self._find_element_by_class(root, "team-score")
        elif "#container" in selector:
            return self._find_element_by_id(root, "container")
        else:
            # Generic search - return first element with matching class
            for class_name in selector.split('.'):
                if class_name.strip():
                    element = self._find_element_by_class(root, class_name.strip())
                    if element:
                        return element
        return None
    
    def _find_element_by_class(self, root: DOMElement, class_name: str) -> Optional[DOMElement]:
        """Find element by CSS class."""
        def traverse(element: DOMElement) -> Optional[DOMElement]:
            if class_name in element.classes:
                return element
            for child in element.children:
                result = traverse(child)
                if result:
                    return result
            return None
        
        return traverse(root)
    
    def _find_element_by_id(self, root: DOMElement, element_id: str) -> Optional[DOMElement]:
        """Find element by ID."""
        def traverse(element: DOMElement) -> Optional[DOMElement]:
            if element.element_id == element_id:
                return element
            for child in element.children:
                result = traverse(child)
                if result:
                    return result
            return None
        
        return traverse(root)
    
    def _generate_alternatives(
        self, 
        root: DOMElement, 
        failed_element: Optional[DOMElement], 
        failed_selector: str
    ) -> List[Dict[str, Any]]:
        """Generate alternative selectors based on DOM structure."""
        alternatives = []
        
        if failed_element is None:
            return alternatives
        
        # Alternative 1: Use ID if available
        if failed_element.element_id:
            alternatives.append({
                "selector": f"#{failed_element.element_id}",
                "strategy": "id",
                "confidence": 0.95,
                "reasoning": "ID-based selectors are most stable"
            })
        
        # Alternative 2: Use combined class selector
        if len(failed_element.classes) > 1:
            combined_class = ".".join(failed_element.classes)
            alternatives.append({
                "selector": f".{combined_class.replace(' ', '.')}",
                "strategy": "class_combination",
                "confidence": 0.85,
                "reasoning": "Multiple classes reduce ambiguity"
            })
        
        # Alternative 3: Use parent-child relationship
        if failed_element.parent_xpath:
            parent_tag = failed_element.parent_xpath.split('/')[-1].split('[')[0]
            alternatives.append({
                "selector": f"{parent_tag} .{failed_element.classes[0] if failed_element.classes else failed_element.tag_name}",
                "strategy": "parent_child",
                "confidence": 0.75,
                "reasoning": "Parent-child relationship adds context"
            })
        
        # Alternative 4: Use attribute selector
        if failed_element.attributes:
            for attr_name, attr_value in failed_element.attributes.items():
                if attr_name.startswith("data-"):
                    alternatives.append({
                        "selector": f"[{attr_name}='{attr_value}']",
                        "strategy": "attribute",
                        "confidence": 0.80,
                        "reasoning": f"Attribute {attr_name} provides stable targeting"
                    })
                    break
        
        return alternatives
    
    def _create_minimal_analysis(self, selector: str) -> DOMAnalysis:
        """Create a minimal analysis when full analysis fails."""
        root = DOMElement(
            tag_name="html",
            xpath="/html",
            css_path="html"
        )
        
        return DOMAnalysis(
            root_element=root,
            failed_element=None,
            total_elements=1,
            max_depth=1,
            element_density={"html": 1},
            potential_alternatives=[]
        )
    
    def get_element_details(self, xpath: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific element.
        
        Args:
            xpath: XPath to the element
            
        Returns:
            Element details or None if not found
        """
        # This would normally traverse the actual DOM
        # For now, return mock data
        return {
            "xpath": xpath,
            "tag_name": "span",
            "classes": ["team-name"],
            "attributes": {"data-team": "home"},
            "text_content": "Team A",
            "computed_styles": {
                "color": "#333333",
                "font_size": "16px",
                "display": "inline-block"
            },
            "bounding_box": {
                "x": 120,
                "y": 85,
                "width": 80,
                "height": 24
            }
        }
    
    def trace_element_path(self, xpath: str) -> List[Dict[str, Any]]:
        """
        Trace the path from root to the specified element.
        
        Args:
            xpath: XPath to the target element
            
        Returns:
            List of elements in the path
        """
        # Mock path tracing
        return [
            {"xpath": "/html", "tag": "html", "type": "root"},
            {"xpath": "/html/body", "tag": "body", "type": "container"},
            {"xpath": "/html/body/div[1]", "tag": "div", "classes": ["container"], "type": "container"},
            {"xpath": "/html/body/div[1]/main", "tag": "main", "classes": ["main"], "type": "container"},
            {"xpath": "/html/body/div[1]/main/div[1]", "tag": "div", "classes": ["scores"], "type": "container"},
            {"xpath": "/html/body/div[1]/main/div[1]/div[1]", "tag": "div", "classes": ["team"], "type": "container"},
            {"xpath": "/html/body/div[1]/main/div[1]/div[1]/span[1]", "tag": "span", "classes": ["team-name"], "type": "target"}
        ]


# Global instance for dependency injection
_dom_viewer_service: Optional[DOMViewerService] = None


def get_dom_viewer_service() -> DOMViewerService:
    """Get or create the global DOM viewer service instance."""
    global _dom_viewer_service
    if _dom_viewer_service is None:
        _dom_viewer_service = DOMViewerService()
    return _dom_viewer_service
