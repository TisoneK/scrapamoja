# Quickstart Guide: Selector Engine Integration

**Date**: 2025-01-29  
**Feature**: 012-selector-engine-integration  
**Purpose**: Implementation guide for selector engine integration

## Overview

This guide demonstrates how to integrate the selector engine into the browser lifecycle example to showcase robust element location, fallback strategies, and telemetry capture.

## Prerequisites

- Python 3.11+ installed
- Playwright browsers installed: `playwright install`
- Existing selector engine implementation available in `src/selectors/`
- Browser lifecycle example at `examples/browser_lifecycle_example.py`

## Implementation Steps

### Step 1: Import Selector Engine Components

Add these imports to `examples/browser_lifecycle_example.py`:

```python
from src.selectors import (
    get_selector_engine,
    SelectorEngine,
    DOMContext,
    TabContextManager
)
from src.selectors.strategies import (
    TextAnchorStrategy,
    AttributeMatchStrategy,
    DOMRelationshipStrategy,
    RoleBasedStrategy
)
```

### Step 2: Create Selector Configuration Class

```python
class SelectorConfiguration:
    """Configuration for multi-strategy element location"""
    
    def __init__(self, element_purpose: str, strategies: List[Dict]):
        self.element_purpose = element_purpose
        self.strategies = strategies
        self.confidence_threshold = 0.7
        self.timeout_per_strategy_ms = 1500
        self.enable_fallback = True

def get_wikipedia_search_config() -> SelectorConfiguration:
    """Configuration for Wikipedia search input field"""
    strategies = [
        {
            "type": "css",
            "selector": "input#searchInput",
            "priority": 1,
            "expected_attributes": {"type": "search", "name": "search"}
        },
        {
            "type": "xpath", 
            "selector": "//input[@name='search']",
            "priority": 2,
            "expected_attributes": {"type": "search"}
        },
        {
            "type": "text",
            "selector": "Search",
            "priority": 3,
            "search_context": "input"
        }
    ]
    return SelectorConfiguration("Wikipedia search input field", strategies)

def get_search_result_config() -> SelectorConfiguration:
    """Configuration for Wikipedia search result links"""
    strategies = [
        {
            "type": "css",
            "selector": ".mw-search-result-heading a",
            "priority": 1
        },
        {
            "type": "xpath",
            "selector": "//div[@class='mw-search-result-heading']//a",
            "priority": 2
        },
        {
            "type": "text",
            "selector": "Python",
            "priority": 3,
            "search_context": "link"
        }
    ]
    return SelectorConfiguration("Wikipedia search result link", strategies)
```

### Step 3: Implement Selector Integration Class

```python
class SelectorEngineIntegration:
    """Integration layer for selector engine operations"""
    
    def __init__(self):
        self.selector_engine = get_selector_engine()
        self.operations = []
        self.interactions = []
        
    async def locate_element(
        self,
        page: Page,
        config: SelectorConfiguration,
        timeout_ms: int = 5000
    ) -> Optional[ElementHandle]:
        """
        Locate element using multi-strategy selector engine
        
        Returns element handle if successful, None if all strategies fail
        """
        operation_id = f"locate_{config.element_purpose.replace(' ', '_')}"
        start_time = time.time()
        
        try:
            # Create DOM context for selector engine
            dom_context = DOMContext(page)
            
            # Try each strategy in priority order
            for strategy_config in sorted(config.strategies, key=lambda x: x['priority']):
                strategy_result = await self._try_strategy(
                    dom_context, strategy_config, operation_id
                )
                
                if strategy_result['success'] and strategy_result['confidence'] >= config.confidence_threshold:
                    # Log successful operation
                    self._log_operation_success(operation_id, config, strategy_result, start_time)
                    return strategy_result['element']
                    
            # All strategies failed
            self._log_operation_failure(operation_id, config, start_time)
            return None
            
        except Exception as e:
            self._log_operation_error(operation_id, config, e, start_time)
            return None
    
    async def interact_with_element(
        self,
        page: Page,
        element: ElementHandle,
        interaction_type: str,
        interaction_data: Optional[Dict] = None
    ) -> Dict:
        """Perform interaction with located element"""
        interaction_id = f"{interaction_type}_{int(time.time())}"
        start_time = time.time()
        
        try:
            if interaction_type == "click":
                await element.click()
            elif interaction_type == "type" and interaction_data:
                await element.fill(interaction_data.get("text", ""))
            elif interaction_type == "scroll":
                await element.scroll_into_view_if_needed()
            
            duration_ms = int((time.time() - start_time) * 1000)
            result = {
                "interaction_id": interaction_id,
                "success": True,
                "duration_ms": duration_ms
            }
            
            self._log_interaction_success(interaction_id, interaction_type, result)
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = {
                "interaction_id": interaction_id,
                "success": False,
                "duration_ms": duration_ms,
                "error": str(e)
            }
            
            self._log_interaction_error(interaction_id, interaction_type, result)
            return result
```

### Step 4: Enhance Browser Lifecycle Example

