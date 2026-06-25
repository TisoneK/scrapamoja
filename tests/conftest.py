"""
Pytest configuration and fixtures for Selector Engine tests.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# Test configuration
TEST_DATA_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser():
    """Launch Playwright browser for testing."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser: Browser):
    """Create a new Playwright page for each test."""
    context = await browser.new_context()
    page = await context.new_page()
    yield page
    await context.close()


@pytest.fixture
def mock_dom_context():
    """Create a mock DOM context for testing."""
    from src.selectors.context import DOMContext
    
    context = MagicMock(spec=DOMContext)
    context.page = AsyncMock()
    context.tab_context = "summary"
    context.url = "https://test.example.com/match/123"
    context.timestamp = "2024-01-01T00:00:00Z"
    context.metadata = {}
    return context


@pytest.fixture
def sample_html_content():
    """Sample HTML content for testing selectors."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Match Page</title>
    </head>
    <body>
        <div class="match-header">
            <div class="team home">
                <span class="team-name">Manchester United</span>
                <span class="score">2</span>
            </div>
            <div class="team away">
                <span class="team-name">Liverpool</span>
                <span class="score">1</span>
            </div>
        </div>
        <div class="match-details">
            <div class="status">FT</div>
            <div class="kickoff-time">15:00</div>
        </div>
        <div class="tabs">
            <div class="tab active" data-tab="summary">Summary</div>
            <div class="tab" data-tab="odds">Odds</div>
            <div class="tab" data-tab="h2h">H2H</div>
        </div>
        <div class="tab-content">
            <div class="summary-content active">
                <div class="statistics">
                    <div class="stat">
                        <span class="label">Possession</span>
                        <span class="home-value">65%</span>
                        <span class="away-value">35%</span>
                    </div>
                </div>
            </div>
            <div class="odds-content">
                <div class="odds-table">
                    <div class="odds-row">
                        <span class="bookmaker">Bet365</span>
                        <span class="home-odds">2.10</span>
                        <span class="draw-odds">3.40</span>
                        <span class="away-odds">3.20</span>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_selector_definition():
    """Sample semantic selector definition for testing."""
    from src.models.selector_models import SemanticSelector, StrategyPattern, ValidationRule
    
    return SemanticSelector(
        name="home_team_name",
        description="Home team name in match header",
        context="summary",
        confidence_threshold=0.8,
        strategies=[
            StrategyPattern(
                id="home_text_anchor",
                type="text_anchor",
                priority=1,
                config={
                    "anchor_text": "Manchester United",
                    "proximity_selector": ".team.home .team-name",
                    "case_sensitive": False
                }
            ),
            StrategyPattern(
                id="home_attribute_match",
                type="attribute_match",
                priority=2,
                config={
                    "attribute": "class",
                    "value_pattern": "team-name",
                    "element_tag": "span"
                }
            )
        ],
        validation_rules=[
            ValidationRule(
                type="regex",
                pattern=r"^[A-Za-z\s]+$",
                required=True,
                weight=0.4
            )
        ]
    )


@pytest.fixture
def mock_playwright_page():
    """Create a mock Playwright page for testing."""
    page = AsyncMock()
    
    # Mock query_selector
    mock_element = AsyncMock()
    mock_element.text_content.return_value = "Manchester United"
    mock_element.get_attribute.return_value = "team-name home"
    page.query_selector.return_value = mock_element
    
    # Mock wait_for_selector
    page.wait_for_selector.return_value = mock_element
    
    # Mock content
    page.content.return_value = "<html><body>Test content</body></html>"
    
    return page


@pytest.fixture
def temp_snapshot_dir(tmp_path):
    """Create a temporary directory for snapshot testing."""
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    return snapshot_dir


# Test markers for better test organization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "selector_engine: Tests for selector engine functionality"
    )
    config.addinivalue_line(
        "markers", "confidence_scoring: Tests for confidence scoring algorithms"
    )
    config.addinivalue_line(
        "markers", "drift_detection: Tests for drift detection functionality"
    )
    config.addinivalue_line(
        "markers", "snapshots: Tests for DOM snapshot functionality"
    )


# Helper functions for testing
async def setup_test_page(page: Page, html_content: str):
    """Set up a test page with given HTML content."""
    await page.set_content(html_content)
    await page.wait_for_load_state("networkidle")


def create_mock_selector_result(success: bool = True, confidence: float = 0.9):
    """Create a mock selector result for testing."""
    from src.models.selector_models import SelectorResult, ElementInfo
    
    if success:
        element_info = ElementInfo(
            tag_name="span",
            text_content="Test Content",
            attributes={"class": "test-class"},
            css_classes=["test-class"],
            dom_path="body.span.test",
            visibility=True,
            interactable=True
        )
        return SelectorResult(
            selector_name="test_selector",
            strategy_used="test_strategy",
            element_info=element_info,
            confidence_score=confidence,
            resolution_time=50.0,
            validation_results=[],
            success=True,
            timestamp="2024-01-01T00:00:00Z"
        )
    else:
        return SelectorResult(
            selector_name="test_selector",
            strategy_used="test_strategy",
            element_info=None,
            confidence_score=0.0,
            resolution_time=100.0,
            validation_results=[],
            success=False,
            timestamp="2024-01-01T00:00:00Z",
            failure_reason="Element not found"
        )
