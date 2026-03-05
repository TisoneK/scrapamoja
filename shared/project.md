# Project Convention

## Purpose
This file is injected into every agent call as part of the system prompt.
It defines the project's conventions, stack, and global rules.
It is agent-agnostic — does not reference any specific LLM provider or IDE.

## Stack
- **Workflow format**: Agentfile (YAML + Markdown)
- **Runtime scripts**: Bash + PowerShell
- **No external frameworks or SDKs required**

## Conventions
- Workflow configs: `workflow.yaml`
- Agents: `agents/<role>.md`
- Skills: `skills/<skill-name>.md`
- Generation artifacts: `artifacts/<workflow-name>/<run-id>/<step-id>-<artifact>.<ext>`
- Runtime step outputs: `outputs/<step-id>-<artifact>.<ext>`

## Agent Behavior
- Be concise and structured in outputs
- If something is unclear, say so explicitly — never guess
- Never invent file paths — use only paths defined in workflow.yaml
