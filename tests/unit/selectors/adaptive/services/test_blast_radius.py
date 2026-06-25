"""
Unit tests for BlastRadius Calculator service.

Story: 3.3 - Calculate Blast Radius
"""

import pytest

from src.selectors.adaptive.services.blast_radius import (
    BlastRadiusCalculator,
    BlastRadiusResult,
    BlastRadiusUI,
    SeverityLevel,
    AffectedSelector,
    RecipeSelector,
    get_blast_radius_calculator,
)


# Sample HTML for testing
SAMPLE_HTML = """
<html>
<body>
    <div id="main-content">
        <section class="product-list">
            <div class="product-card" data-id="1">
                <span class="product-name">Product 1</span>
                <button class="buy-btn">Buy</button>
            </div>
            <div class="product-card" data-id="2">
                <span class="product-name">Product 2</span>
                <button class="buy-btn">Buy</button>
            </div>
        </section>
        <aside class="sidebar">
            <div class="ad-banner">
                <button class="ad-click">Click Here</button>
            </div>
        </aside>
    </div>
</body>
</html>
"""

SAMPLE_HTML_NO_MATCH = """
<html>
<body>
    <div id="unrelated">
        <button class="other-btn">Other</button>
    </div>
</body>
</html>
"""

SAMPLE_HTML_DEEP_NESTING = """
<html>
<body>
    <div id="container">
        <section>
            <article>
                <div>
                    <span id="target">Target</span>
                </div>
            </article>
        </section>
    </div>
</body>
</html>
"""


class TestSeverityLevel:
    """Tests for SeverityLevel enum."""
    
    def test_severity_values(self):
        """Test that severity levels have correct string values."""
        assert SeverityLevel.LOW.value == "low"
        assert SeverityLevel.MEDIUM.value == "medium"
        assert SeverityLevel.HIGH.value == "high"
        assert SeverityLevel.CRITICAL.value == "critical"


