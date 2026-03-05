---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/product-brief-scrapamoja-2026-03-02.md
  - docs/yaml-configuration.md
  - docs/workflows/workflows.start.md
workflowType: 'architecture'
project_name: scrapamoja
user_name: Tisone
date: '2026-03-02'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
- **Selector Failure Detection & Capture**: System detects selector failures, captures DOM snapshots, records failure context
- **Alternative Selector Proposal**: Analyzes DOM structure, proposes multiple strategies with confidence scores, shows blast radius
- **Human Verification Workflow**: Visual previews, approve/reject/flag workflow, custom selector creation
- **Learning & Weight Adjustment**: Per-selector learning from approvals/rejections, tracks survival across generations
- **Versioned Recipes**: Recipe versioning, stability scoring, inheritance support (Parent → Child)
- **Audit Logging**: Complete audit trail of human decisions, queryable history
- **Escalation UI**: Dashboard view, technical and non-technical modes, fast triage workflow
- **Feature Flags**: Per-sport and per-site enable/disable

**Non-Functional Requirements:**
- **Performance**: Escalation UI < 5 min, Proposal generation < 30 sec, Weight adjustment < 1 sec
- **Scalability**: 1000+ recipe versions, 5+ concurrent users
- **Accessibility**: Non-technical UI, visual previews, plain language
- **Integration**: YAML compatibility, Playwright integration, hot-reload

### Scale & Complexity

- Primary domain: Backend API + Web UI (Escalation Dashboard)
- Complexity level: Medium
- Estimated architectural components: 8-10 major components

### Technical Constraints & Dependencies

- Must extend existing YAML configuration system (docs/yaml-configuration.md)
- Must integrate with existing multi-strategy selector engine
- Must work with Playwright for DOM snapshot capture
- Configuration changes must support hot-reload
- Existing system has: Configuration Loader, Inheritance Resolver, Semantic Index, File Watcher, Enhanced Registry, Enhanced Resolver

### Cross-Cutting Concerns Identified

1. **Configuration Versioning**: Recipe versions must integrate with existing YAML hierarchy
2. **Audit Trail**: All human decisions need persistent logging
3. **Learning System**: Weight adjustments must not block selector resolution
4. **Feature Flags**: Incremental rollout by sport requires flag system
5. **Dual UI Modes**: Technical and non-technical views of same data

---

## Starter Template Evaluation

### Primary Technology Domain

**Python Library with Web UI Extension** - This is an extension project (brownfield), not a new greenfield project. The "starter" is the existing scrapamoja codebase.

### Existing Technical Foundation

Based on the project context analysis:

| Component | Technology | Location |
|-----------|------------|----------|
| Selector Engine | Python (async) | `src/selectors/` |
| Configuration | YAML-based | `src/selectors/config/` |
| Browser Automation | Playwright | Python integration |
| Web Framework | Existing patterns | TBD for Escalation UI |
| Database | TBD | For recipes/audit |

### Extension Points Identified

**New Components Required:**
1. **Recipe Versioning System** - Extends YAML config with version metadata
2. **Audit Log Storage** - Persistent storage for human decisions
3. **Escalation UI** - Web dashboard for selector approval workflow
4. **Learning Engine** - Weight adjustment based on approvals/rejections
5. **Feature Flag Service** - Per-sport enable/disable

### Technical Stack Recommendations

**Backend Extension (Python):**
- FastAPI for Escalation UI REST API
- SQLite (MVP) / PostgreSQL (production) for recipe/audit storage
- Pydantic for data validation
- Existing async patterns continue

**Frontend (Escalation UI):**
- React + TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- Shadcn/UI or similar component library

**Database:**
- SQLite for development/MVP
- PostgreSQL for production with multiple users

### Rationale for Selection

This is a **brownfield extension project** - the starter is the existing codebase. The architectural decisions focus on:

1. **Minimal invasion** - Extend existing patterns, don't rewrite
2. **Hot-reload compatibility** - Maintain existing YAML config system
3. **Separation of concerns** - New features in new modules
4. **Scalability path** - MVP SQLite → production PostgreSQL

### Note

Project initialization is NOT a "create new project" command. Instead, this involves:
1. Adding new Python modules to existing structure
2. Extending YAML schema with new fields
3. Creating new Escalation UI frontend (can use Vite + React starter)

---

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Database choice (SQLite for MVP)
- API framework (FastAPI)
- Code organization (new module)

**Important Decisions (Shape Architecture):**
- UI framework (React + TypeScript)
- Authentication (API Keys)
- Component integration points

**Deferred Decisions (Post-MVP):**
- PostgreSQL migration
- OAuth2 authentication
- Multi-site expansion

---

### Data Architecture

| Decision | Choice | Rationale |
|----------|--------|----------|
| Database | SQLite (MVP) | Zero config, file-based, simple MVP |
| Database | PostgreSQL (Future) | Better concurrency for production |
| ORM | SQLAlchemy 2.0 | Python standard, async support |
| Migration | Alembic | Industry standard for Python |

**Tables Required:**
- `recipes` - Versioned selector configurations
- `audit_log` - Human decision records
- `weights` - Learning algorithm weights
- `feature_flags` - Per-sport/site flags
- `snapshots` - Reference to captured DOM snapshots

---

### API & Communication

| Decision | Choice | Rationale |
|----------|--------|----------|
| Framework | FastAPI | Async-native, matches existing patterns |
| Documentation | Auto-generated OpenAPI | Built-in with FastAPI |
| Error Handling | RFC 7807 Problem Details | Standardized API errors |
| Rate Limiting | Per-API-key | Simple, effective |

