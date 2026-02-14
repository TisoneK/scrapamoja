# Scrapamoja Workflows

This directory contains standardized workflows for system operations and debugging.

## 📂 Current Structure

```
docs/workflows/
├── workflows.start.md                    # Main entry point (this file)
├── selectors/
│   ├── workflows.selectors.debug.md       # Quick debugging
│   ├── workflows.selectors.debug.complete.md  # Comprehensive analysis
│   └── workflows.selectors.design.standards.md  # Engineering rules
├── snapshot-analysis.md                   # System health analysis
└── system-maintenance.md                  # Maintenance procedures
```

**Note:** `workflows.selectors.start.md` was intentionally removed to eliminate duplicate entry points. Use this file as the single entry point.

---

## 🎯 What Do You Do?

**Select a number (1-6) to start corresponding workflow:**

### 🔍 Debug Selector Issues
**Most Common Task** - 80% of workflow usage

1. **[Automated Debugging](scripts/selectors/Debug-Selectors.ps1)** - Smart clustering, faster processing, auto-detects environment, prevents shell errors
2. **[Manual Step-by-Step](selectors/workflows.selectors.debug.md)** - Original workflow for learning and detailed analysis
3. **[Complete Analysis](selectors/workflows.selectors.debug.complete.md)** - Complex issues, comprehensive methodology

### 🏗️ Design New Selectors  
**Engineering Task** - 15% of workflow usage

4. **[Design Standards](selectors/workflows.selectors.design.standards.md)** - Engineering rules, anti-patterns, performance budgets

### 📊 Analyze System Health
**Maintenance Task** - 5% of workflow usage

5. **[Snapshot Analysis](snapshot-analysis.md)** - System performance, failure patterns
6. **[System Maintenance](system-maintenance.md)** - Cleanup, optimization, monitoring

---

## 🚀 Quick Start Guide

**New Users:** Start here and follow the decision tree above.

**Experienced Users:** Jump directly to your needed workflow using the links.

For more information, see main [Snapshot System Status](../SNAPSHOT_SYSTEM_STATUS.md) documentation.
