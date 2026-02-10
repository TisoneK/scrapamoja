# YAML Selector Configuration Examples

This directory contains example YAML selector configurations for the YAML-Based Selector Configuration System.

## Directory Structure

```
config/
├── main/                    # Main page selectors
│   └── page_selectors.yaml
├── fixture/                 # Fixture/match list selectors
│   ├── _context.yaml       # Context defaults for fixtures
│   └── match_list.yaml     # Match list selectors
└── match/                   # Match detail selectors
    ├── _context.yaml       # Context defaults for matches
    └── tabs/               # Tab-specific selectors
        ├── primary/
        │   └── match_overview.yaml
        ├── secondary/
        │   └── match_statistics.yaml
        └── tertiary/
            └── match_comments.yaml
```

## Configuration Files

### Main Configuration (`main/page_selectors.yaml`)
Contains selectors for main navigation pages including:
- Navigation menus and links
- Page titles and content areas
- Footer sections
- Loading indicators

### Fixture Configuration (`fixture/`)
Contains selectors for fixture/match list pages:
- `match_list.yaml`: Match list containers, individual match items, team names, scores
- `_context.yaml`: Context defaults for all fixture configurations

### Match Configuration (`match/`)
Contains selectors for detailed match pages:
- `_context.yaml`: Context defaults for all match configurations
- `tabs/primary/match_overview.yaml`: Overview tab with match details, lineups, events
- `tabs/secondary/match_statistics.yaml`: Statistics tab with team stats, charts
- `tabs/tertiary/match_comments.yaml`: Comments tab with user discussions

## Key Features Demonstrated

### 1. Hierarchical Inheritance
- Context files (`_context.yaml`) provide defaults for child configurations
- Child configurations inherit and can override parent defaults
- Strategy templates can be inherited from parent contexts

### 2. Strategy Templates
- Reusable strategy definitions (e.g., `navigation_link`, `team_name`)
- Parameterized templates with validation and confidence settings
- Template references in selector definitions

### 3. Context-Aware Selectors
- Selectors organized by context (e.g., `main.navigation`, `fixture.list`, `match.tabs.primary`)
- Context-specific validation and confidence scoring
- Hierarchical context structure for precise targeting

### 4. Multi-Strategy Resolution
- Multiple strategies per selector with priority ordering
- Fallback strategies for robust element detection
- Strategy type diversity (CSS, text anchor, attribute match, role-based)

### 5. Validation Rules
- Type-specific validation (string, number, boolean, array, object)
- Length constraints and pattern matching
- Required vs optional field validation

### 6. Confidence Scoring
- Per-selector confidence thresholds and weights
- Context-specific confidence boost factors
- Strategy-specific confidence configurations

## Usage Examples

### Basic Selector Definition
```yaml
page_title:
  description: "Main page title"
  context: "main.content"
  strategies:
    - type: "css_selector"
      parameters:
        selector: "title, h1, .page-title"
      priority: 1
  validation:
    required: true
    type: "string"
    min_length: 3
  confidence:
    threshold: 0.9
```

### Template Usage
```yaml
home_team:
  description: "Home team name"
  context: "fixture.match"
  strategies:
    - template: "team_name"
      priority: 1
  validation:
    required: true
    type: "string"
```

### Context Defaults Inheritance
```yaml
# In _context.yaml
context_defaults:
  page_type: "match"
  wait_strategy: "network_idle"
  timeout: 10000

# Child configurations inherit these defaults
# and can override them if needed
```

## Best Practices

1. **Use Semantic Names**: Choose descriptive, semantic selector names
2. **Organize by Context**: Group selectors by their usage context
3. **Provide Fallbacks**: Include multiple strategies for robustness
4. **Validate Thoroughly**: Use appropriate validation rules
5. **Set Realistic Confidence**: Configure confidence thresholds based on selector reliability
6. **Document Clearly**: Provide clear descriptions for each selector
7. **Use Templates**: Leverage strategy templates to reduce duplication

## Integration

These configurations can be loaded using the ConfigurationLoader:

```python
from src.selectors.engine.configuration import ConfigurationLoader

loader = ConfigurationLoader()
config = await loader.load_configuration(Path("config/main/page_selectors.yaml"))
```

The system will automatically handle inheritance, validation, and semantic indexing.
