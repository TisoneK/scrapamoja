#!/usr/bin/env python3
"""
Wikipedia Selector Configuration Demo

This script demonstrates the YAML selector configurations using the actual
Wikipedia HTML structure from both main page and article pages.

Usage:
    python -m examples.wikipedia_selector_demo
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the examples directory to the path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from selector_config_loader import get_selector_config, list_selector_configs
    YAML_CONFIG_AVAILABLE = True
except ImportError:
    print("❌ YAML config loader not available")
    sys.exit(1)


def print_separator(title):
    """Print a formatted separator with title."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def demonstrate_configurations():
    """Demonstrate all available selector configurations."""
    print_separator("WIKIPEDIA SELECTOR CONFIGURATIONS DEMONSTRATION")
    
    print("This demo showcases selector configurations based on actual Wikipedia HTML structure:")
    print("• Main page (wikipedia.org) with pure-form style search")
    print("• Article pages with Vector 2022 search interface")
    print("• Search results pages with result listings")
    print("• Various page elements (navigation, TOC, external links, etc.)")
    
    # Get all available configurations
    available_configs = list_selector_configs()
    print(f"\n📋 Available configurations: {len(available_configs)}")
    
    # Demonstrate each configuration with detailed analysis
    for config_name in sorted(available_configs):
        try:
            config = get_selector_config(config_name)
            
            print(f"\n🔧 Configuration: {config_name}")
            print(f"   Purpose: {config.element_purpose}")
            print(f"   Strategies: {len(config.strategies)}")
            print(f"   Confidence threshold: {config.confidence_threshold}")
            print(f"   Timeout: {config.timeout_per_strategy_ms}ms")
            print(f"   Fallback enabled: {config.enable_fallback}")
            
            # Analyze strategies
            print(f"   Strategy breakdown:")
            css_count = sum(1 for s in config.strategies if s.type == "css")
            xpath_count = sum(1 for s in config.strategies if s.type == "xpath")
            text_count = sum(1 for s in config.strategies if s.type == "text")
            
            print(f"     • CSS selectors: {css_count}")
            print(f"     • XPath selectors: {xpath_count}")
            print(f"     • Text selectors: {text_count}")
            
            # Show strategy details
            for i, strategy in enumerate(config.strategies, 1):
                print(f"     {i}. {strategy.type.upper()} - {strategy.selector}")
                if strategy.expected_attributes:
                    attrs = ", ".join(f"{k}='{v}'" for k, v in strategy.expected_attributes.items())
                    print(f"        Expected: {attrs}")
                if strategy.search_context:
                    print(f"        Context: {strategy.search_context}")
                if strategy.description:
                    print(f"        Description: {strategy.description}")
            
        except Exception as e:
            print(f"❌ Error loading '{config_name}': {e}")


def analyze_html_compatibility():
    """Analyze compatibility with different Wikipedia page types."""
    print_separator("HTML COMPATIBILITY ANALYSIS")
    
    print("Based on analysis of Wikipedia HTML structure:")
    print()
    
    # Main page analysis
    print("🏠 MAIN PAGE (wikipedia.org):")
    print("   • Search input: input#searchInput (type='text')")
    print("   • Search button: button[type='submit']")
    print("   • Featured content: .central-featured")
    print("   • Language links: #p-lang a")
    print("   • Navigation: .other-project-link")
    
    # Article page analysis
    print("\n📄 ARTICLE PAGE (Vector 2022):")
    print("   • Search input: .mw-searchInput (type='search')")
    print("   • Search button: .cdx-search-input__end-button")
    print("   • Article title: #firstHeading")
    print("   • Article content: #mw-content-text")
    print("   • Table of contents: #toc")
    print("   • External links: .external.text")
    
    # Search results page analysis
    print("\n🔍 SEARCH RESULTS PAGE:")
    print("   • Result links: .mw-search-result-heading a")
    print("   • Result data: .mw-search-result-data a")
    print("   • Search input: .mw-searchInput")
    print("   • Navigation: .mw-search-result-list")
    
    print("\n✅ Cross-page compatibility:")
    print("   • Universal search: input[@name='search']")
    print("   • Universal buttons: //form//button")
    print("   • Universal links: //a")
    print("   • Text-based fallbacks for dynamic content")


def demonstrate_best_practices():
    """Demonstrate selector engineering best practices."""
    print_separator("SELECTOR ENGINEERING BEST PRACTICES")
    
    print("🎯 Priority Strategy:")
    print("   1. Most specific selectors first (ID > Class > Attribute > Tag)")
    print("   2. CSS selectors for performance")
    print("   3. XPath for complex relationships")
    print("   4. Text-based as final fallback")
    print()
    
    print("🛡️ Robustness Features:")
    print("   • Multiple fallback strategies per element")
    print("   • Expected attribute validation")
    print("   • Context-aware searching")
    print("   • Confidence scoring thresholds")
    print()
    
    print("📊 Performance Considerations:")
    print("   • CSS selectors: Fastest execution")
    print("   • XPath: Moderate overhead, powerful")
    print("   • Text-based: Slowest, most flexible")
    print("   • Timeout per strategy: 1500ms")
    print()
    
    print("🔧 Configuration Management:")
    print("   • YAML-based declarative configs")
    print("   • Version-controlled selector definitions")
    print("   • Environment-specific overrides")
    print("   • Runtime validation and error handling")


def show_usage_examples():
    """Show practical usage examples."""
    print_separator("USAGE EXAMPLES")
    
    print("📝 Basic Usage:")
    print("```python")
    print("from selector_config_loader import get_selector_config")
    print()
    print("# Load search configuration")
    print("search_config = get_selector_config('search_input')")
    print()
    print("# Use with selector engine")
    print("element = await selector_engine.locate_element(page, search_config)")
    print("```")
    print()
    
    print("🔄 Fallback Strategy:")
    print("```python")
    print("# Try multiple configurations")
    print("configs = [")
    print("    get_selector_config('search_input'),")
    print("    get_selector_config('main_page_content')")
    print("]")
    print()
    print("for config in configs:")
    print("    element = await selector_engine.locate_element(page, config)")
    print("    if element:")
    print("        break  # Found with this config")
    print("```")
    print()
    
    print("🎛️ Environment Configuration:")
    print("```bash")
    print("# Enable debug mode")
    print("export DEBUG_SELECTOR=1")
    print()
    print("# Run example")
    print("python -m examples.browser_lifecycle_example")
    print("```")


def main():
    """Run the complete demonstration."""
    print("🌍 Wikipedia Selector Configuration Demonstration")
    print("=" * 60)
    
    try:
        # Check PyYAML availability
        import yaml
        print(f"✅ PyYAML version: {yaml.__version__}")
    except ImportError:
        print("❌ PyYAML not installed. Install with: pip install PyYAML")
        return False
    
    # Run demonstrations
    demonstrate_configurations()
    analyze_html_compatibility()
    demonstrate_best_practices()
    show_usage_examples()
    
    print_separator("SUMMARY")
    print("🎉 YAML selector configurations successfully demonstrated!")
    print()
    print("📚 Key benefits:")
    print("   • 10 comprehensive configurations for Wikipedia")
    print("   • Cross-page compatibility (main, article, search)")
    print("   • Multi-strategy fallback mechanisms")
    print("   • Production-ready selector engineering")
    print("   • Easy maintenance and updates")
    print()
    print("🚀 Ready for integration with:")
    print("   • Browser lifecycle examples")
    print("   • Web scraping workflows")
    print("   • Automated testing frameworks")
    print("   • Content extraction pipelines")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