class TestBlastRadiusCalculator:
    """Tests for BlastRadiusCalculator service."""
    
    @pytest.fixture
    def calculator(self):
        """Create a BlastRadiusCalculator instance."""
        return BlastRadiusCalculator()
    
    @pytest.fixture
    def sample_selectors(self):
        """Create sample selectors for testing."""
        return [
            RecipeSelector(
                selector_string=".product-card",
                recipe_id=1,
                sport="football",
                confidence_score=0.8,
            ),
            RecipeSelector(
                selector_string=".buy-btn",
                recipe_id=1,
                sport="football",
                confidence_score=0.9,
            ),
            RecipeSelector(
                selector_string=".ad-banner",
                recipe_id=2,
                sport="basketball",
                confidence_score=0.7,
            ),
            RecipeSelector(
                selector_string=".sidebar",
                recipe_id=2,
                sport="basketball",
                confidence_score=0.6,
            ),
        ]
    
    # === Tests for _calculate_severity ===
    
    def test_severity_low_single_selector_single_sport(self, calculator):
        """Test LOW severity: 1-2 affected, 1 sport."""
        assert calculator._calculate_severity(1, 1) == SeverityLevel.LOW
        assert calculator._calculate_severity(2, 1) == SeverityLevel.LOW
    
    def test_severity_medium_multiple_selectors(self, calculator):
        """Test MEDIUM severity: 3-5 affected or 2-3 sports."""
        assert calculator._calculate_severity(3, 1) == SeverityLevel.MEDIUM
        assert calculator._calculate_severity(5, 2) == SeverityLevel.MEDIUM
        assert calculator._calculate_severity(3, 3) == SeverityLevel.MEDIUM
    
    def test_severity_high_multiple_affected(self, calculator):
        """Test HIGH severity: 6-10 affected or 4+ sports."""
        assert calculator._calculate_severity(6, 1) == SeverityLevel.HIGH
        assert calculator._calculate_severity(9, 1) == SeverityLevel.HIGH
        assert calculator._calculate_severity(3, 4) == SeverityLevel.HIGH
    
    def test_severity_critical_many_affected(self, calculator):
        """Test CRITICAL severity: 10+ affected."""
        assert calculator._calculate_severity(10, 1) == SeverityLevel.CRITICAL
        assert calculator._calculate_severity(15, 3) == SeverityLevel.CRITICAL
        assert calculator._calculate_severity(20, 5) == SeverityLevel.CRITICAL
    
    # === Tests for _find_ancestor_containers ===
    
    def test_find_ancestors_with_id(self, calculator):
        """Test finding ancestors with ID attributes."""
        ancestors = calculator._find_ancestor_containers(
            SAMPLE_HTML, 
            ".buy-btn"
        )
        # Should find #main-content and/or #product-list
        assert len(ancestors) > 0
        assert any("#main-content" in a for a in ancestors)
    
    def test_find_ancestors_no_match(self, calculator):
        """Test when selector doesn't match."""
        ancestors = calculator._find_ancestor_containers(
            SAMPLE_HTML,
            ".nonexistent"
        )
        assert ancestors == []
    
    def test_find_ancestors_deep_nesting(self, calculator):
        """Test with deeply nested elements."""
        ancestors = calculator._find_ancestor_containers(
            SAMPLE_HTML_DEEP_NESTING,
            "#target"
        )
        # Should find at least #container as an ancestor
        assert len(ancestors) > 0
    
    def test_find_ancestors_max_depth(self, calculator):
        """Test that ancestor depth is limited."""
        # With MAX_ANCESTOR_DEPTH = 5, should not exceed this
        ancestors = calculator._find_ancestor_containers(
            SAMPLE_HTML_DEEP_NESTING,
            "#target"
        )
        assert len(ancestors) <= calculator.MAX_ANCESTOR_DEPTH
    
    # === Tests for _shares_ancestor ===
    
    def test_shares_ancestor_true(self, calculator):
        """Test detecting shared ancestors."""
        proposed_ancestors = ["#main-content", ".product-list"]
        
        # .product-card should share #main-content
        assert calculator._shares_ancestor(
            ".product-card",
            SAMPLE_HTML,
            proposed_ancestors
        ) is True
    
    def test_shares_ancestor_false(self, calculator):
        """Test when no shared ancestors."""
        proposed_ancestors = [".sidebar"]
        
        # .product-card should NOT share with sidebar
        assert calculator._shares_ancestor(
            ".product-card",
            SAMPLE_HTML,
            proposed_ancestors
        ) is False
    
    def test_shares_ancestor_empty_ancestors(self, calculator):
        """Test with empty ancestors list."""
        assert calculator._shares_ancestor(
            ".product-card",
            SAMPLE_HTML,
            []
        ) is False
    
    def test_shares_ancestor_no_match(self, calculator):
        """Test when selector doesn't match HTML."""
        assert calculator._shares_ancestor(
            ".nonexistent",
            SAMPLE_HTML,
            ["#main-content"]
        ) is False
    
    # === Tests for calculate_blast_radius ===
    
    @pytest.mark.asyncio
    async def test_calculate_blast_radius_with_impact(
        self, calculator, sample_selectors
    ):
        """Test blast radius calculation with affected selectors."""
        result = await calculator.calculate_blast_radius(
            proposed_selector=".buy-btn",
            html_content=SAMPLE_HTML,
            all_selectors=sample_selectors,
        )
        
        assert isinstance(result, BlastRadiusResult)
        assert result.proposed_selector == ".buy-btn"
        assert result.affected_count >= 0
        assert isinstance(result.severity, SeverityLevel)
    
    @pytest.mark.asyncio
    async def test_calculate_blast_radius_no_match(
        self, calculator, sample_selectors
    ):
        """Test blast radius when selector doesn't match."""
        result = await calculator.calculate_blast_radius(
            proposed_selector=".nonexistent",
            html_content=SAMPLE_HTML_NO_MATCH,
            all_selectors=sample_selectors,
        )
        
        assert result.affected_count == 0
        assert result.severity == SeverityLevel.LOW
        assert result.container_path == ""
    
    @pytest.mark.asyncio
    async def test_calculate_blast_radius_empty_selectors(
        self, calculator
    ):
        """Test blast radius with no other selectors."""
        result = await calculator.calculate_blast_radius(
            proposed_selector=".buy-btn",
            html_content=SAMPLE_HTML,
            all_selectors=[],
        )
        
        assert result.affected_count == 0
        assert result.severity == SeverityLevel.LOW


