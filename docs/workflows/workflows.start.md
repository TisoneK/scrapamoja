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

**Select a number (1-5) to start the corresponding workflow:**

### 🔍 Debug Selector Issues
**Most Common Task** - 80% of workflow usage

1. **[Check & Fix Failed Selectors](selectors/workflows.selectors.debug.md)** - Find broken selectors, analyze failures, and fix them using debugging workflow
2. **[Complete Analysis](selectors/workflows.selectors.debug.complete.md)** - Complex issues, comprehensive methodology

### 🏗️ Design New Selectors  
**Engineering Task** - 15% of workflow usage

3. **[Design Standards](selectors/workflows.selectors.design.standards.md)** - Engineering-grade rules, anti-patterns, performance budgets

### 📊 Analyze System Health
**Maintenance Task** - 5% of workflow usage

4. **[Snapshot Analysis](snapshot-analysis.md)** - System performance, failure patterns
5. **[System Maintenance](system-maintenance.md)** - Cleanup, optimization, monitoring

---

## 🚀 Quick Start Guide

**New Contributors:** Start here and follow the decision tree above.

**Experienced Users:** Jump directly to your needed workflow using the links.

## 📋 Workflow Features

All workflows include:
- ✅ **Clear purpose and objectives**
- ✅ **Step-by-step procedures** 
- ✅ **Expected outcomes**
- ✅ **Cross-references** to related workflows
- ✅ **Machine-checkable constraints** (where applicable)

## Integration

These workflows integrate with the snapshot observability system to provide:
- Evidence-based debugging
- Standardized processes
- Reproducible results
- Historical analysis capabilities

For more information, see main [Snapshot System Status](../SNAPSHOT_SYSTEM_STATUS.md) documentation.
