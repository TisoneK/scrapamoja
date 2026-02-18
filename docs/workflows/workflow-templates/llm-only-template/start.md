---
description: Entry point for LLM-only workflow with mode selection
---

# LLM-Only Workflow Template

Choose your workflow mode:

## 🚀 Quick Start

### Analysis Mode
Analyze situations, identify options, and provide recommendations.
- **Use when**: Need to understand complex situations and make decisions
- **Output**: Analysis report with multiple options and recommendations

### Generation Mode  
Create content, solutions, or creative outputs.
- **Use when**: Need to generate new materials or solve problems creatively
- **Output**: Generated content with quality validation

### Review Mode
Evaluate existing work and provide improvement suggestions.
- **Use when**: Need to assess quality and identify improvements
- **Output**: Review report with actionable feedback

### Planning Mode
Develop strategic plans and implementation roadmaps.
- **Use when**: Need to create structured approaches to goals
- **Output**: Strategic plan with milestones and timelines

## 📋 Prerequisites

- **LLM Assistant**: For analysis, generation, and decision support
- **Domain Knowledge**: Understanding of the specific problem area
- **Clear Objectives**: Well-defined goals and success criteria
- **Collaboration**: Willingness to provide feedback and make decisions

## 🔧 Configuration

Current workflow settings are defined in:
- **rules.md**: LLM behavior and decision guidelines
- **status.json**: Progress tracking and metrics
- **templates/**: Reusable prompt templates

## 📊 Current Status

```json
{
  "workflow": "llm-only-template",
  "status": "template",
  "progress": 0,
  "ready_for_customization": true
}
```

## 🚀 Getting Started

1. **Customize this template** for your specific domain
2. **Update rules.md** with your LLM behavior requirements
3. **Create prompt templates** for your workflow steps
4. **Test with sample scenarios** before production use
5. **Monitor quality** and refine based on feedback

## 📚 Documentation

- **Main Guide**: [llm-only-template.md](llm-only-template.md)
- **Overview**: [README.md](README.md)
- **LLM Rules**: [rules.md](rules.md)

## 🤖 LLM Interaction Patterns

### Analysis Workflow
1. **Context Gathering**: Understand the situation and requirements
2. **Factor Analysis**: Identify key variables and constraints
3. **Option Generation**: Develop multiple viable approaches
4. **Evaluation**: Assess pros and cons of each option
5. **Recommendation**: Provide reasoned recommendation

### Generation Workflow
1. **Requirement Understanding**: Clarify what needs to be created
2. **Creative Exploration**: Generate initial ideas and approaches
3. **Development**: Build out the content or solution
4. **Quality Check**: Self-validate against requirements
5. **Refinement**: Improve based on quality criteria

### Review Workflow
1. **Assessment**: Evaluate current state against standards
2. **Issue Identification**: Find problems and improvement opportunities
3. **Prioritization**: Rank issues by importance and impact
4. **Solution Design**: Develop specific improvement recommendations
5. **Action Plan**: Create implementation roadmap

---

*This is a template. Customize it for your specific workflow requirements and domain expertise.*