class TestBlastRadiusResult:
    """Tests for BlastRadiusResult dataclass."""
    
    def test_default_values(self):
        """Test default values for BlastRadiusResult."""
        result = BlastRadiusResult(
            proposed_selector=".test",
            affected_count=0,
        )
        
        assert result.affected_selectors == []
        assert result.affected_sports == []
        assert result.severity == SeverityLevel.LOW
        assert result.container_path == ""
    
    def test_with_values(self):
        """Test BlastRadiusResult with all values."""
        affected = [
            AffectedSelector(
                selector_string=".test",
                recipe_id=1,
                sport="football",
                confidence_score=0.8,
            )
        ]
        
        result = BlastRadiusResult(
            proposed_selector=".test",
            affected_count=1,
            affected_selectors=affected,
            affected_sports=["football"],
            severity=SeverityLevel.MEDIUM,
            container_path="#main",
        )
        
        assert result.affected_count == 1
        assert len(result.affected_selectors) == 1
        assert result.affected_sports == ["football"]
        assert result.severity == SeverityLevel.MEDIUM
        assert result.container_path == "#main"


class TestBlastRadiusUI:
    """Tests for BlastRadiusUI dataclass."""
    
    def test_from_result_low(self):
        """Test conversion from BlastRadiusResult with LOW severity."""
        result = BlastRadiusResult(
            proposed_selector=".test",
            affected_count=1,
            affected_selectors=[],
            affected_sports=["football"],
            severity=SeverityLevel.LOW,
            container_path="#main",
        )
        
        ui = BlastRadiusUI.from_result(result)
        
        assert ui.proposed_selector == ".test"
        assert ui.severity_badge == "green"
        assert ui.severity_label == "Low"
        assert ui.affected_count == 1
        assert ui.affected_sports == ["football"]
    
    def test_from_result_medium(self):
        """Test conversion from BlastRadiusResult with MEDIUM severity."""
        result = BlastRadiusResult(
            proposed_selector=".test",
            affected_count=3,
            affected_sports=["football", "basketball"],
            severity=SeverityLevel.MEDIUM,
        )
        
        ui = BlastRadiusUI.from_result(result)
        
        assert ui.severity_badge == "yellow"
        assert ui.severity_label == "Medium"
    
    def test_from_result_high(self):
        """Test conversion from BlastRadiusResult with HIGH severity."""
        result = BlastRadiusResult(
            proposed_selector=".test",
            affected_count=6,
            severity=SeverityLevel.HIGH,
        )
        
        ui = BlastRadiusUI.from_result(result)
        
        assert ui.severity_badge == "orange"
        assert ui.severity_label == "High"
    
    def test_from_result_critical(self):
        """Test conversion from BlastRadiusResult with CRITICAL severity."""
        result = BlastRadiusResult(
            proposed_selector=".test",
            affected_count=10,
            severity=SeverityLevel.CRITICAL,
        )
        
        ui = BlastRadiusUI.from_result(result)
        
        assert ui.severity_badge == "red"
        assert ui.severity_label == "Critical"
    
    def test_affected_selectors_preview(self):
        """Test affected selectors preview is limited to 5."""
        result = BlastRadiusResult(
            proposed_selector=".test",
            affected_count=10,
            affected_selectors=[
                AffectedSelector(f".test-{i}", i, "sport", 0.5)
                for i in range(10)
            ],
            severity=SeverityLevel.CRITICAL,
        )
        
        ui = BlastRadiusUI.from_result(result)
        
        assert len(ui.affected_selectors_preview) == 5
        assert ui.affected_selectors_preview[0] == ".test-0"
        assert ui.affected_selectors_preview[4] == ".test-4"
    
    def test_container_description_empty(self):
        """Test container description when empty."""
        result = BlastRadiusResult(
            proposed_selector=".test",
            affected_count=0,
            severity=SeverityLevel.LOW,
            container_path="",
        )
        
        ui = BlastRadiusUI.from_result(result)
        
        assert ui.container_description == "No shared containers"


class TestGetBlastRadiusCalculator:
    """Tests for module-level get_blast_radius_calculator function."""
    
    def test_returns_calculator_instance(self):
        """Test that function returns a BlastRadiusCalculator instance."""
        calc = get_blast_radius_calculator()
        assert isinstance(calc, BlastRadiusCalculator)
    
    def test_returns_same_instance(self):
        """Test that function returns the same instance."""
        calc1 = get_blast_radius_calculator()
        calc2 = get_blast_radius_calculator()
        assert calc1 is calc2
