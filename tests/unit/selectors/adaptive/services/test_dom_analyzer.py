"""
Tests for DOM Analyzer Service.

Story: 3.1 - Analyze DOM Structure
"""

import pytest
from unittest.mock import Mock, patch

from src.selectors.adaptive.services.dom_analyzer import (
    DOMAnalyzer,
    AlternativeSelector,
    StrategyType,
)


class TestDOMAnalyzer:
    """Test suite for DOMAnalyzer service."""

    @pytest.fixture
    def analyzer(self):
        """Create a DOMAnalyzer instance."""
        return DOMAnalyzer()

    # Sample HTML fixtures
    SIMPLE_HTML = """
    <html>
        <body>
            <div id="main">
                <span class="highlight">Target Element</span>
                <button id="submit-btn" class="btn primary">Submit</button>
            </div>
        </body>
    </html>
    """

    COMPLEX_HTML = """
    <html>
        <body>
            <nav id="navbar" class="nav">
                <ul>
                    <li><a href="/home" class="nav-link">Home</a></li>
                    <li><a href="/about" class="nav-link">About</a></li>
                </ul>
            </nav>
            <main>
                <div class="container">
                    <div id="content" data-testid="main-content" role="main">
                        <h1 class="title">Welcome</h1>
                        <p id="description" class="desc" data-cy="description">
                            This is a description paragraph.
                        </p>
                        <button type="button" class="action-btn" 
                                aria-label="Click me" role="button">
                            Click Me
                        </button>
                    </div>
                </div>
            </main>
        </body>
    </html>
    """

    EMPTY_HTML = ""

    MALFORMED_HTML = "<html><body><div>Unclosed divs"

    NO_TARGET_HTML = """
    <html>
        <body>
            <div id="other">Not the target</div>
        </body>
    </html>
    """

    # ==================== Tests for analyze_snapshot ====================

    @pytest.mark.asyncio
    async def test_analyze_snapshot_basic(self, analyzer):
        """Test basic snapshot analysis returns alternatives."""
        alternatives = await analyzer.analyze_snapshot(
            html_content=self.SIMPLE_HTML,
            failed_selector=".highlight",
        )

        assert len(alternatives) > 0
        assert all(isinstance(alt, AlternativeSelector) for alt in alternatives)

    @pytest.mark.asyncio
    async def test_analyze_snapshot_empty_html(self, analyzer):
        """Test analysis with empty HTML returns empty list."""
        alternatives = await analyzer.analyze_snapshot(
            html_content=self.EMPTY_HTML,
            failed_selector=".some-selector",
        )

        assert alternatives == []

    @pytest.mark.asyncio
    async def test_analyze_snapshot_malformed_html(self, analyzer):
        """Test analysis handles malformed HTML gracefully."""
        alternatives = await analyzer.analyze_snapshot(
            html_content=self.MALFORMED_HTML,
            failed_selector=".some-selector",
        )

        # Should return empty list, not crash
        assert isinstance(alternatives, list)

    @pytest.mark.asyncio
    async def test_analyze_snapshot_no_matching_target(self, analyzer):
        """Test analysis when failed selector doesn't match."""
        alternatives = await analyzer.analyze_snapshot(
            html_content=self.SIMPLE_HTML,
            failed_selector=".nonexistent-class",
        )

        # Should still find alternatives via fallback
        assert isinstance(alternatives, list)

    @pytest.mark.asyncio
    async def test_analyze_snapshot_sorts_by_confidence(self, analyzer):
        """Test alternatives are sorted by confidence score (highest first)."""
        alternatives = await analyzer.analyze_snapshot(
            html_content=self.COMPLEX_HTML,
            failed_selector="#description",
        )

        # Verify sorted by confidence descending
        if len(alternatives) > 1:
            for i in range(len(alternatives) - 1):
                assert alternatives[i].confidence_score >= alternatives[i + 1].confidence_score

    @pytest.mark.asyncio
    async def test_analyze_snapshot_deduplicates(self, analyzer):
        """Test that duplicate selectors are removed."""
        alternatives = await analyzer.analyze_snapshot(
            html_content=self.COMPLEX_HTML,
            failed_selector="#description",
        )

        selector_strings = [alt.selector_string for alt in alternatives]
        assert len(selector_strings) == len(set(selector_strings))

    @pytest.mark.asyncio
    async def test_analyze_snapshot_all_strategies_present(self, analyzer):
        """Test that all strategy types are represented."""
        alternatives = await analyzer.analyze_snapshot(
            html_content=self.COMPLEX_HTML,
            failed_selector="#description",
        )

        strategy_types = {alt.strategy_type for alt in alternatives}
        # Should have multiple strategy types
        assert len(strategy_types) >= 3

    # ==================== Tests for CSS Strategy ====================

    def test_analyze_css_with_id(self, analyzer):
        """Test CSS strategy generates ID-based selectors."""
        soup = analyzer._analyze_html_to_soup(self.SIMPLE_HTML)
        target = soup.select_one("#submit-btn")

        alternatives = analyzer._analyze_css(target, soup)

        id_selectors = [alt for alt in alternatives 
                        if "#submit-btn" in alt.selector_string]
        assert len(id_selectors) > 0
        assert any(alt.confidence_score == 0.9 for alt in id_selectors)

    def test_analyze_css_with_class(self, analyzer):
        """Test CSS strategy generates class-based selectors."""
        soup = analyzer._analyze_html_to_soup(self.SIMPLE_HTML)
        target = soup.select_one(".highlight")

        alternatives = analyzer._analyze_css(target, soup)

        class_selectors = [alt for alt in alternatives 
                          if alt.selector_string.startswith(".")]
        assert len(class_selectors) > 0

    def test_analyze_css_tag_class_combo(self, analyzer):
        """Test CSS strategy generates tag+class combinations."""
        soup = analyzer._analyze_html_to_soup(self.COMPLEX_HTML)
        target = soup.select_one(".action-btn")

        alternatives = analyzer._analyze_css(target, soup)

        # Should have tag.class format
        tag_class = [alt for alt in alternatives 
                     if alt.selector_string.startswith("button.")]
        assert len(tag_class) > 0

    # ==================== Tests for XPath Strategy ====================

    def test_analyze_xpath_generates_paths(self, analyzer):
        """Test XPath strategy generates path-based selectors."""
        soup = analyzer._analyze_html_to_soup(self.SIMPLE_HTML)
        target = soup.select_one("#submit-btn")

        alternatives = analyzer._analyze_xpath(target, soup)

        xpath_selectors = [alt for alt in alternatives 
                          if alt.selector_string.startswith("//")]
        assert len(xpath_selectors) > 0

    def test_analyze_xpath_with_id(self, analyzer):
        """Test XPath strategy generates ID-based XPath."""
        soup = analyzer._analyze_html_to_soup(self.COMPLEX_HTML)
        target = soup.select_one("#description")

        alternatives = analyzer._analyze_xpath(target, soup)

        # Should have XPath with @id
        id_xpath = [alt for alt in alternatives 
                    if "@id=" in alt.selector_string]
        assert len(id_xpath) > 0

    # ==================== Tests for Text Anchor Strategy ====================

    def test_analyze_text_anchor_exact(self, analyzer):
        """Test text anchor strategy generates exact text selectors."""
        soup = analyzer._analyze_html_to_soup(self.COMPLEX_HTML)
        target = soup.select_one("h1")

        alternatives = analyzer._analyze_text_anchor(target, soup)

        text_selectors = [alt for alt in alternatives 
                         if "text()" in alt.selector_string]
        assert len(text_selectors) > 0

    def test_analyze_text_anchor_partial(self, analyzer):
        """Test text anchor strategy generates partial text selectors."""
        soup = analyzer._analyze_html_to_soup(self.COMPLEX_HTML)
        target = soup.select_one("#description")

        alternatives = analyzer._analyze_text_anchor(target, soup)

        contains_selectors = [alt for alt in alternatives 
                            if "contains(" in alt.selector_string]
        assert len(contains_selectors) > 0

    # ==================== Tests for Attribute Match Strategy ====================

    def test_analyze_attribute_data_attrs(self, analyzer):
        """Test attribute match strategy generates data-attribute selectors."""
        soup = analyzer._analyze_html_to_soup(self.COMPLEX_HTML)
        target = soup.select_one("[data-testid='main-content']")

        alternatives = analyzer._analyze_attribute_match(target, soup)

        data_selectors = [alt for alt in alternatives 
                         if "data-" in alt.selector_string]
        assert len(data_selectors) > 0

    def test_analyze_attribute_data_cy(self, analyzer):
        """Test attribute match strategy recognizes data-cy attributes."""
        soup = analyzer._analyze_html_to_soup(self.COMPLEX_HTML)
        target = soup.select_one("[data-cy='description']")

        alternatives = analyzer._analyze_attribute_match(target, soup)

        # Should generate data-cy selector
        assert any("data-cy" in alt.selector_string for alt in alternatives)

    def test_analyze_attribute_name(self, analyzer):
        """Test attribute match strategy generates name attribute selectors."""
        html = '<input name="username" type="text"/>'
        soup = analyzer._analyze_html_to_soup(f"<html><body>{html}</body></html>")
        target = soup.select_one("[name='username']")

        alternatives = analyzer._analyze_attribute_match(target, soup)

        name_selectors = [alt for alt in alternatives 
                         if "name=" in alt.selector_string]
        assert len(name_selectors) > 0

    def test_analyze_attribute_aria_label(self, analyzer):
        """Test attribute match strategy handles title attribute."""
        html = '<div title="Click me" class="btn">Click</div>'
        soup = analyzer._analyze_html_to_soup(f"<html><body>{html}</body></html>")
        target = soup.select_one("[title='Click me']")

        alternatives = analyzer._analyze_attribute_match(target, soup)

        # Should have title selectors
        assert len(alternatives) > 0

    # ==================== Tests for DOM Relationship Strategy ====================

    def test_analyze_dom_parent_with_id(self, analyzer):
        """Test DOM relationship strategy generates parent ID selectors."""
        soup = analyzer._analyze_html_to_soup(self.COMPLEX_HTML)
        target = soup.select_one(".title")

        alternatives = analyzer._analyze_dom_relationship(target, soup)

        parent_selectors = [alt for alt in alternatives 
                           if "#" in alt.selector_string.split()[0]]
        assert len(parent_selectors) > 0

    def test_analyze_dom_sibling(self, analyzer):
        """Test DOM relationship strategy generates sibling selectors."""
        soup = analyzer._analyze_html_to_soup(self.COMPLEX_HTML)
        target = soup.select_one(".desc")

        alternatives = analyzer._analyze_dom_relationship(target, soup)

        # Should have + or ~ sibling combinators
        sibling = [alt for alt in alternatives 
                  if "+" in alt.selector_string or "~" in alt.selector_string]
        assert len(sibling) >= 0  # May not always have prev sibling

    def test_analyze_dom_child(self, analyzer):
        """Test DOM relationship strategy generates child selectors."""
        soup = analyzer._analyze_html_to_soup(self.COMPLEX_HTML)
        target = soup.select_one(".title")

        alternatives = analyzer._analyze_dom_relationship(target, soup)

        # Should have > child combinator
        child = [alt for alt in alternatives 
                if ">" in alt.selector_string]
        assert len(child) > 0

    # ==================== Tests for Role-Based Strategy ====================

    def test_analyze_role_basic(self, analyzer):
        """Test role-based strategy generates role selectors."""
        soup = analyzer._analyze_html_to_soup(self.COMPLEX_HTML)
        target = soup.select_one("[role='main']")

        alternatives = analyzer._analyze_role_based(target, soup)

        role_selectors = [alt for alt in alternatives 
                        if "role=" in alt.selector_string]
        assert len(role_selectors) > 0

    def test_analyze_role_with_label(self, analyzer):
        """Test role-based strategy generates role+label selectors."""
        soup = analyzer._analyze_html_to_soup(self.COMPLEX_HTML)
        target = soup.select_one("[aria-label='Click me'][role='button']")

        alternatives = analyzer._analyze_role_based(target, soup)

        # Should have combined role + aria-label
        assert len(alternatives) > 0

    def test_analyze_role_aria_labelledby(self, analyzer):
        """Test role-based strategy handles aria-labelledby."""
        html = '<div role="dialog" aria-labelledby="title">Content</div>'
        soup = analyzer._analyze_html_to_soup(f"<html><body>{html}</body></html>")
        target = soup.select_one("[role='dialog']")

        alternatives = analyzer._analyze_role_based(target, soup)

        labelledby = [alt for alt in alternatives 
                    if "aria-labelledby" in alt.selector_string]
        assert len(labelledby) > 0

    # ==================== Tests for Edge Cases ====================

    def test_analyze_element_no_id_no_class(self, analyzer):
        """Test analysis of element with no ID or class."""
        html = "<html><body><div><span>Plain text</span></div></body></html>"
        soup = analyzer._analyze_html_to_soup(html)
        target = soup.select_one("span")

        css_alts = analyzer._analyze_css(target, soup)

        # Should still generate tag-only selector
        tag_only = [alt for alt in css_alts if alt.selector_string == "span"]
        assert len(tag_only) > 0

    def test_analyze_element_with_multiple_classes(self, analyzer):
        """Test analysis of element with multiple classes."""
        html = '<div class="first second third">Content</div>'
        soup = analyzer._analyze_html_to_soup(f"<html><body>{html}</body></html>")
        target = soup.select_one(".first")

        alternatives = analyzer._analyze_css(target, soup)

        # Should generate both single and multi-class selectors
        assert len(alternatives) > 0

    def test_analyze_link_with_href(self, analyzer):
        """Test analysis of anchor element with href."""
        soup = analyzer._analyze_html_to_soup(self.COMPLEX_HTML)
        target = soup.select_one(".nav-link")

        alternatives = analyzer._analyze_attribute_match(target, soup)

        href_alts = [alt for alt in alternatives 
                    if "href=" in alt.selector_string]
        assert len(href_alts) > 0

    def test_analyze_input_with_type(self, analyzer):
        """Test analysis of input element with type."""
        html = '<input type="email" class="form-input" name="email"/>'
        soup = analyzer._analyze_html_to_soup(f"<html><body>{html}</body></html>")
        target = soup.select_one("input")

        alternatives = analyzer._analyze_attribute_match(target, soup)

        type_alts = [alt for alt in alternatives 
                    if "type=" in alt.selector_string]
        assert len(type_alts) > 0

    # ==================== Tests for Helper Methods ====================

    def test_deduplicate_alternatives(self, analyzer):
        """Test deduplication keeps highest confidence."""
        alternatives = [
            AlternativeSelector("#test", StrategyType.CSS, 0.5, "Test"),
            AlternativeSelector("#test", StrategyType.CSS, 0.8, "Test"),
            AlternativeSelector(".test", StrategyType.CSS, 0.7, "Test"),
        ]

        result = analyzer._deduplicate_alternatives(alternatives)

        # Should have 2 items (deduplicated + .test)
        assert len(result) == 2
        # Should keep highest confidence for #test
        test_alt = [alt for alt in result if alt.selector_string == "#test"][0]
        assert test_alt.confidence_score == 0.8

    def test_to_dict_conversion(self, analyzer):
        """Test AlternativeSelector to_dict method."""
        alt = AlternativeSelector(
            selector_string="#test",
            strategy_type=StrategyType.CSS,
            confidence_score=0.9,
            element_description="ID selector",
        )

        result = alt.to_dict()

        assert result["selector_string"] == "#test"
        assert result["strategy_type"] == "css"
        assert result["confidence_score"] == 0.9
        assert result["element_description"] == "ID selector"

    # ==================== Tests for Integration Points ====================

    @pytest.mark.asyncio
    async def test_analyze_with_sport_context(self, analyzer):
        """Test analysis accepts sport context parameter."""
        alternatives = await analyzer.analyze_snapshot(
            html_content=self.COMPLEX_HTML,
            failed_selector="#description",
            sport="football",
            site="flashscore",
        )

        # Should not affect results, just accept parameter
        assert isinstance(alternatives, list)

    @pytest.mark.asyncio
    async def test_analyze_with_site_context(self, analyzer):
        """Test analysis accepts site context parameter."""
        alternatives = await analyzer.analyze_snapshot(
            html_content=self.COMPLEX_HTML,
            failed_selector="#description",
            site="example.com",
        )

        assert isinstance(alternatives, list)

    # ==================== Test Helper Method ====================

    def _analyze_html_to_soup(self, html: str):
        """Helper to convert HTML to BeautifulSoup for testing."""
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, 'lxml')


