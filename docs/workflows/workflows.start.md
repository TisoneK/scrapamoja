# Scrapamoja Workflows

This directory contains standardized workflows for system operations and debugging.

---

## � System Status

| Component | Status | Details | Action |
|-----------|--------|---------|--------|
| **Debugging** | 🟢 Healthy | No pending failures | [Start Debugging](#1-automated-debugging) |
| **Storage** | 🟢 Clean | < 500MB, < 30 days old | [Check Storage](#6-system-maintenance) |
| **Selectors** | 🟢 Healthy | 0 design issues | [Review Standards](#4-design-standards) |
| **Maintenance** | 🔵 Up to date | Last run today | System ready |

---

## 🎯 Recommended for You

### � High Priority (Based on current state)

**1. [Automated Debugging](scripts/selectors/Debug-Selectors.ps1)** ← **Most Common (80% usage)**
- Smart clustering, faster processing
- Auto-detects environment, prevents shell errors
- **Best for:** Most debugging scenarios

### 📋 Common Tasks

**2. [Design Standards](selectors/workflows.selectors.design.standards.md)** ← **Engineering (15% usage)**
- Engineering rules, anti-patterns, performance budgets
- **Best for:** New selector development

**3. [System Maintenance](system-maintenance.md)** ← **Maintenance (5% usage)**
- Cleanup, optimization, monitoring
- **Best for:** Regular system health

### 🔧 Advanced Options

**4. [Manual Debugging](selectors/workflows.selectors.debug.md)** ← **Learning Mode**
- Original workflow for learning and detailed analysis
- **Best for:** Understanding debugging process

**5. [Complete Analysis](selectors/workflows.selectors.debug.complete.md)** ← **Complex Issues**
- Comprehensive methodology for difficult problems
- **Best for:** Complex or persistent failures

**6. [Snapshot Analysis](snapshot-analysis.md)** ← **Performance Analysis**
- System performance, failure patterns
- **Best for:** Performance investigation

---

## ⚡ Quick Actions

### 🚀 Start Debugging (One command)
```bash
# Auto-detect failures, cluster them, fix in batches
./docs/scripts/selectors/Debug-Selectors.ps1
```

### 📁 Check System Health
```bash
# Validate all components, report issues
./docs/workflows/system-maintenance.md
```

### 🔧 Review Design Rules
```bash
# Check selector engineering standards
./docs/workflows/selectors/workflows.selectors.design.standards.md
```

---

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

---

## 🎯 What Do You Want to Do?

### [🐛 Fix a Problem](#1-automated-debugging)
- **Selector failures?** → Automated Debugging
- **Design issues?** → Design Standards  
- **System errors?** → System Maintenance

### [📊 Analyze Data](#6-snapshot-analysis)
- **Performance?** → Snapshot Analysis
- **Patterns?** → Complete Analysis
- **Health?** → System Check

### [🔧 Maintain System](#3-system-maintenance)
- **Cleanup?** → Archive Session (if needed)
- **Update?** → System Maintenance
- **Optimize?** → Performance Tuning

---

**Note:** `workflows.selectors.start.md` was intentionally removed to eliminate duplicate entry points. Use this file as the single entry point.

---

## 🚀 Quick Start Guide

**New Users:** Start with [Automated Debugging](#1-automated-debugging) - it handles 80% of use cases automatically.

**Experienced Users:** Jump directly to your needed workflow using the links above.

**System Administrators:** Check [System Status](#-system-status) first, then proceed with appropriate workflow.

For more information, see main [Snapshot System Status](../SNAPSHOT_SYSTEM_STATUS.md) documentation.