**API Endpoints Required:**
- `GET /failures` - List selector failures
- `GET /failures/{id}` - Get failure details + snapshot
- `POST /failures/{id}/approve` - Approve proposed selector
- `POST /failures/{id}/reject` - Reject with reason
- `GET /recipes` - List recipe versions
- `GET /recipes/{id}` - Get specific recipe
- `GET /audit` - Query audit history
- `GET /weights` - View learning weights
- `PATCH /weights/{selector}` - Adjust weights

---

### Frontend Architecture

| Decision | Choice | Rationale |
|----------|--------|----------|
| Build Tool | Vite | Fast, modern, industry standard |
| Framework | React | Large ecosystem, familiar |
| Language | TypeScript | Type safety, better DX |
| State Management | React Query + Zustand | Server state + UI state |
| UI Library | Shadcn/UI | Clean, accessible components |
| Styling | Tailwind CSS | Utility-first, popular |

**Frontend Components:**
- Failure Dashboard - List of selector failures
- Failure Detail View - Snapshot + proposed alternatives
- Approval Panel - Approve/Reject/Modify actions
- Recipe Viewer - Version history + stability scores
- Audit Log - Searchable decision history
- Settings - Feature flags, API keys management

---

### Authentication & Security

| Decision | Choice | Rationale |
|----------|--------|----------|
| Auth Method | API Keys | Simple, good for integrations |
| Key Storage | Hashed in database | Security best practice |
| Rate Limiting | Per-key | Prevent abuse |
| Future Auth | OAuth2 | For team expansion |

---

### Code Organization

| Decision | Choice | Rationale |
|----------|--------|----------|
| New Module | `src/selectors/adaptive/` | Extend existing selector module |
| Sub-packages | `src/selectors/adaptive/{api,db,models,services}` | Organized structure under selectors |
| Frontend | `ui/escalation/` | Separate from core UI |
| Config | Extend existing YAML system | Maintain compatibility |

**Proposed Structure:**
```
src/
├── selectors/
│   ├── adaptive/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   ├── schemas/
│   │   │   └── dependencies/
│   │   ├── db/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   └── migrations/
│   │   ├── services/
│   │   │   ├── failure_detector.py
│   │   │   ├── proposal_engine.py
│   │   │   ├── learning_engine.py
│   │   │   └── audit_service.py
│   │   └── config/
│   ├── engine/
│   │   ├── resolver.py
│   │   ├── registry.py
│   │   └── configuration/
│   └── config/
└── ui/
    └── escalation/
        ├── components/
        ├── pages/
        ├── hooks/
        └── api/
```

---

### Integration Points

**With Existing System:**
| Component | Integration |
|-----------|-------------|
| Selector Engine | Listen for resolution failures |
| Snapshot System | Reference captured snapshots |
| YAML Config | Extend with recipe metadata |
| Site Registry | Per-site feature flags |

---

### Implementation Sequence

1. **Phase 1: Foundation**
   - Set up `src/selectors/adaptive/` module
   - Create SQLite database + models
   - Build basic FastAPI endpoints

2. **Phase 2: Core Workflow**
   - Integrate with selector failure detection
   - Create escalation UI React app
   - Build failure dashboard + detail view

3. **Phase 3: Intelligence**
   - Implement proposal engine
   - Add learning engine (weight adjustment)
   - Build recipe versioning

4. **Phase 4: Polish**
   - Add audit logging UI
   - Feature flag management
   - API key management

---

## Implementation Patterns & Consistency Rules

### Naming Patterns

**Database:**
- Tables: `snake_case` plural (e.g., `recipes`, `audit_logs`)
- Columns: `snake_case` (e.g., `created_at`, `user_id`)
- Foreign keys: `{table}_id` format (e.g., `recipe_id`)

**API Endpoints:**
- RESTful: plural nouns (e.g., `/failures`, `/recipes`)
- HTTP methods: GET (read), POST (create), PATCH (update), DELETE (remove)

**Code:**
- Python: `snake_case` functions/variables
- TypeScript: `camelCase` variables, `PascalCase` components
- Files: `snake_case.py`, `kebab-case.tsx`

---

### Structure Patterns

**Tests:**
- Co-located with source: `selectors/adaptive/services/test_service.py`
- Or `tests/` folder for integration tests

**Components (React):**
- By feature: `features/failures/components/FailureCard.tsx`

**Shared utilities:**
- `selectors/adaptive/shared/utils.py`

---

### API Response Formats

**Success:**
```json
{"data": {...}}
```

**Error (RFC 7807):**
```json
{"type": "/errors/not-found", "title": "Not Found", "detail": "Recipe not found"}
```

**Dates:** ISO 8601 format (`2026-03-02T14:30:00Z`)

---

### Process Patterns

**Error Handling:**
- Use FastAPI's exception handlers
- Return appropriate HTTP status codes
- Log errors with context

**Loading States:**
- React Query handles server state
- Zustand for UI state

**Validation:**
- Pydantic models for request/response
- Zod schemas for frontend

---

## Next Steps

The architecture document is complete. The key decisions are:

1. **Extend existing** `src/selectors/` with adaptive features in `src/selectors/adaptive/`
2. **SQLite** for MVP, PostgreSQL for production
3. **FastAPI** for the API
4. **React + TypeScript + Vite** for Escalation UI
5. **API Keys** for authentication
6. **4-phase implementation** approach

The architecture is saved to `_bmad-output/planning-artifacts/architecture.md`