```python
class BrowserLifecycleExample:
    def __init__(self):
        self.browser_manager = get_browser_manager()
        self.selector_integration = SelectorEngineIntegration()
        
    async def perform_wikipedia_search(self, page: Page, search_term: str):
        """Enhanced Wikipedia search using selector engine"""
        
        # Step 1: Locate search input using selector engine
        search_config = get_wikipedia_search_config()
        search_input = await self.selector_integration.locate_element(
            page=page,
            config=search_config
        )
        
        if not search_input:
            print("❌ Failed to locate search input using all strategies")
            return False
        
        print("✅ Located search input using selector engine")
        
        # Step 2: Type search term with stealth behavior
        await self.selector_integration.interact_with_element(
            page=page,
            element=search_input,
            interaction_type="type",
            interaction_data={"text": search_term}
        )
        
        # Step 3: Press Enter and wait for results
        await page.keyboard.press("Enter")
        await page.wait_for_load_state("networkidle")
        
        # Step 4: Locate search results using selector engine
        result_config = get_search_result_config()
        search_results = await self.selector_integration.locate_element(
            page=page,
            config=result_config
        )
        
        if not search_results:
            print("❌ Failed to locate search results")
            return False
        
        print("✅ Located search results using selector engine")
        
        # Step 5: Click first result
        await self.selector_integration.interact_with_element(
            page=page,
            element=search_results,
            interaction_type="click"
        )
        
        return True
```

### Step 5: Add Telemetry and Logging

```python
    def _log_operation_success(self, operation_id: str, config: SelectorConfiguration, 
                              strategy_result: Dict, start_time: float):
        """Log successful selector operation"""
        duration_ms = int((time.time() - start_time) * 1000)
        
        print(f"✅ Selector operation successful: {config.element_purpose}")
        print(f"   Strategy: {strategy_result['type']}")
        print(f"   Confidence: {strategy_result['confidence']:.2f}")
        print(f"   Duration: {duration_ms}ms")
        
        # Store operation data for telemetry
        self.operations.append({
            "operation_id": operation_id,
            "element_purpose": config.element_purpose,
            "successful_strategy": strategy_result['type'],
            "confidence_score": strategy_result['confidence'],
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def get_telemetry_summary(self) -> Dict:
        """Generate telemetry summary for the session"""
        if not self.operations:
            return {}
            
        total_operations = len(self.operations)
        successful_operations = len([op for op in self.operations if op.get("confidence_score", 0) > 0.7])
        
        return {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "success_rate": successful_operations / total_operations,
            "average_confidence": sum(op.get("confidence_score", 0) for op in self.operations) / total_operations,
            "total_duration_ms": sum(op.get("duration_ms", 0) for op in self.operations),
            "strategies_used": list(set(op.get("successful_strategy") for op in self.operations))
        }
```

### Step 6: Update Main Execution

```python
async def main():
    """Enhanced main function with selector engine integration"""
    example = BrowserLifecycleExample()
    
    try:
        # Create browser session
        session = await example.browser_manager.create_session(
            configuration=BrowserConfiguration(
                browser_type=BrowserType.CHROMIUM,
                headless=True
            )
        )
        
        # Navigate to Wikipedia
        page = await session.get_or_create_tab()
        await page.goto("https://en.wikipedia.org")
        
        # Perform search using selector engine
        success = await example.perform_wikipedia_search(page, "Python programming")
        
        if success:
            print("✅ Wikipedia search completed using selector engine")
            
            # Display telemetry
            telemetry = example.selector_integration.get_telemetry_summary()
            print(f"📊 Telemetry: {telemetry}")
        else:
            print("❌ Wikipedia search failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await example.browser_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

## Running the Enhanced Example

```bash
# Set test mode for additional logging
$env:TEST_MODE=1

# Run the enhanced example
python -m examples.browser_lifecycle_example
```

## Expected Output

```
✅ Located search input using selector engine
✅ Selector operation successful: Wikipedia search input field
   Strategy: css
   Confidence: 0.92
   Duration: 45ms
✅ Located search results using selector engine
✅ Selector operation successful: Wikipedia search result link
   Strategy: css
   Confidence: 0.88
   Duration: 67ms
✅ Wikipedia search completed using selector engine
📊 Telemetry: {
    "total_operations": 2,
    "successful_operations": 2,
    "success_rate": 1.0,
    "average_confidence": 0.9,
    "total_duration_ms": 112,
    "strategies_used": ["css"]
}
```

## Verification Commands

```powershell
# Verify selector engine usage in logs
Get-Content data/logs/*.log | Select-String "selector|element_found" -Context 2,2

# Check telemetry data
Get-ChildItem data/telemetry/ -Filter "*.json" | ForEach-Object { 
    Write-Host "Telemetry: $($_.Name)"
    Get-Content $_.FullName | ConvertFrom-Json
}

# Verify snapshots with selector data
Get-ChildItem data/snapshots/ -Filter "*.json" | ForEach-Object {
    $snapshot = Get-Content $_.FullName | ConvertFrom-Json
    if ($snapshot.selector_operations) {
        Write-Host "✅ Selector operations found in $($_.Name)"
    }
}
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure selector engine is properly installed in `src/selectors/`
2. **Timeout issues**: Increase timeout values in configuration
3. **Low confidence scores**: Adjust confidence thresholds or improve selectors
4. **Missing telemetry**: Check log directory permissions

### Debug Mode

Enable debug logging by setting environment variable:
```bash
$env:DEBUG_SELECTOR=1
```

This will provide detailed strategy attempt information and timing data.