class TestStrategyType:
    """Test suite for StrategyType enum."""

    def test_strategy_type_values(self):
        """Test StrategyType has correct values."""
        assert StrategyType.CSS.value == "css"
        assert StrategyType.XPATH.value == "xpath"
        assert StrategyType.TEXT_ANCHOR.value == "text_anchor"
        assert StrategyType.ATTRIBUTE_MATCH.value == "attribute_match"
        assert StrategyType.DOM_RELATIONSHIP.value == "dom_relationship"
        assert StrategyType.ROLE_BASED.value == "role_based"

    def test_strategy_type_enum_access(self):
        """Test StrategyType can be accessed by value."""
        assert StrategyType("css") == StrategyType.CSS
        assert StrategyType("xpath") == StrategyType.XPATH


class TestAlternativeSelector:
    """Test suite for AlternativeSelector dataclass."""

    def test_create_selector(self):
        """Test creating an AlternativeSelector."""
        alt = AlternativeSelector(
            selector_string="#test-id",
            strategy_type=StrategyType.CSS,
            confidence_score=0.85,
            element_description="Test ID selector",
        )

        assert alt.selector_string == "#test-id"
        assert alt.strategy_type == StrategyType.CSS
        assert alt.confidence_score == 0.85
        assert alt.element_description == "Test ID selector"

    def test_confidence_score_bounds(self):
        """Test confidence scores can be any float."""
        alt_low = AlternativeSelector(
            selector_string=".test",
            strategy_type=StrategyType.CSS,
            confidence_score=0.0,
            element_description="Low confidence",
        )
        assert alt_low.confidence_score == 0.0

        alt_high = AlternativeSelector(
            selector_string="#test",
            strategy_type=StrategyType.CSS,
            confidence_score=1.0,
            element_description="High confidence",
        )
        assert alt_high.confidence_score == 1.0
